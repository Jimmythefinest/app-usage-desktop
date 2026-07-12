# app-usage CLI

A cross-platform (Linux & Windows) app usage tracker that logs active window focus, idle time, and shell commands, then processes and exports them as structured notes to an [Obsidian](https://obsidian.md/) vault.

---

## Installation

### Linux (Debian/Ubuntu) — via .deb package
```bash
sudo dpkg -i app-usage_0.1.0_amd64.deb
```
> This is the only step that requires admin (`sudo`). Everything after this — setup, shell hooks, and the startup service — runs entirely in user space with no elevated permissions required.

### Any Platform — via pip
Requires **Python 3.10+**.
```bash
cd cli/
pip install .
```

---

## Quick Start

Run the interactive setup wizard. It handles everything in one shot:
```bash
app-usage setup
```

The wizard will ask you:
1. **Your Obsidian vault path** — saves to config automatically.
2. **Enable command logging?** — appends the correct hook to your shell config (`~/.bashrc`, `~/.zshrc`, or PowerShell `$PROFILE`) based on what you're running.
3. **Install startup service?** — registers the daemon to start automatically at every login. No admin required.

Then add any GitHub repos you want to sync (optional):
```bash
app-usage config add-repo owner/repo-name
```

---

## Commands

### `app-usage setup`
Interactive one-hit setup wizard. Configures vault, shell hooks, and startup service in one go.

---

### `app-usage daemon`
Starts the background tracker daemon. Logs active window focus, title changes, idle state, and lock/unlock events to daily `.jsonl` files in `~/.local/share/app_usage/analytics/`.

Also runs a full `build → sync → import` pipeline every **10 minutes** in the background automatically.

> **Note:** The correct backend is selected automatically:
> - **Linux X11** → `xdotool`/`xprintidle`-based tracker
> - **Linux GNOME Wayland** → native DBus tracker (requires GNOME extension, see below)
> - **Windows** → native `ctypes` Windows API tracker

---

### `app-usage install-service`
Installs the daemon as a login-time service without admin privileges.

- **Linux** — Writes a user service unit at `~/.config/systemd/user/app-usage.service`, then enables it with `systemctl --user`.
- **Windows** — Creates a per-user Task Scheduler logon task that runs `app-usage daemon`.

```bash
# Install
app-usage install-service

# Check status (Linux)
systemctl --user status app-usage

# Remove service
app-usage uninstall-service
```

---

### `app-usage uninstall-service`
Stops and removes the user-space startup registration for the current platform.

---

### `app-usage build`
Processes raw analytics logs into structured activity JSON files.

- Reads from: `~/.local/share/app_usage/analytics/*.jsonl`
- Also reads shell commands from: `~/.local/share/app_usage/commands/*.jsonl`
- Outputs to: `~/.local/share/app_usage/activities/*.json`

Each **Activity** represents a single window/app session, including:
- Total elapsed and focused time
- Focus intervals (paused on idle/lock)
- Window titles seen
- Shell commands run during the session

---

### `app-usage sync`
Fetches commits and issues from configured GitHub repositories using the `gh` CLI.

- Writes commit notes to: `<vault>/commits/`
- Writes project notes to: `<vault>/projects/`
- Requires `gh` CLI to be installed and authenticated.

---

### `app-usage import`
Imports processed activities into your Obsidian vault as Markdown notes with YAML frontmatter queryable via [Dataview](https://github.com/blacksmithgu/obsidian-dataview).

- Reads from: `~/.local/share/app_usage/activities/`
- Outputs to: `<vault>/Activities/`
- Idempotent: re-running preserves any manual edits (session links, tags, etc.)

---

### `app-usage run-all`
Runs `build` → `sync` → `import` sequentially in one command.

---

### `app-usage config`

Manage your global configuration stored at `~/.config/app_usage/config.json`.

| Subcommand | Description |
|---|---|
| `config view` | Print current configuration |
| `config set-vault <path>` | Set the Obsidian vault directory |
| `config add-repo <owner/repo>` | Add a GitHub repository to sync |
| `config remove-repo <owner/repo>` | Remove a GitHub repository |

---

## Shell Command Logging

You can securely log every command you type in your terminal to your activity notes. We support **Bash**, **Zsh**, and **PowerShell** out of the box.

`app-usage setup` will configure this automatically. To add it manually:

**Bash (`~/.bashrc`)**:
```bash
eval "$(app-usage hook bash)"
```

**Zsh (`~/.zshrc`)**:
```zsh
eval "$(app-usage hook zsh)"
```

**PowerShell (`$PROFILE`)**:
```powershell
Invoke-Expression (& app-usage hook pwsh | Out-String)
```

---

## Data Directories

| Path | Contents |
|---|---|
| `~/.config/app_usage/config.json` | Global settings (vault, repos) |
| `~/.local/share/app_usage/analytics/` | Raw daily event logs (`.jsonl`) |
| `~/.local/share/app_usage/commands/` | Shell command logs (`.jsonl`) |
| `~/.local/share/app_usage/activities/` | Processed activity files (`.json`) |
| `~/.local/share/app_usage/github/` | Fetched GitHub data (`.json`) |

> On **Windows**, all data directories are located under `%LOCALAPPDATA%\app_usage\`.

---

## Obsidian Vault Structure

After running `app-usage run-all`, your vault will contain:

```
<vault>/
  Activities/        ← One note per tracked app session
  commits/           ← One note per git commit
  projects/          ← One note per GitHub repo (with Dataview commit table)
```

Each Activity note includes a `session:` field you can populate to link it to a Session note, and a `commands:` list of shell commands run during that window.

---

## Dependencies

| Package | Used For | Platform |
|---|---|---|
| `psutil` | Process name & executable lookup | Both |
| `dbus-next` | Screen lock & Wayland detection | Linux only |
| `xdotool` | Active window & PID detection | Linux (X11) |
| `xprintidle` | Idle time detection | Linux (X11) |
| `gh` CLI | GitHub commit & issue fetching | Both (optional) |

### Linux X11 System Dependencies:
```bash
sudo apt install xdotool xprintidle  # Debian/Ubuntu
```

### Linux GNOME Wayland Requirements:
Because Wayland blocks apps from seeing active windows, you must install the bundled GNOME extension.
```bash
# Install the extension
cp -r gnome-extension/app-usage-tracker@jimmy.example.com ~/.local/share/gnome-shell/extensions/
# Enable it
gnome-extensions enable app-usage-tracker@jimmy.example.com
```
After enabling, `app-usage daemon` will automatically detect Wayland and use DBus instead of X11 tools.

---

## Developer Guide: Porting to New Desktop Environments

The daemon architecture is highly modular to support the massive fragmentation of window management on Linux (especially Wayland).

If you want to add support for a new Desktop Environment (e.g., **KDE Plasma Wayland**, **Sway/Wlroots**, or **macOS**):

1. **Create a new tracker backend:**
   Create a new file in `app_usage_cli/` (e.g., `tracker_wayland_kde.py` or `tracker_mac.py`).
   
   Your tracker needs to implement a `main()` function containing an infinite loop that periodically logs events (`FOCUS`, `TITLE`, `IDLE`, `ACTIVE`, `LOCK`, `UNLOCK`) into `.jsonl` files in `config.get_analytics_dir()`.

   *Look at `tracker_wayland_gnome.py` as a modern, `asyncio`-based reference template.*

2. **Update the Router:**
   Open `app_usage_cli/cli.py` and modify the `run_daemon()` function. 
   Add a new `elif` branch to detect the environment variables for your target system, and route to your new tracker:

   ```python
   def run_daemon(args):
       # ...
       if os.environ.get("XDG_SESSION_TYPE") == "wayland":
           desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
           if "GNOME" in desktop:
               from . import tracker_wayland_gnome
               tracker_wayland_gnome.main()
           elif "KDE" in desktop:
               # Route to your new KDE tracker here!
               from . import tracker_wayland_kde
               tracker_wayland_kde.main()
   ```

3. **Re-install locally:**
   Run `pip install .` to apply your CLI routing changes.
