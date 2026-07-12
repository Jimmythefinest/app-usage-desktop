from __future__ import annotations

import shlex
import subprocess
import sys
from shutil import which
from pathlib import Path
from textwrap import dedent
from typing import Optional

try:
    from win32com.client import Dispatch
except ImportError:
    Dispatch = None

SERVICE_NAME = "app-usage"


def _launcher_command() -> list[str]:
    launcher = which(SERVICE_NAME)
    if launcher:
        return [launcher, "daemon"]

    argv0 = Path(sys.argv[0])
    if argv0.exists():
        return [str(argv0), "daemon"]

    return [sys.executable, "-m", "app_usage_cli.cli", "daemon"]


def _linux_unit_path() -> Path:
    return Path.home() / ".config" / "systemd" / "user" / f"{SERVICE_NAME}.service"


def _linux_unit_content() -> str:
    command = shlex.join(_launcher_command())
    return dedent(
        f"""\
        [Unit]
        Description=App Usage Tracker
        After=default.target

        [Service]
        Type=simple
        ExecStart={command}
        Restart=on-failure
        RestartSec=5

        [Install]
        WantedBy=default.target
        """
    )


def _windows_task_command(*extra_args: str) -> str:
    """Build a properly quoted schtasks /TR command string."""
    if extra_args:
        return subprocess.list2cmdline(list(extra_args) + ["daemon"])
    return subprocess.list2cmdline(_launcher_command())


def _create_startup_shortcut(exe_path: str) -> None:
    """Create a Windows startup shortcut for the app-usage daemon."""
    startup_dir = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    startup_dir.mkdir(parents=True, exist_ok=True)
    shortcut_path = startup_dir / "App Usage.lnk"

    # Try pywin32 first if available
    if Dispatch:
        try:
            shell = Dispatch("WScript.Shell")
            shortcut = shell.CreateShortcut(str(shortcut_path))
            shortcut.TargetPath = exe_path
            shortcut.Arguments = "daemon"
            shortcut.WorkingDirectory = str(Path(exe_path).parent)
            shortcut.Save()

            print(f"[*] Created Windows startup shortcut: {shortcut_path}")
            return
        except Exception as e:
            print(f"[!] pywin32 failed: {e}, trying PowerShell fallback...")

    # Fallback to PowerShell
    try:
        ps_script = dedent(f"""
            $WshShell = New-Object -ComObject WScript.Shell
            $Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
            $Shortcut.TargetPath = "{exe_path}"
            $Shortcut.Arguments = "daemon"
            $Shortcut.WorkingDirectory = "{Path(exe_path).parent}"
            $Shortcut.Save()
        """).strip()

        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            check=True,
            capture_output=True,
        )
        print(f"[*] Created Windows startup shortcut: {shortcut_path}")
    except Exception as e:
        print(f"[!] Failed to create startup shortcut (both pywin32 and PowerShell): {e}")


def _check_daemon_executable() -> Optional[str]:
    """Check if daemon executable exists on Windows.

    Searches, in order: the directory containing this script/executable
    (the actual "install" location), and the current working directory
    (kept as a secondary fallback for dev/manual runs).
    """
    if sys.platform != "win32":
        return None

    daemon_names = ["app-usage-daemon.exe", "app-usage.exe"]

    search_dirs = []
    try:
        search_dirs.append(Path(sys.argv[0]).resolve().parent)
    except Exception:
        pass
    search_dirs.append(Path.cwd())

    for directory in search_dirs:
        for daemon_name in daemon_names:
            daemon_path = directory / daemon_name
            if daemon_path.exists():
                return str(daemon_path)

    return None


def install_service() -> None:
    if sys.platform == "win32":
        # Check if daemon executable exists
        daemon_exe = _check_daemon_executable()
        if not daemon_exe:
            print("[!] WARNING: Daemon executable not found!")
            print("[!] Without a compiled daemon, a terminal window will appear on every login.")
            print("[!] To avoid this, please download and build the daemon from:")
            print("[!]   https://github.com/jimmythefinest/app-usage-clean")
            print("[!]")
            ans = input("[?] Continue without daemon executable? (y/n): ").strip().lower()
            if ans != "y":
                print("[*] Service installation cancelled.")
                return

        task_name = SERVICE_NAME
        # Build a properly quoted /TR argument in both cases (fixes unquoted
        # path bug when daemon_exe contains spaces, e.g. under Program Files).
        task_cmd = (
            _windows_task_command(daemon_exe)
            if daemon_exe
            else _windows_task_command()
        )

        # Try to install as scheduled task first
        try:
            subprocess.run(
                [
                    "schtasks",
                    "/Create",
                    "/TN",
                    task_name,
                    "/SC",
                    "ONLOGON",
                    "/RL",
                    "LIMITED",
                    "/TR",
                    task_cmd,
                    "/F",
                ],
                check=True,
            )
            print(f"[*] Installed Windows logon task: {task_name}")
            return
        except subprocess.CalledProcessError as e:
            print(f"[!] Failed to create scheduled task: {e}")
            print("[*] Attempting to create startup shortcut instead...")

        # Fall back to startup shortcut.
        # Prefer the daemon executable we already located (if any) so the
        # shortcut matches what the user was warned/consented about; only
        # fall back to searching PATH for the CLI launcher if we never
        # found a daemon exe in the first place.
        shortcut_target = daemon_exe or which(SERVICE_NAME)
        if shortcut_target:
            try:
                _create_startup_shortcut(shortcut_target)
                return
            except Exception as e:
                print(f"[!] Failed to create startup shortcut: {e}")
                print("[!] Unable to register service. Please run as Administrator or install manually.")
                return

        print("[!] Unable to find app-usage executable and failed to create scheduled task.")
        return

    unit_path = _linux_unit_path()
    unit_path.parent.mkdir(parents=True, exist_ok=True)
    unit_path.write_text(_linux_unit_content(), encoding="utf-8")

    try:
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "--user", "enable", "--now", f"{SERVICE_NAME}.service"], check=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"[!] Failed to enable systemd user service: {e}")
        print("[!] The unit file was written, but could not be activated.")
        print("[!] This can happen on systems without a running user systemd instance")
        print("[!] (e.g. some containers, WSL, or headless servers).")
        print(f"[!] Unit file location: {unit_path}")
        return

    print(f"[*] Installed Linux user service: {unit_path}")


def uninstall_service() -> None:
    if sys.platform == "win32":
        subprocess.run(
            ["schtasks", "/Delete", "/TN", SERVICE_NAME, "/F"],
            check=False,
        )
        print(f"[*] Removed Windows logon task: {SERVICE_NAME}")

        # Remove startup shortcut
        startup_dir = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        shortcut_path = startup_dir / "App Usage.lnk"
        if shortcut_path.exists():
            shortcut_path.unlink()
            print(f"[*] Removed Windows startup shortcut: {shortcut_path}")

        return

    unit_path = _linux_unit_path()
    subprocess.run(["systemctl", "--user", "disable", "--now", f"{SERVICE_NAME}.service"], check=False)
    if unit_path.exists():
        unit_path.unlink()
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
    print(f"[*] Removed Linux user service: {unit_path}")