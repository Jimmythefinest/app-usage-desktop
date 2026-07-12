#!/usr/bin/env python3

import asyncio
import json
import signal
import threading
import time
from datetime import datetime
from pathlib import Path
from dbus_next.aio import MessageBus
from dbus_next import BusType

from . import config

LOG_DIR = config.get_analytics_dir()
POLL_INTERVAL = 0.5
IDLE_TIMEOUT = 300  # seconds
SYNC_INTERVAL = 600 # 10 minutes

running = True
last_app = None
last_title = None
idle = False
locked = False

def log(event, **kwargs):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logfile = LOG_DIR / f"{datetime.now():%Y-%m-%d}.jsonl"

    entry = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "event": event,
        **kwargs
    }

    with open(logfile, "a") as f:
        f.write(json.dumps(entry) + "\n")

async def get_idle_time(bus):
    try:
        introspection = await bus.introspect("org.gnome.Mutter.IdleMonitor", "/org/gnome/Mutter/IdleMonitor/Core")
        obj = bus.get_proxy_object("org.gnome.Mutter.IdleMonitor", "/org/gnome/Mutter/IdleMonitor/Core", introspection)
        interface = obj.get_interface("org.gnome.Mutter.IdleMonitor")
        # Returns (uint64,) in ms
        result = await interface.call_get_idletime()
        return result / 1000.0
    except Exception as e:
        return 0

async def get_focused_window(bus):
    try:
        introspection = await bus.introspect("org.gnome.Shell", "/org/gnome/Shell/Extensions/AppUsage")
        obj = bus.get_proxy_object("org.gnome.Shell", "/org/gnome/Shell/Extensions/AppUsage", introspection)
        interface = obj.get_interface("org.gnome.Shell.Extensions.AppUsage")
        # Returns [app_name, window_title, pid, window_id]
        app_name, title, pid, window_id = await interface.call_get_active_window()
        
        if not app_name and not title:
            return None
            
        return {
            "window": window_id,
            "pid": pid,
            "app": app_name,
            "title": title,
            "exe": "" # Wayland doesn't easily expose executable path without procfs scraping
        }
    except Exception as e:
        return None

async def monitor_lock(bus):
    global locked
    try:
        introspection = await bus.introspect("org.gnome.ScreenSaver", "/org/gnome/ScreenSaver")
        obj = bus.get_proxy_object("org.gnome.ScreenSaver", "/org/gnome/ScreenSaver", introspection)
        interface = obj.get_interface("org.gnome.ScreenSaver")

        def active_changed(active):
            global locked
            if active and not locked:
                locked = True
                log("LOCK")
            elif not active and locked:
                locked = False
                log("UNLOCK")

        interface.on_active_changed(active_changed)
    except Exception as e:
        log("ERROR", message=f"DBus Monitor Failure: {str(e)}")

async def monitor():
    global idle, last_app, last_title
    
    bus = await MessageBus(bus_type=BusType.SESSION).connect()
    await monitor_lock(bus)

    while running:
        if locked:
            await asyncio.sleep(POLL_INTERVAL)
            continue

        idle_time = await get_idle_time(bus)

        if not idle and idle_time >= IDLE_TIMEOUT:
            idle = True
            log("IDLE")
        elif idle and idle_time < 2:
            idle = False
            log("ACTIVE")

        if not idle:
            current = await get_focused_window(bus)

            if current is not None:
                if current["app"] != last_app:
                    log("FOCUS", **current)
                    last_app = current["app"]
                    last_title = current["title"]
                elif current["title"] != last_title:
                    log(
                        "TITLE",
                        window=current["window"],
                        pid=current["pid"],
                        app=current["app"],
                        title=current["title"]
                    )
                    last_title = current["title"]
            else:
                last_app = None
                last_title = None

        await asyncio.sleep(POLL_INTERVAL)

def scheduled_run_all():
    from . import builder, syncer, importer
    while running:
        for _ in range(SYNC_INTERVAL):
            if not running: return
            time.sleep(1)
        if not running: return
        
        print("\n--- Scheduled Background Sync ---")
        try:
            builder.main()
            syncer.main()
            importer.main()
        except Exception as e:
            print(f"Error during background sync: {e}")

def shutdown(*args):
    global running
    log("SHUTDOWN")
    running = False

def main():
    log("BOOT")

    # Start periodic sync thread
    sync_thread = threading.Thread(target=scheduled_run_all, daemon=True)
    sync_thread.start()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    asyncio.run(monitor())

if __name__ == "__main__":
    main()
