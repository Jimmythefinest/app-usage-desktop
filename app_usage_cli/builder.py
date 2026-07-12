#!/usr/bin/env python3
import json
import hashlib
from pathlib import Path
from datetime import datetime
from collections import OrderedDict
from  app_usage_cli import config

ANALYTICS_DIR = config.get_analytics_dir()
OUTPUT_DIR = config.get_activities_dir()
COMMANDS_DIR = config.get_command_logs_dir()

MAX_GAP = 300  # seconds

def parse(ts:str)->datetime:
    return datetime.fromisoformat(ts)

def seconds(a,b):
    return (b-a).total_seconds()

def normalize_title(title:str)->str:
    if not title:
        return ""
    title=title.strip()
    for suf in (" - Google Chrome"," - Visual Studio Code"):
        if title.endswith(suf):
            title=title[:-len(suf)]
    return title.lower()

def make_activity_id(app,exe,start,window):
    key=f"{app or ''}|{exe or ''}|{int(start.timestamp()*1000)}|{window}"
    return "act_"+hashlib.sha1(key.encode()).hexdigest()[:16]

def build(events, commands=None):
    if commands is None:
        commands = []
    events.sort(key=lambda e:e["time"])
    activities=[]
    windows={}
    focused_window=None

    def finalize(wid):
        act=windows.pop(wid)
        if act["focus_start"] is not None:
            act["focus"].append({
                "start":act["focus_start"].isoformat(),
                "end":act["last_seen"].isoformat()
            })
        total=sum(seconds(parse(i["start"]),parse(i["end"])) for i in act["focus"])
        titles=list(act["titles"].keys())
        activities.append({
            "id":make_activity_id(act["app"],act["exe"],act["start"],act["window"]),
            "window":act["window"],
            "app":act["app"],
            "pid":act["pid"],
            "exe":act["exe"],
            "start":act["start"].isoformat(),
            "end":act["last_seen"].isoformat(),
            "elapsed_seconds":int(seconds(act["start"],act["last_seen"])),
            "focused_seconds":int(total),
            "focus_intervals":act["focus"],
            "titles":titles,
            "commands":[]
        })

    for event in events:
        now=parse(event["time"])

        stale=[]
        for wid,act in windows.items():
            if act["focus_start"] is None and seconds(act["last_seen"],now)>MAX_GAP:
                stale.append(wid)
        for wid in stale:
            finalize(wid)

        if event["event"]=="FOCUS":
            if focused_window is not None and focused_window in windows:
                cur=windows[focused_window]
                if cur["focus_start"] is not None:
                    cur["focus"].append({
                        "start":cur["focus_start"].isoformat(),
                        "end":now.isoformat()
                    })
                    cur["focus_start"]=None
                    cur["last_seen"]=now

            focused_window=event["window"]

            if focused_window not in windows:
                windows[focused_window]={
                    "window":event["window"],
                    "app":event["app"],
                    "pid":event["pid"],
                    "exe":event.get("exe"),
                    "start":now,
                    "last_seen":now,
                    "focus_start":now,
                    "focus":[],
                    "titles":OrderedDict()
                }
            else:
                windows[focused_window]["focus_start"]=now
                windows[focused_window]["last_seen"]=now

        elif event["event"]=="TITLE":
            wid=event["window"]
            if wid not in windows:
                windows[wid]={
                    "window":wid,
                    "app":event["app"],
                    "pid":event["pid"],
                    "exe":event.get("exe"),
                    "start":now,
                    "last_seen":now,
                    "focus_start":None,
                    "focus":[],
                    "titles":OrderedDict()
                }
            act=windows[wid]
            act["last_seen"]=now
            act["titles"][event["title"]]=None

        elif event["event"] in ("IDLE", "LOCK", "SHUTDOWN"):
            if focused_window is not None and focused_window in windows:
                cur = windows[focused_window]
                if cur["focus_start"] is not None:
                    cur["focus"].append({
                        "start": cur["focus_start"].isoformat(),
                        "end": now.isoformat()
                    })
                    cur["focus_start"] = None
                cur["last_seen"] = now

        elif event["event"] in ("ACTIVE", "UNLOCK", "BOOT"):
            if focused_window is not None and focused_window in windows:
                cur = windows[focused_window]
                if cur["focus_start"] is None:
                    cur["focus_start"] = now
                cur["last_seen"] = now

    for wid in list(windows.keys()):
        finalize(wid)

    for cmd in commands:
        if cmd.get("event") != "COMMAND":
            continue
        cmd_time = parse(cmd["timestamp"]).replace(tzinfo=None)
        for act in activities:
            matched = False
            for f in act["focus_intervals"]:
                if parse(f["start"]) <= cmd_time <= parse(f["end"]):
                    matched = True
                    break
            
            if matched:
                act["commands"].append({
                    "timestamp": cmd["timestamp"],
                    "command": cmd["command"],
                    "cwd": cmd.get("cwd", ""),
                    "exit_code": cmd.get("exit_code", 0)
                })
                break

    return activities

def main():
    for file in sorted(ANALYTICS_DIR.glob("*.jsonl")):
        print(f"Processing {file.name}")
        events=[]
        with file.open() as f:
            for line in f:
                line=line.strip()
                if line:
                    events.append(json.loads(line))
        
        date_str = file.stem
        cmd_file = COMMANDS_DIR / f"{date_str}.jsonl"
        commands = []
        if cmd_file.exists():
            with cmd_file.open() as f:
                for line in f:
                    line = line.strip()
                    if line:
                        commands.append(json.loads(line))

        activities=build(events, commands)
        out=OUTPUT_DIR/file.with_suffix(".json").name
        with out.open("w") as f:
            json.dump(activities,f,indent=2)
        print(f" -> {len(activities)} activities")
        print(f" -> {out}")

if __name__=="__main__":
    main()
