#!/usr/bin/env python3
import argparse
import sys
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
        from . import tracker_windows
        tracker_windows.main()
    else:
        if os.environ.get("XDG_SESSION_TYPE") == "wayland" and "GNOME" in os.environ.get("XDG_CURRENT_DESKTOP", "").upper():
            from . import tracker_wayland_gnome
            tracker_wayland_gnome.main()
        else:
            from . import tracker
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
    shell_path = os.environ.get("SHELL", "")
    shell_name = Path(shell_path).name.lower()
    
    if sys.platform == "win32":
        shell_name = "pwsh"
        
    if shell_name in ("bash", "zsh"):
        ans = input(f"Detected {shell_name}. Do you want to enable automatic command logging? (Y/n): ").strip().lower()
        if ans in ("", "y", "yes"):
            rc_file = Path.home() / f".{shell_name}rc"
            hook_str = f'\n eval "$(app-usage hook {shell_name})"\n'
            
            if rc_file.exists() and f"app-usage hook {shell_name}" in rc_file.read_text():
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
            
            hook_str = '\n Invoke-Expression (& app-usage hook pwsh | Out-String)\n'
            if profile_file.exists() and "app-usage hook pwsh" in profile_file.read_text():
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
    print("    app-usage daemon")

def run_install_service(args):
    service.install_service()

def run_uninstall_service(args):
    service.uninstall_service()

def main():
    parser = argparse.ArgumentParser(description="App Usage Analytics CLI")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Subcommand to run")

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

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
