class GitHubCompanion {

    constructor() {
        this.base = "http://localhost:8791";
    }

    async status() {
        const r = await fetch(`${this.base}/status`);
        return await r.json();
    }

    async getRecent(repo, opts = {}) {
        const params = new URLSearchParams();
        if (repo) params.set("repo", repo);
        if (opts.commits) params.set("commits", opts.commits);
        if (opts.issues) params.set("issues", opts.issues);

        const r = await fetch(`${this.base}/github?${params.toString()}`);
        const data = await r.json();

        if (!r.ok)
            throw new Error(data.error || `Companion returned ${r.status}`);

        return data;
    }
}
