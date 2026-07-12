---
type: project
status: active
priority: high
stage: development
created: <% tp.date.now("YYYY-MM-DD") %>
updated: <% tp.date.now("YYYY-MM-DD") %>
completion: 65
tags:
  - project
  - python
  - linux
  - windows
  - obsidian
  - productivity
  - analytics
  - github
domain:
  - Desktop Analytics
  - Productivity
  - Knowledge Management
stack:
  - Python
  - Typer
  - psutil
  - xdotool
  - GitHub API
  - JSONL
  - Markdown
  - Obsidian
  - systemd
  - Windows Task Scheduler
repository: https://github.com/Jimmythefinest/app-usage-desktop/
documentation:
demo:
related:
  - - - Obsidian Plugin
  - - - Desktop Activity Tracking
  - - - GitHub Integration
objectives:
  - Record desktop activity with minimal overhead.
  - Convert activity into meaningful work sessions.
  - Integrate GitHub activity.
  - Automatically generate Obsidian notes.
  - Build a personal productivity knowledge base.
problems:
  - Window titles change frequently and create noisy data.
  - Background processes should not count as user activity.
  - Shell command logging must work across multiple shells.
  - Activity imports must remain idempotent.
  - Cross-platform startup requires different implementations.
next_actions:
  - Improve activity session detection.
  - Add configurable session merge/split rules.
  - Expand GitHub synchronization.
  - Improve Obsidian templates.
  - Package binaries for Windows and Linux.
deadline:
---

# App Usage Obsidian intergration

## Overview

App Usage Clean is a desktop activity tracking application that records user interaction with applications, windows, and shell commands. It processes raw analytics into structured work sessions and automatically exports them into an Obsidian vault as Markdown notes.

The project exists to create a searchable personal productivity database that combines desktop usage, GitHub activity, and notes into a single knowledge system.

The intended outcome is a lightweight, cross-platform productivity tool that can later serve as the foundation for an Obsidian plugin and AI-powered personal assistant.

---

# Goals

## Short Term
- [ ] Finish activity processing pipeline
- [x] Improve session generation
- [ ] Improve GitHub synchronization
- [x] Stabilize command logging
- [x] Improve CLI experience

## Mid Term
- [x] Publish first public release
- [ ] Add plugin architecture
- [ ] Support configurable workflows
- [ ] Improve analytics reporting
- [ ] Create documentation

## Long Term
- [ ] Full Obsidian plugin
- [ ] AI-assisted activity summaries
- [ ] Multi-device synchronization
- [ ] Calendar integration
- [ ] Open-source community contributions

---

# Requirements

## Functional

- Track focused applications
- Track window titles
- Detect idle periods
- Record lock/unlock events
- Record shell commands
- Import activities into Obsidian
- Synchronize GitHub commits and issues
- Generate Markdown notes
- Support incremental imports

## Technical

- Cross-platform
- Lightweight background service
- JSONL-based logging
- CLI-driven workflow
- Idempotent imports
- Configurable storage paths

## Constraints

- Low CPU usage
- Low memory usage
- Privacy-first local storage
- No database dependency
- Offline-first operation

---

# Architecture

## High Level

```text
Desktop Events
      ↓
Analytics Logger
      ↓
JSONL Files
      ↓
Activity Builder
      ↓
GitHub Sync
      ↓
Markdown Importer
      ↓
Obsidian Vault
```

## Components

### Frontend

- CLI
- Obsidian Markdown Notes

### Backend

- Analytics collector
- Activity builder
- GitHub synchronizer
- Markdown importer

### Database

- JSONL
- JSON configuration
- Markdown
- YAML frontmatter

### AI / Logic

- Activity segmentation
- Session merging
- Focus analysis
- Command association

### Infrastructure

- systemd user service
- Windows Task Scheduler
- Startup shortcut fallback

---

# Data Model

## Entities

| Entity | Purpose |
|---|---|
| Analytics Event | Raw desktop event |
| Activity | Processed work session |
| Command | Logged shell command |
| GitHub Commit | Imported commit |
| GitHub Issue | Imported issue |
| Project | Related repository/project |
| Configuration | User settings |

---

# APIs / Interfaces

| Name | Purpose |
|---|---|
| Analytics Logger | Record desktop events |
| Activity Builder | Generate activities |
| GitHub API | Import commits/issues |
| Markdown Importer | Create Obsidian notes |
| CLI | User interaction |

---

# Research

## Topics

- Activity tracking
- Session detection
- Knowledge management
- Obsidian workflows
- GitHub automation

## References

- Obsidian documentation
- GitHub REST API
- systemd documentation
- Windows Task Scheduler

## Papers

- Human-computer interaction
- Personal knowledge management

## Tutorials

- Typer CLI
- psutil
- xdotool

---

# Experiments

| Date | Experiment | Result |
|---|---|---|
| 2026-07 | Window focus tracking | Successful |
| 2026-07 | Command logging hooks | Successful |
| 2026-07 | Obsidian import pipeline | Successful |
| 2026-07 | GitHub synchronization | Working |

---

# Tasks

## Todo

- [ ] Improve session editing
- [ ] Add configuration UI
- [ ] Add plugin support
- [ ] Better analytics summaries
- [ ] Improve documentation

## In Progress

- [ ] Activity generation improvements
- [ ] GitHub synchronization

## Blocked

- [ ] Obsidian plugin development

## Done

- [x] Window tracking
- [x] Idle detection
- [x] Lock/unlock tracking
- [x] Markdown importing
- [x] Command logging
- [x] GitHub syncing
- [x] Cross-platform startup

---

# Bugs / Issues

| Issue | Cause | Status |
|---|---|---|
| Shell hook path issues | Relative executable paths | Fixed |
| Duplicate imports | Missing activity mapping | Fixed |
| Cross-platform startup differences | OS-specific services | Mitigated |

---

# Ideas

- AI-generated daily summaries
- Timeline visualization
- Automatic work categorization
- Calendar export
- Time tracking dashboard
- Obsidian plugin with editable sessions
- Team analytics mode

---

# Decisions

| Decision | Reason |
|---|---|
| JSONL instead of database | Simple, portable, append-only |
| Markdown output | Native Obsidian compatibility |
| Idempotent imports | Prevent duplicate notes |
| CLI-first design | Easy automation |
| Local-first storage | Privacy and reliability |

---

# Metrics

| Metric | Value |
|---|---|
| Completion | 65% |
| Platforms | Linux, Windows |
| CLI Commands | Growing |
| Supported Shells | Bash, Zsh, PowerShell |

---

# Risks

| Risk | Impact | Mitigation |
|---|---|---|
| OS-specific behavior | High | Abstract platform differences |
| Activity noise | Medium | Better filtering algorithms |
| Large analytics files | Medium | Incremental processing |
| Obsidian format changes | Low | Configurable templates |

---

# Notes

This project is intended to become the foundation for a complete personal productivity ecosystem centered around Obsidian. Future versions may include an Obsidian plugin, AI-assisted summaries, customizable activity processing, and integrations with additional developer tools.

---

# Daily Logs

## <% tp.date.now("YYYY-MM-DD") %>

### Worked On

- Release preparation
- Obsidian importer improvements
- Command logging
- Service installation
- GitHub synchronization

### Problems

- Reliable shell hook installation
- Session generation heuristics
- Cross-platform startup differences

### Discoveries

- Idempotent imports greatly simplify repeated workflows.
- Focused-window tracking produces cleaner activity data than process monitoring alone.
- Markdown with YAML frontmatter integrates naturally with Obsidian.

### Next

- Improve session editing.
- Finish plugin architecture.
- Publish the first public release.