#!/usr/bin/env python3
import argparse
import shlex
import sys
from pathlib import Path
from shutil import which
from app_usage_cli import builder, importer, syncer, tracker, config, hooks, service

def run_build(args):
    print("--- Building Activities ---")
    builder.main()

def run_sync(args):
    print("--- Syncing Repositories ---")
    syncer.main()

def run_import(args):
    print("--- Importing to Obsidian ---")
    importer.main()

def run_all(args):
    run_build(args)
    run_sync(args)
    run_import(args)

def run_daemon(args):
    import sys
    import os
    print("--- Starting App Usage Tracker Daemon ---")
    if sys.platform == "win32":
        from app_usage_cli import tracker_windows
        tracker_windows.main()
    else:
        if os.environ.get("XDG_SESSION_TYPE") == "wayland" and "GNOME" in os.environ.get("XDG_CURRENT_DESKTOP", "").upper():
            from . import tracker_wayland_gnome
            tracker_wayland_gnome.main()
        else:
            from app_usage_cli import tracker
            tracker.main()

def run_config_set_vault(args):
    cfg = config.load_config()
    cfg["vault_dir"] = args.path
    config.save_config(cfg)
    print(f"Vault directory set to: {args.path}")

def run_config_view(args):
    cfg = config.load_config()
    for k, v in cfg.items():
        print(f"{k}: {v}")

def run_config_add_repo(args):
    cfg = config.load_config()
    repos = cfg.setdefault("repositories", [])
    if args.repo in repos:
        print(f"Repository already exists: {args.repo}")
    else:
        repos.append(args.repo)
        config.save_config(cfg)
        print(f"Added repository: {args.repo}")

def run_config_remove_repo(args):
    cfg = config.load_config()
    repos = cfg.get("repositories", [])
    if args.repo not in repos:
        print(f"Repository not found: {args.repo}")
    else:
        repos.remove(args.repo)
        config.save_config(cfg)
        print(f"Removed repository: {args.repo}")


def _resolve_app_usage_path() -> str:
    """Best-effort absolute path to the running app-usage executable/script.

    Shell rc files are sourced in fresh, minimal-PATH shells (and PowerShell
    profiles run in contexts that may not include the install directory), so
    a bare `app-usage` in the hook can fail to resolve even though it worked
    fine in the interactive shell that ran `setup`. Resolve to an absolute
    path up front and bake that into the hook instead.
    """
    # PyInstaller-frozen executable: sys.executable *is* app-usage(.exe).
    if getattr(sys, "frozen", False):
        return str(Path(sys.executable).resolve())

    # Installed console-script on PATH right now (e.g. via pip install).
    found = which("app-usage")
    if found:
        return str(Path(found).resolve())

    # Running as a plain script.
    argv0 = Path(sys.argv[0])
    if argv0.exists():
        return str(argv0.resolve())

    # Last resort: hope it's on PATH wherever the hook eventually runs.
    return "app-usage"


def run_setup(args):
    import os
    import sys
    from pathlib import Path
    
    print("=== App Usage Tracker Setup ===\n")
    
    # 1. Vault Directory
    vault = input("Enter the absolute path to your Obsidian vault: ").strip()
    if not vault:
        print("Setup cancelled.")
        return
        
    vault_path = Path(vault).expanduser().resolve()
    cfg = config.load_config()
    cfg["vault_dir"] = str(vault_path)
    config.save_config(cfg)
    print(f"[*] Vault directory set to: {vault_path}\n")
    
    # 2. Shell Integration
    app_usage_path = _resolve_app_usage_path()

    shell_path = os.environ.get("SHELL", "")
    shell_name = Path(shell_path).name.lower()
    
    if sys.platform == "win32":
        shell_name = "pwsh"
        
    if shell_name in ("bash", "zsh"):
        ans = input(f"Detected {shell_name}. Do you want to enable automatic command logging? (Y/n): ").strip().lower()
        if ans in ("", "y", "yes"):
            rc_file = Path.home() / f".{shell_name}rc"
            quoted_path = shlex.quote(app_usage_path)
            hook_str = f'\n eval "$({quoted_path} hook {shell_name})"\n'
            
            if rc_file.exists() and f"hook {shell_name}" in rc_file.read_text():
                print(f"[*] Command logging already enabled in {rc_file}")
            else:
                with rc_file.open("a") as f:
                    f.write(hook_str)
                print(f"[*] Command logging enabled! Added hook to {rc_file}")
                print(f"    (Please restart your terminal or run `source {rc_file}` to apply)")
    
    elif sys.platform == "win32":
        ans = input("Detected Windows. Do you want to enable automatic command logging in PowerShell? (Y/n): ").strip().lower()
        if ans in ("", "y", "yes"):
            profile_dir = Path.home() / "Documents" / "WindowsPowerShell"
            profile_dir.mkdir(parents=True, exist_ok=True)
            profile_file = profile_dir / "Microsoft.PowerShell_profile.ps1"
            
            hook_str = f'\n Invoke-Expression (& "{app_usage_path}" hook pwsh | Out-String)\n'
            if profile_file.exists() and "hook pwsh" in profile_file.read_text():
                 print(f"[*] Command logging already enabled in {profile_file}")
            else:
                with profile_file.open("a") as f:
                    f.write(hook_str)
                print(f"[*] Command logging enabled! Added hook to {profile_file}")
                print("    (Please restart your PowerShell terminal to apply)")

    # 3. Startup Service
    ans = input("Install the tracker as a background service at login? (Y/n): ").strip().lower()
    if ans in ("", "y", "yes"):
        service.install_service()
        print("    (The daemon will start automatically on your next login, or immediately if your session manager supports it.)")
    
    print("=== Setup Complete! ===")
    print("You can now start the background tracker by running:")
    print(f"    {app_usage_path} daemon")

