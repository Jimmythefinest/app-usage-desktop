class GitHubCommits {

    commitFolder() {
        return "GitHub/Commits";
    }

    projectFolder() {
        return "Projects";
    }

    parseRepo(input) {
        if (!input) return null;
        const text = input.trim();
        let m = text.match(/github\.com[:/]([^/\s]+)\/([^/\s#.]+)/);
        if (m) return `${m[1]}/${m[2].replace(/\.git$/, "")}`;
        m = text.match(/^([\w.-]+)\/([\w.-]+)$/);
        if (m) return `${m[1]}/${m[2].replace(/\.git$/, "")}`;
        return null;
    }

    projectName(repo) {
        return repo.replace("/", "-");
    }

    slug(message) {
        return (message || "")
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, "-")
            .replace(/^-+|-+$/g, "")
            .slice(0, 40);
    }

    async commitExists(sha) {
        const files = app.vault.getMarkdownFiles();
        for (const f of files) {
            if (!f.path.startsWith(this.commitFolder() + "/")) continue;
            const cache = app.metadataCache.getFileCache(f);
            const fm = cache && cache.frontmatter;
            if (fm && String(fm.sha) === String(sha)) return true;
        }
        return false;
    }

    async ensureProject(repo) {
        const name = this.projectName(repo);
        const path = `${this.projectFolder()}/${name}.md`;
        if (app.vault.getAbstractFileByPath(path)) return;
        const content =
`---
type: Project
repo: ${repo}
---

# ${name}

Repo: [${repo}](https://github.com/${repo})
`;
        await customJS.Vault.createNote(this.projectFolder(), name, content);
    }

    async ensureCommitNote(repo, commit) {
        const today = moment().format("YYYY-MM-DD");
        const slug = this.slug(commit.message);
        const name = `${commit.sha}-${slug}`;
        const projectName = this.projectName(repo);

        const content =
`---
type: Commit
sha: ${commit.sha}
repo: ${repo}
project: "${projectName}"
date: ${today}
author: ${commit.author || ""}
message: "${commit.message || ""}"
---

# ${commit.sha} ${commit.message || ""}

## Links
- Day: [[Daily Note/${today}]]
- Project: [[${this.projectFolder()}/${projectName}]]

## Details
- SHA: \`${commit.sha}\`
- Author: ${commit.author || ""}
- Date: ${commit.date || today}
- Repo: ${repo}

[View on GitHub](https://github.com/${repo}/commit/${commit.sha})
`;

        const file = await customJS.Vault.createNote(
            this.commitFolder(), name, content
        );

        await this.ensureProject(repo);
        await customJS.DailyNote.addNote(today, file);

        return file;
    }

    async sync(repoUrl, limit = 10) {
        const repo = this.parseRepo(repoUrl);
        if (!repo)
            throw new Error(`Could not parse GitHub repo from: ${repoUrl}`);

        const data = await customJS.GitHubCompanion.getRecent(
            repo, { commits: limit, issues: 0 }
        );

        const commits = data.commits || [];
        let created = 0, skipped = 0;
        const notes = [];

        for (const c of commits) {
            if (await this.commitExists(c.sha)) {
                skipped++;
                continue;
            }
            const file = await this.ensureCommitNote(repo, c);
            created++;
            notes.push(file);
        }

        return {
            repo,
            total: commits.length,
            created,
            skipped,
            notes
        };
    }
}
