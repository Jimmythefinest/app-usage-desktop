import json
import os
import sys
from datetime import datetime
from pathlib import Path
from . import config

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
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def generate_hook(args):
    """
    Generates the appropriate shell hook based on the requested shell.
    """
    shell = args.shell.lower()
    
    # Notice we don't output color or fluff, just pure bash/zsh/pwsh code
    # to be eval'd by the shell.
    
    if shell == "bash":
        # Bash hook using PROMPT_COMMAND
        # We capture history right after the command runs
        print('''\
__app_usage_log_command() {
    local cmd
    # Get the last command from history and strip the leading number and spaces
    cmd=$(history 1 | sed -e 's/^[ ]*[0-9]*[ ]*//')
    # Skip empty commands or duplicate history commands
    if [ -n "$cmd" ]; then
        app-usage log-command "$PWD" "$cmd"
    fi
}
# Append to PROMPT_COMMAND safely
if [[ "$PROMPT_COMMAND" != *__app_usage_log_command* ]]; then
    PROMPT_COMMAND="__app_usage_log_command; ${PROMPT_COMMAND:-}"
fi
''')
    elif shell == "zsh":
        # Zsh hook using preexec
        # preexec passes the exact typed command as $1
        print('''\
__app_usage_log_command() {
    app-usage log-command "$PWD" "$1"
}
autoload -Uz add-zsh-hook
add-zsh-hook preexec __app_usage_log_command
''')
    elif shell in ("pwsh", "powershell"):
        # PowerShell uses PSReadLine history
        print('''\
$__appUsagePreviousCommand = ""
Set-PSReadLineOption -HistorySaveStyle SaveIncrementally

function __appUsagePromptHook {
    $hist = Get-History -Count 1
    if ($hist) {
        $cmd = $hist.CommandLine.Trim()
        if ($cmd -ne "" -and $cmd -ne $global:__appUsagePreviousCommand) {
            $global:__appUsagePreviousCommand = $cmd
            app-usage log-command "$PWD" "$cmd"
        }
    }
}

# Attach to the Prompt function
$global:PromptBackup = $function:prompt
$function:prompt = {
    __appUsagePromptHook
    & $global:PromptBackup
}
''')
    else:
        print(f"echo 'Error: Unsupported shell {shell}. Supported: bash, zsh, pwsh'", file=sys.stderr)
        sys.exit(1)