def run_install_service(args):
    service.install_service()

def run_uninstall_service(args):
    service.uninstall_service()

def interactive_repl():
    """Interactive REPL loop for the CLI."""
    print("App Usage Analytics CLI (Interactive Mode)")
    print("Type 'help' for a list of commands or 'exit' to quit\n")
    
    available_commands = {
        "build": "Process raw analytics into activities",
        "sync": "Sync GitHub repositories and issues",
        "import": "Import activities to Obsidian vault",
        "run-all": "Run build, sync, and import sequentially",
        "daemon": "Run the background tracker daemon",
        "config": "Manage configuration (view, set-vault, add-repo, remove-repo)",
        "setup": "Interactive 1-hit setup wizard",
        "install-service": "Install the daemon as a user-space startup service",
        "uninstall-service": "Remove the startup service",
        "log-command": "Log a command to the daily command log",
        "hook": "Generate shell integration hook",
        "help": "Show this help message",
        "exit": "Exit the interactive mode",
    }
    
    while True:
        try:
            user_input = input("app-usage> ").strip()
            
            if not user_input:
                continue
            
            if user_input == "exit":
                print("Goodbye!")
                break
            
            if user_input == "help":
                print("\nAvailable commands:")
                for cmd, desc in available_commands.items():
                    print(f"  {cmd:<20} {desc}")
                print()
                continue
            
            # Parse the input as if it were command-line arguments
            args_list = user_input.split()
            try:
                args = main_parser().parse_args(args_list)
                if hasattr(args, 'func'):
                    args.func(args)
                else:
                    print(f"Unknown command: {args_list[0]}")
            except SystemExit:
                # argparse calls sys.exit on error, catch it to stay in loop
                pass
            except Exception as e:
                print(f"Error: {e}")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break


def main_parser():
    """Create and return the argument parser (extracted for reuse)."""
    parser = argparse.ArgumentParser(description="App Usage Analytics CLI")
    subparsers = parser.add_subparsers(dest="command", required=False, help="Subcommand to run")

    # Build command
    parser_build = subparsers.add_parser("build", help="Process raw analytics into activities")
    parser_build.set_defaults(func=run_build)

    # Sync command
    parser_sync = subparsers.add_parser("sync", help="Sync GitHub repositories and issues")
    parser_sync.set_defaults(func=run_sync)

    # Import command
    parser_import = subparsers.add_parser("import", help="Import activities to Obsidian vault")
    parser_import.set_defaults(func=run_import)

    # All command
    parser_all = subparsers.add_parser("run-all", help="Run build, sync, and import sequentially")
    parser_all.set_defaults(func=run_all)
    
    # Daemon command
    parser_daemon = subparsers.add_parser("daemon", help="Run the background tracker daemon")
    parser_daemon.set_defaults(func=run_daemon)

    # Config command
    parser_config = subparsers.add_parser("config", help="Manage configuration")
    config_subs = parser_config.add_subparsers(dest="config_command", required=True)
    
    cmd_set_vault = config_subs.add_parser("set-vault", help="Set the Obsidian vault directory")
    cmd_set_vault.add_argument("path", help="Absolute path to your vault")
    cmd_set_vault.set_defaults(func=run_config_set_vault)
    
    cmd_view = config_subs.add_parser("view", help="View current configuration")
    cmd_view.set_defaults(func=run_config_view)

    cmd_add_repo = config_subs.add_parser("add-repo", help="Add a GitHub repository to sync")
    cmd_add_repo.add_argument("repo", help="Repository in owner/name format (e.g. jimmythefinest/SIMP)")
    cmd_add_repo.set_defaults(func=run_config_add_repo)

    cmd_remove_repo = config_subs.add_parser("remove-repo", help="Remove a GitHub repository")
    cmd_remove_repo.add_argument("repo", help="Repository in owner/name format")
    cmd_remove_repo.set_defaults(func=run_config_remove_repo)
    
    # setup command
    parser_setup = subparsers.add_parser("setup", help="Interactive 1-hit setup wizard")
    parser_setup.set_defaults(func=run_setup)

    # service commands
    parser_install_service = subparsers.add_parser("install-service", help="Install the daemon as a user-space startup service")
    parser_install_service.set_defaults(func=run_install_service)

    parser_uninstall_service = subparsers.add_parser("uninstall-service", help="Remove the startup service")
    parser_uninstall_service.set_defaults(func=run_uninstall_service)
    
    # log-command command
    parser_log_cmd = subparsers.add_parser("log-command", help="Log a command to the daily command log")
    parser_log_cmd.add_argument("cwd", help="Current working directory")
    parser_log_cmd.add_argument("command_string", help="The command string executed")
    parser_log_cmd.set_defaults(func=hooks.log_command)
    
    # hook command
    parser_hook = subparsers.add_parser("hook", help="Generate shell integration hook")
    parser_hook.add_argument("shell", choices=["bash", "zsh", "pwsh", "powershell"], help="Target shell")
    parser_hook.set_defaults(func=hooks.generate_hook)
    
    return parser


def main():
    parser = main_parser()
    args = parser.parse_args()
    
    # If no command provided, enter interactive mode
    if not args.command:
        interactive_repl()
        return
    
    # Otherwise execute the command
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()