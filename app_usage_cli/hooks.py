import json
import os
import shlex
import sys
from datetime import datetime
from pathlib import Path
from  app_usage_cli import config


def _resolve_hook_command() -> str:
    """Best-effort absolute path to the app executable or script used by hooks."""
    if getattr(sys, "frozen", False):
        return str(Path(sys.executable).resolve())

    script_path = Path(sys.argv[0]).expanduser()
    if script_path.is_absolute():
        return str(script_path.resolve())

    if sys.executable:
        return str(Path(sys.executable).resolve())

    return "app-usage"


def _quote_for_shell(path: str, shell: str) -> str:
    if shell in ("pwsh", "powershell"):
        return '"' + path.replace('"', '`"') + '"'
    return shlex.quote(path)


def log_command(args):
    """
    Logs a command directly to the current day's command log file.
    Used by the shell integrations.
    """
    cwd = args.cwd
    command = args.command_string
    
    # We use timezone-aware ISO formats in commands
    now = datetime.now().astimezone()
    
    entry = {
        "timestamp": now.isoformat(),
        "command": command,
        "cwd": cwd
    }
    
    log_dir = config.get_command_logs_dir()
    log_file = log_dir / f"{now:%Y-%m-%d}.jsonl"
    if not log_dir.exists():
        log_dir.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def generate_hook(args):
    """
    Generates the appropriate shell hook based on the requested shell.
    """
    shell = args.shell.lower()
    
    # Notice we don't output color or fluff, just pure bash/zsh/pwsh code
    # to be eval'd by the shell.
    
    command_path = _resolve_hook_command()
    quoted_command = _quote_for_shell(command_path, shell)

    if shell == "bash":
        # Bash hook using PROMPT_COMMAND
        # We capture history right after the command runs
        print(f'''\
__app_usage_log_command() {{
    local cmd
    # Get the last command from history and strip the leading number and spaces
    cmd=$(history 1 | sed -e 's/^[ ]*[0-9]*[ ]*//')
    # Skip empty commands or duplicate history commands
    if [ -n "$cmd" ]; then
        {quoted_command} log-command "$PWD" "$cmd"
    fi
}}
# Append to PROMPT_COMMAND safely
if [[ "$PROMPT_COMMAND" != *__app_usage_log_command* ]]; then
    PROMPT_COMMAND="__app_usage_log_command; ${{PROMPT_COMMAND:-}}"
fi
''')
    elif shell == "zsh":
        # Zsh hook using preexec
        # preexec passes the exact typed command as $1
        print(f'''\
__app_usage_log_command() {{
    {quoted_command} log-command "$PWD" "$1"
}}
autoload -Uz add-zsh-hook
add-zsh-hook preexec __app_usage_log_command
''')
    elif shell in ("pwsh", "powershell"):
        # PowerShell uses PSReadLine history
        print(f'''\
if (-not (Get-Variable -Name __appUsagePreviousCommand -Scope Script -ErrorAction SilentlyContinue)) {{
    $script:__appUsagePreviousCommand = ""
}}
Set-PSReadLineOption -HistorySaveStyle SaveIncrementally

function __appUsagePromptHook {{
    $hist = Get-History -Count 1
    if ($hist) {{
        $cmd = $hist.CommandLine.Trim()
        if ($cmd -and $cmd -ne $script:__appUsagePreviousCommand) {{
            $script:__appUsagePreviousCommand = $cmd
            & {quoted_command} log-command "$PWD" "$cmd"
        }}
    }}
}}

# Only wrap the prompt once. If this hook is sourced more than once (e.g. a
# nested pwsh session, or setup run twice), re-wrapping an already-wrapped
# prompt via a global backup variable would make the backup point back to
# itself and recurse infinitely. Guard with a flag instead of blindly
# re-capturing $function:prompt every time.
if (-not $global:__appUsagePromptHooked) {{
    $global:__appUsagePromptHooked = $true
    $global:AppUsagePromptBackup = $function:prompt

    function global:prompt {{
        __appUsagePromptHook
        & $global:AppUsagePromptBackup
    }}
}}
''')
    else:
        print(f"echo 'Error: Unsupported shell {shell}. Supported: bash, zsh, pwsh'", file=sys.stderr)
        sys.exit(1)