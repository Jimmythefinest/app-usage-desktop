from pathlib import Path
import sys

from app_usage_cli import hooks


class Args:
    def __init__(self, shell: str):
        self.shell = shell


def test_powershell_hook_uses_prompt_based_logging(capsys):
    hooks.generate_hook(Args("pwsh"))
    output = capsys.readouterr().out

    assert '$__appUsagePreviousCommand = ""' in output
    assert 'function __appUsagePromptHook' in output
    assert 'function global:prompt' in output
    assert 'log-command "$PWD" "$cmd"' in output


def test_hook_uses_resolved_path(monkeypatch, capsys):
    monkeypatch.setattr(hooks, '_resolve_hook_command', lambda: str(Path(r"C:\\temp\\app-usage.exe")))
    hooks.generate_hook(Args("pwsh"))
    output = capsys.readouterr().out

    assert r'& "C:\temp\app-usage.exe" log-command "$PWD" "$cmd"' in output
