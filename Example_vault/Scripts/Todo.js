class Todo {

    async create(data) {

        const folder = "Todos";

        const id = await customJS.Vault.nextId("todo", folder, "Todo");

        const filename = data.title || "Todo";

        const content =
            `---
type: Todo

id: ${id}

date: ${data.date}

title: "${data.title}"

status: ${data.status || "todo"}

priority: ${data.priority || "medium"}

due: ${data.due || ""}

notes: |
  ${data.notes || ""}

---

- [ ] ${data.title}

\`\`\`dataviewjs
const checkbox = dv.el("input", "", {type: "checkbox"});
const titleEl = dv.el("div", dv.current().title || "Untitled");
const statusEl = dv.el("span", \`Status:  "todo"\`);

if (dv.current().status === "done") {
    checkbox.checked = true;
}

checkbox.addEventListener("change", async () => {
    const newStatus = checkbox.checked ? "done" : "todo";
    await dv.app.fileManager.processFrontMatter(dv.current().file, fm => {
        fm.status = newStatus;
    });
    statusEl.setText(\`Status: ${data.status}\`);
});
\`\`\`
`;

        const file = await customJS.Vault.createNote(
            folder,
            filename,
            content
        );

        await customJS.DailyNote.addTodo(data.date, file, id);
        await customJS.DailyNote.build(data.date);

        return file;
    }

    async getTodos(date) {

        return await customJS.DailyNote.getTodos(date);

    }
    
    // Update frontmatter helper
    async updateFrontmatter(path, updates) {

        const file = app.vault.getAbstractFileByPath(path);
        if (!file) return null;

        let text = await app.vault.read(file);

        const fmMatch = text.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?/);

        let fmText = fmMatch ? fmMatch[1] : "";
        let rest = fmMatch ? text.slice(fmMatch[0].length) : text;

        const lines = fmText.split(/\r?\n/).filter(Boolean);
        const parsed = {};
        let inNotes = false;
        let notesLines = [];

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            if (inNotes) {
                notesLines.push(line.replace(/^\s{2}/, ''));
                continue;
            }
            const notesMatch = line.match(/^notes:\s*\|/);
            if (notesMatch) {
                inNotes = true;
                continue;
            }
            const m = line.match(/^([A-Za-z0-9_]+):\s*(.*)$/);
            if (m) parsed[m[1]] = m[2];
        }

        if (notesLines.length) parsed.notes = notesLines.join('\n');

        // merge updates
        for (const k of Object.keys(updates)) {
            parsed[k] = updates[k];
        }

        // build frontmatter output (preserve common ordering)
        const order = ['type','id','date','title','status','priority','due','notes'];
        const out = [];
        for (const key of order) {
            if (!(key in parsed)) continue;
            if (key === 'notes') {
                out.push('notes: |');
                const noteVal = String(parsed.notes || '');
                if (noteVal.length) {
                    const noteLines = noteVal.split(/\r?\n/);
                    for (const nl of noteLines) out.push('  ' + nl);
                } else {
                    out.push('  ');
                }
            } else {
                out.push(`${key}: ${parsed[key]}`);
            }
        }

        const newFm = '---\n' + out.join('\n') + '\n---\n\n';

        const newText = newFm + rest;

        try {
            await app.vault.modify(file, newText);
            return file;
        } catch (e) {
            console.log('Failed to update frontmatter for', path, e);
            return null;
        }
    }

    async setStatus(path, status) {
        return await this.updateFrontmatter(path, { status });
    }

    async setPriority(path, priority) {
        return await this.updateFrontmatter(path, { priority });
    }

}

// Todo class — loaded by CustomJS
