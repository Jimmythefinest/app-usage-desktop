# app-usage (Obsidian Export Layer)

A cross-platform app usage tracker that adds an **analytics resolution/export layer** specifically for **Obsidian** notes—turning raw app-focus + idle events (and optional shell command logs) into structured, queryable Markdown content for your vault.

(Uses app-usage tracking data and exports it into an Obsidian vault.)

---

## Installation

### Windows (Easiest for Non-Developers)

This project is a **resolution/export layer on top of app-usage analytics**, turning your raw tracking data into **Obsidian-ready notes**.

1. Download the latest Windows standalone **`.zip`** from the Releases page.
2. Extract the zip to a **permanent folder** on your PC (example: `C:\app-usage\app-usage-portable`).
3. **Keep both executables together** in that same folder (the CLI and the daemon).
4. Open the folder.
5. Run the **CLI** by starting:
   - `app-usage.exe`
   - then Typing setup
   The setup wizard will:
   - ask for your Obsidian vault location
   - enable shell command logging (shell hooks; Windows uses PowerShell-style integration)
   - install the tracker so it runs automatically at login

6. Optional: start tracking manually with:
   - `app-usage.exe daemon`

> Tip: you can also run the setup without PowerShell by double-clicking `app-usage.exe` and choosing `setup` in the menu/terminal prompt.

> Important: do not split the executables into different directories. The Windows service/launcher expects them to live together in the installed folder.

---

### Windows data/export behavior

The tracker daemon runs in the background and will **periodically auto-sync** data for:
- GitHub commit/project notes (via configured repos)
- Activity/build/import into your Obsidian vault

The generated notes are intended primarily for **machine-generated, queryable history** in Obsidian (and commit/project notes), not human-authored journaling.

### Linux & Advanced Users (via prebuilt binary)

Download the attached Linux standalone binary (if provided by the release), move it to a permanent location, then run `setup`.

1. Move the binary to a permanent folder (example):
   - `~/usr/bin/` (or `/usr/local/bin/` if you prefer; you may need sudo)
2. Make sure it is executable:
   - `chmod +x app-usage`
3. Run:
   - `./app-usage setup`

The setup wizard will guide you to your Obsidian vault location.

> The daemon runs in the background and will periodically auto-sync activity/build/import into your vault.

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
               from  app_usage_cli import tracker_wayland_gnome
               tracker_wayland_gnome.main()
           elif "KDE" in desktop:
               # Route to your new KDE tracker here!
               from  app_usage_cli import tracker_wayland_kde
               tracker_wayland_kde.main()
   ```

3. **Re-install locally:**
   Run `pip install .` to apply your CLI routing changes.
