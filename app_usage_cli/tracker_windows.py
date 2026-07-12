import time
import json
import signal
import threading
from datetime import datetime
import psutil
from . import config
import ctypes
import os

# Ensure this runs on Windows
if os.name == 'nt':
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
else:
    user32 = None
    kernel32 = None

LOG_DIR = config.get_analytics_dir()
POLL_INTERVAL = 0.5
IDLE_TIMEOUT = 300
SYNC_INTERVAL = 600

running = True
last_app = None
last_title = None
idle = False
locked = False

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

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

def get_idle_time():
    if not user32 or not kernel32: return 0
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    user32.GetLastInputInfo(ctypes.byref(lii))
    millis = kernel32.GetTickCount() - lii.dwTime
    return millis / 1000.0

def get_focused_window():
    if not user32: return None
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd: return None
        
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        
        p = psutil.Process(pid.value)
        return {
            "window": hwnd,
            "pid": pid.value,
            "app": p.name(),
            "title": title,
            "exe": p.exe()
        }
    except Exception:
        return None

def monitor():
    global idle, last_app, last_title, locked

    while running:
        current = get_focused_window()
        
        # Simple lock detection based on active window process
        is_locked = False
        if current and current["app"].lower() in ("logonui.exe", "lockapp.exe"):
            is_locked = True

        if is_locked and not locked:
            locked = True
            log("LOCK")
        elif not is_locked and locked:
            locked = False
            log("UNLOCK")

        if locked:
            time.sleep(POLL_INTERVAL)
            continue

        idle_time = get_idle_time()
        
        if not idle and idle_time >= IDLE_TIMEOUT:
            idle = True
            log("IDLE")
        elif idle and idle_time < 2:
            idle = False
            log("ACTIVE")

        if not idle and current is not None:
            if current["app"] != last_app:
                log("FOCUS", **current)
                last_app = current["app"]
                last_title = current["title"]
            elif current["title"] != last_title:
                log("TITLE", window=current["window"], pid=current["pid"], app=current["app"], title=current["title"])
                last_title = current["title"]
        elif not idle and current is None:
            last_app = None
            last_title = None

        time.sleep(POLL_INTERVAL)

def shutdown(*args):
    global running
    log("SHUTDOWN")
    running = False

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
    if os.name != 'nt':
        print("This tracker is for Windows only.")
        return
    log("BOOT")
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    
    sync_thread = threading.Thread(target=scheduled_run_all, daemon=True)
    sync_thread.start()
    
    monitor()

if __name__ == "__main__":
    main()
