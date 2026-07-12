#!/usr/bin/env python3

import asyncio
import json
import signal
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

import psutil


###############################################################################
# CONFIG
###############################################################################

from . import config

LOG_DIR = config.get_analytics_dir()
POLL_INTERVAL = 0.5
IDLE_TIMEOUT = 300  # seconds
SYNC_INTERVAL = 600 # seconds (10 minutes)

###############################################################################
# STATE
###############################################################################

running = True

last_app = None
last_title = None

idle = False
locked = False  # Main thread reads this, DBus thread writes this

###############################################################################
# LOGGER
###############################################################################


def log(event, **kwargs):
    LOG_DIR.mkdir(exist_ok=True)
    logfile = LOG_DIR / f"{datetime.now():%Y-%m-%d}.jsonl"

    entry = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "event": event,
        **kwargs
    }

    with open(logfile, "a") as f:
        f.write(json.dumps(entry) + "\n")




###############################################################################
# WINDOW (Optimized to spawn only ONE subprocess instead of three)
###############################################################################


def get_focused_window():
    try:
        # Get active window ID
        window = subprocess.check_output(
            ["xdotool", "getactivewindow"], text=True, stderr=subprocess.DEVNULL
        ).strip()

        # Combine PID and Name fetches into a single bash/subprocess execution context
        # to drastically reduce CPU context-switching overhead
        pid_and_title = subprocess.check_output(
            f"xdotool getwindowpid {window} && xdotool getwindowname {window}",
            shell=True,
            text=True,
            stderr=subprocess.DEVNULL
        ).strip().split("\n")

        if len(pid_and_title) < 2:
            return None

        pid = int(pid_and_title[0])
        title = pid_and_title[1]
        process = psutil.Process(pid)

        return {
            "window": int(window),
            "pid": pid,
            "app": process.name(),
            "title": title,
            "exe": process.exe()
        }
    except Exception:
        # Gracefully catch instances where xdotool can't find an active window 
        # (e.g., during lock screens, desktop switching, or empty workspaces)
        return None


###############################################################################
# IDLE
###############################################################################


def get_idle_time():
    try:
        ms = int(subprocess.check_output(["xprintidle"], text=True).strip())
        return ms / 1000.0
    except Exception:
        return 0


###############################################################################
# LOCK / UNLOCK (DBus listener thread)
###############################################################################


async def monitor_lock():
    from dbus_next.aio import MessageBus
    from dbus_next import BusType
    global locked

    try:
        bus = await MessageBus(bus_type=BusType.SESSION).connect()
        introspection = await bus.introspect(
            "org.gnome.ScreenSaver", "/org/gnome/ScreenSaver"
        )
        obj = bus.get_proxy_object(
            "org.gnome.ScreenSaver", "/org/gnome/ScreenSaver", introspection
        )
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

        while running:
            await asyncio.sleep(1)
            
    except Exception as e:
        log("ERROR", message=f"DBus Monitor Failure: {str(e)}")


def lock_thread():
    # Loop execution context now safely has access to the asyncio namespace
    asyncio.run(monitor_lock())


###############################################################################
# MAIN LOOP
###############################################################################


def monitor():
    global idle
    global last_app
    global last_title

    while running:
        # If the screen is locked, suspend polling metrics until it unlocks
        if locked:
            time.sleep(POLL_INTERVAL)
            continue

        # 1. Idle Check
        idle_time = get_idle_time()

        if not idle and idle_time >= IDLE_TIMEOUT:
            idle = True
            log("IDLE")
        elif idle and idle_time < 2:
            idle = False
            log("ACTIVE")

        # 2. Focus Check (Only track if not idle)
        if not idle:
            current = get_focused_window()

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
                # If window lost focus completely, clear state cache so 
                # returning to the app logs cleanly
                last_app = None
                last_title = None

        time.sleep(POLL_INTERVAL)


###############################################################################
# SHUTDOWN
###############################################################################


def shutdown(*args):
    global running
    log("SHUTDOWN")
    running = False


signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

###############################################################################
# MAIN ENTRYPOINT
###############################################################################


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


def main():
    log("BOOT")

    # Start the DBus background thread for lock detection
    t = threading.Thread(target=lock_thread, daemon=True)
    t.start()

    # Start periodic sync thread
    sync_thread = threading.Thread(target=scheduled_run_all, daemon=True)
    sync_thread.start()

    # Run the main monitor loop
    monitor()


if __name__ == "__main__":
    main()
