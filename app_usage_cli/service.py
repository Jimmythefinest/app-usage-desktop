import shlex
import subprocess
import sys
from shutil import which
from pathlib import Path
from textwrap import dedent

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


def _windows_task_command() -> str:
    return subprocess.list2cmdline(_launcher_command())


def install_service() -> None:
    if sys.platform == "win32":
        task_name = SERVICE_NAME
        task_cmd = _windows_task_command()
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

    unit_path = _linux_unit_path()
    unit_path.parent.mkdir(parents=True, exist_ok=True)
    unit_path.write_text(_linux_unit_content(), encoding="utf-8")

    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", f"{SERVICE_NAME}.service"], check=True)
    print(f"[*] Installed Linux user service: {unit_path}")


def uninstall_service() -> None:
    if sys.platform == "win32":
        subprocess.run(
            ["schtasks", "/Delete", "/TN", SERVICE_NAME, "/F"],
            check=False,
        )
        print(f"[*] Removed Windows logon task: {SERVICE_NAME}")
        return

    unit_path = _linux_unit_path()
    subprocess.run(["systemctl", "--user", "disable", "--now", f"{SERVICE_NAME}.service"], check=False)
    if unit_path.exists():
        unit_path.unlink()
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
    print(f"[*] Removed Linux user service: {unit_path}")
