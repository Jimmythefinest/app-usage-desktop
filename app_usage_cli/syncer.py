#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path
from textwrap import dedent
from . import config

OUTPUT_DIR = config.get_github_dir()

OBSIDIAN_VAULT_DIR = config.get_vault_dir()
COMMITS_DIR = OBSIDIAN_VAULT_DIR / "commits"
PROJECTS_DIR = OBSIDIAN_VAULT_DIR / "projects"
COMMITS_DIR.mkdir(parents=True, exist_ok=True)
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

DATAVIEW_START = "%% commit-history:start %%"
DATAVIEW_END = "%% commit-history:end %%"

def repo_slug(repo: str) -> str:
    return repo.replace("/", "-")

def yaml_str(value: str) -> str:
    return json.dumps(value)

def run_gh_command(args):
    try:
        result = subprocess.run(["gh"] + args, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running 'gh {' '.join(args)}': {e.stderr.strip()}")
        return None

def parse_date_string(date_str: str) -> str:
    return date_str.split("T")[0]

def get_commits(repo: str, limit: int = 30):
    output = run_gh_command(["api", f"repos/{repo}/commits?per_page={limit}"])
    if not output: return []
    try:
        raw_commits = json.loads(output)
    except json.JSONDecodeError:
        return []
    
    commits = []
    for c in raw_commits:
        ci = c.get("commit", {})
        ai = ci.get("author", {})
        commits.append({
            "sha": c.get("sha"),
            "message": ci.get("message", "").split("\n")[0],
            "author": ai.get("name", "unknown"),
            "date": ai.get("date"),
        })
    print(len(commits))
    return commits

def get_issues(repo: str, limit: int = 30):
    output = run_gh_command(["issue", "list", "--repo", repo, "--limit", str(limit), "--json", "number,title,state,createdAt,updatedAt,url,labels"])
    return json.loads(output) if output else []

def write_commit_note(repo: str, commit: dict, commits_dir: Path = COMMITS_DIR):
    short_sha = commit["sha"][:7] if commit.get("sha") else "unknown"
    note_id = f"commit_{repo_slug(repo)}_{short_sha}"
    note_path = commits_dir / f"{note_id}.md"

    if note_path.exists(): return

    date, time_str = commit['date'].split('T') if commit.get('date') else ("", "Z")
    
    content = dedent(f"""\
        ---
        type: Commit
        id: {note_id}
        repo: {yaml_str(repo)}
        project: "[[proj_{repo_slug(repo)}]]"
        sha: {yaml_str(commit.get('sha', ''))}
        short_sha: {yaml_str(short_sha)}
        message: {yaml_str(commit.get('message', ''))}
        author: {yaml_str(commit.get('author', ''))}
        date: {date}
        time: {yaml_str(time_str.replace('Z', ''))}
        url: {yaml_str(f"https://github.com/{repo}/commit/{commit['sha']}" if commit.get("sha") else "")}
        sessions: []
        ---
        """)
    note_path.write_text(content, encoding="utf-8")
    print(f" -> Wrote commit note {note_path}")

def ensure_project_note(repo: str, projects_dir: Path = PROJECTS_DIR):
    note_id = f"proj_{repo_slug(repo)}"
    note_path = projects_dir / f"{note_id}.md"
    
    dataview_block = dedent(f"""\
        {DATAVIEW_START}
        ```dataview
        TABLE date, time, message, author, sessions
        FROM "commits"
        WHERE repo = "{repo}"
        SORT date DESC, time DESC
        ```
        {DATAVIEW_END}""")

    if note_path.exists():
        existing = note_path.read_text(encoding="utf-8")
        if DATAVIEW_START in existing and DATAVIEW_END in existing:
            pre, post = existing.split(DATAVIEW_START)[0], existing.split(DATAVIEW_END)[1]
            note_path.write_text(pre + dataview_block + post, encoding="utf-8")
        else:
            note_path.write_text(existing.rstrip("\n") + "\n\n" + dataview_block + "\n", encoding="utf-8")
        return

    content = dedent(f"""\
        ---
        type: Project
        id: {note_id}
        repo: {yaml_str(repo)}
        ---
        
        # {repo}
        
        ## Commit History
        
        {dataview_block}
        """)
    note_path.write_text(content, encoding="utf-8")
    print(f" -> Created project note {note_path}")

def main():
    cfg = config.load_config()
    repos = cfg.get("repositories", [])
    if not repos:
        print("No repositories configured in global config.")
        return

    daily_logs = {}

    for repo in repos:
        print(f"Syncing direct metrics for {repo}...")
        
        commits = get_commits(repo)
        if commits:
            ensure_project_note(repo)
            for c in commits:
                write_commit_note(repo, c)
                day = parse_date_string(c["date"])
                day_log = daily_logs.setdefault(day, {"commits": [], "issues": []})
                day_log["commits"].append({
                    "repo": repo, "sha": c["sha"], "message": c["message"],
                    "author": c["author"], "time": c["date"].split("T")[1].replace("Z", "")
                })

        for i in get_issues(repo):
            day = parse_date_string(i["updatedAt"])
            day_log = daily_logs.setdefault(day, {"commits": [], "issues": []})
            day_log["issues"].append({
                "repo": repo, "number": i["number"], "title": i["title"],
                "state": i["state"], "url": i["url"],
                "labels": [lbl["name"] for lbl in i.get("labels", [])],
                "time": i["updatedAt"].split("T")[1].replace("Z", "")
            })

    for day, content in daily_logs.items():
        out_file = OUTPUT_DIR / f"github_{day}.json"
        content["commits"].sort(key=lambda x: x["time"])
        content["issues"].sort(key=lambda x: x["time"])
        with open(out_file, "w") as f:
            json.dump(content, f, indent=2)
        print(f" -> Saved {out_file} [Commits: {len(content['commits'])}, Issues: {len(content['issues'])}]")

if __name__ == "__main__":
    main()
