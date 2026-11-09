#!/usr/bin/env python3
import argparse
import os
import sys

from app_usage_cli import company, service


def run_daemon(args):
    print("--- Starting activity agent ---")
    if sys.platform == "win32":
        from app_usage_cli import tracker_windows
        tracker_windows.main()
    elif os.environ.get("XDG_SESSION_TYPE") == "wayland" and "GNOME" in os.environ.get("XDG_CURRENT_DESKTOP", "").upper():
        from app_usage_cli import tracker_wayland_gnome
        tracker_wayland_gnome.main()
    else:
        from app_usage_cli import tracker
        tracker.main()


def run_gui(args=None):
    from app_usage_cli import gui
    gui.main()


def main_parser():
    p = argparse.ArgumentParser(prog="app-usage", description="Company activity agent (run with no command to open the window)")
    sub = p.add_subparsers(dest="command")
    sub.add_parser("gui", help="Open the window (default)").set_defaults(func=run_gui)
    e = sub.add_parser("enroll", help="Join a company from the terminal")
    e.add_argument("--server", required=True, help="Server address, e.g. https://activity.example.com")
    e.add_argument("--company-id", "--code", dest="company_id", required=True, help="Company ID from your manager")
    e.add_argument("--name", default="", help="Your name (asked if omitted)")
    e.add_argument("--email", default="", help="Your work email (optional)")
    e.add_argument("-y", "--yes", action="store_true", help="Accept the policy without prompting (managed installs)")
    e.set_defaults(func=lambda a: company.cli_enroll(a.server, a.company_id, a.name, a.email, a.yes))
    for name, fn, help_ in [
        ("status", company.status, "Show enrolment and exactly what is collected"),
        ("preview", company.preview, "Print the data that would be uploaded, without sending"),
        ("sync", company.cli_sync, "Upload now"),
        ("unenroll", company.cli_unenroll, "Stop uploading and unlink this computer"),
        ("daemon", run_daemon, "Run the background tracker"),
        ("install-service", service.install_service, "Start the agent at login"),
        ("uninstall-service", service.uninstall_service, "Remove the startup service"),
    ]:
        sub.add_parser(name, help=help_).set_defaults(func=lambda a, fn=fn: fn(a) if fn is run_daemon else fn())
    return p


def main():
    args = main_parser().parse_args()
    (args.func if getattr(args, "func", None) else run_gui)(args)


if __name__ == "__main__":
    main()
