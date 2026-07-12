#!/usr/bin/env python3
import json, re
from pathlib import Path
from  app_usage_cli import config

INPUT = config.get_activities_dir()
OUTPUT = config.get_vault_dir() / "Activities"
OUTPUT.mkdir(parents=True, exist_ok=True)
INDEX = OUTPUT / "activity_index.json"

def load_index():
    return json.loads(INDEX.read_text()) if INDEX.exists() else {}

def save_index(idx):
    INDEX.write_text(json.dumps(idx, indent=2))

def read_user_fields(path):
    fields = {"claimed": "false", "session": "", "project": "", "task": "", "status": "Inbox", "tags": "[]"}
    if not path.exists(): return fields
    txt = path.read_text(encoding="utf8")
    for k in fields:
        m = re.search(rf"^{k}:\s*(.*)$", txt, re.MULTILINE)
        if m: 
            val = m.group(1).strip()
            # Unescape heavily quoted values (cleans up previous double-dumps like "\"\\\"\\\"\"")
            while val.startswith('"') and val.endswith('"') and len(val) >= 2:
                try:
                    new_val = json.loads(val)
                    if not isinstance(new_val, str) or new_val == val:
                        break
                    val = new_val
                except json.JSONDecodeError:
                    break
            fields[k] = val
    return fields

def fmt(sec):
    sec = int(sec); m, s = divmod(sec, 60); h, m = divmod(m, 60)
    return f"{h}h {m}m {s}s" if h else (f"{m}m {s}s" if m else f"{s}s")

def note(act, u):
    def yaml_list(items, indent=2):
        pad = " " * indent
        return "\n".join(f"{pad}- {json.dumps(i)}" for i in items) if items else ""

    def yaml_focus_list(intervals, indent=2):
        pad = " " * indent
        lines = []
        for i in intervals:
            lines.append(f"{pad}- start: {json.dumps(i['start'])}")
            lines.append(f"{pad}  end: {json.dumps(i['end'])}")
        return "\n".join(lines) if lines else "[]"

    def yaml_cmd_list(cmds, indent=2):
        pad = " " * indent
        lines = []
        for c in cmds:
            lines.append(f"{pad}- timestamp: {json.dumps(c['timestamp'])}")
            lines.append(f"{pad}  command: {json.dumps(c['command'])}")
            lines.append(f"{pad}  cwd: {json.dumps(c.get('cwd', ''))}")
        return "\n".join(lines) if lines else ""

    titles_md = "\n".join(f"- {t}" for t in act.get("titles", []))
    focus_md = "\n".join(f"- {i['start']} → {i['end']}" for i in act.get("focus_intervals", []))
    cmds = act.get("commands", [])
    cmd_md = "\n".join(f"- [{c['timestamp'].split('T')[1].split('+')[0]}] `{c['command']}` (cwd: {c.get('cwd', '')})" for c in cmds) or "_No commands recorded._"
    
    session = json.dumps(u['session'])
    status = json.dumps(u['status'])
    project = json.dumps(u['project'])
    task = json.dumps(u['task'])
    tags = u['tags']  # emit as-is (e.g. [])
    
    return f"""\
---
type: Activity
activity_id: {act['id']}
claimed: {u['claimed']}
session: {session}
project: {project}
task: {task}
status: {status}
tags: {tags}
app: {act['app']}
pid: {act['pid']}
window: {act['window']}
exe: {json.dumps(act.get('exe', ''))}
start: {json.dumps(act['start'])}
end: {json.dumps(act['end'])}
elapsed_seconds: {act['elapsed_seconds']}
focused_seconds: {act['focused_seconds']}
titles:
{yaml_list(act.get('titles', []))}
focus_intervals:
{yaml_focus_list(act.get('focus_intervals', []))}
commands: 
{yaml_cmd_list(act.get('commands', []))}
---

# {act['app']}

## Summary
- Elapsed: {fmt(act['elapsed_seconds'])}
- Focused: {fmt(act['focused_seconds'])}

## Titles
{titles_md}

## Focus Intervals
{focus_md}

## Commands
{cmd_md}

# Notes

"""

def main():
    idx = load_index()
    created = updated = 0
    
    for jf in sorted(INPUT.glob("*.json")):
        data = json.loads(jf.read_text())
        if not isinstance(data, list):
            print(f"Skipping {jf.name} (not an activity list)")
            continue
        for act in data:
            if not isinstance(act, dict) or "id" not in act:
                continue
            path = OUTPUT / idx.get(act["id"], f"{act['id']}.md")
            user = read_user_fields(path)
            path.write_text(note(act, user), encoding="utf8")
            
            if act["id"] in idx: 
                updated += 1
            else: 
                idx[act["id"]] = path.name
                created += 1
    
    save_index(idx)
    print(f"Created: {created}\nUpdated: {updated}")

if __name__ == "__main__":
    main()
