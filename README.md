# app-usage CLI

A cross-platform (Linux & Windows) app usage tracker that logs active window focus, idle time, and shell commands, then processes and exports them as structured notes to an [Obsidian](https://obsidian.md/) vault.

---

## Installation

### Windows (Easiest for Non-Developers)

1. Download the latest Windows standalone executable (`app-usage.exe` or `.zip`) from the Releases page (or use `build_windows.bat` to generate one).
2. Extract the `.zip` file (if downloaded) to a folder (e.g., `C:\app-usage`).
3. Open Command Prompt or PowerShell in that folder to run the tool, or add the folder to your system's `PATH` to use the `app-usage` command from anywhere.

### Linux & Advanced Users (via Python)

Requires **Python 3.10+** and a virtual environment or system Python with pip.

```bash
# Clone or copy the cli/ directory to your machine
cd cli/
pip install .
```

This installs the `app-usage` command globally in your environment.

---

## Quick Start

```bash
# 1. Set your Obsidian vault location
app-usage config set-vault /path/to/your/obsidian/vault

# 2. Add GitHub repos to sync (optional)
app-usage config add-repo owner/repo-name

# 3. Start the background tracker daemon
app-usage daemon

# 4. At any time, process and export everything
app-usage run-all
```

---

## Commands

### `app-usage daemon`
Starts the background tracker daemon. Logs active window focus, title changes, idle state, and lock/unlock events to daily `.jsonl` files in `~/.local/share/app_usage/analytics/`.

> **Note:** On Linux X11, runs the `xdotool`/`xprintidle`-based tracker.
> On Linux Wayland (GNOME), uses native DBus with a custom GNOME extension.
> On Windows, uses the native `ctypes` Windows API tracker automatically.

---

### `app-usage build`
Processes raw analytics logs into structured activity JSON files.

- Reads from: `~/.local/share/app_usage/analytics/*.jsonl`
- Also reads shell commands from: `~/.command_logs/*.jsonl` (if present)
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

## Data Directories

| Path | Contents |
|---|---|
| `~/.config/app_usage/config.json` | Global settings (vault, repos) |
| `~/.local/share/app_usage/analytics/` | Raw daily event logs (`.jsonl`) |
| `~/.local/share/app_usage/activities/` | Processed activity files (`.json`) |
| `~/.local/share/app_usage/github/` | Fetched GitHub data (`.json`) |
| `~/.command_logs/` | Shell command logs (optional, external) |

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
cp -r cli/gnome-extension/app-usage-tracker@jimmy.example.com ~/.local/share/gnome-shell/extensions/
# Enable it
gnome-extensions enable app-usage-tracker@jimmy.example.com
```
After enabling, `app-usage daemon` will automatically detect Wayland and use DBus instead of X11 tools!

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
