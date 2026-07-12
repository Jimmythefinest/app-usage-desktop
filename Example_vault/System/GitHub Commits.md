---
type: GitHub Commits
---
```dataviewjs
const commitPages = await dv.pages('"commits"');

// Only consider real commit notes (frontmatter `type: Commit`)
const commits = commitPages.where(p => p.type === 'Commit');

// Sort by increasing age (oldest first)
commits.sort((a, b) => {
  const da = new Date(`${a.date}T${a.time}`);
  const db = new Date(`${b.date}T${b.time}`);
  return da - db;
});

dv.table(
  ['Date', 'Time', 'Message', 'Author', 'Session', 'Commit'],
  commits.map(c => [c.date, c.time, c.message, c.author, c.session, `[${c.short_sha}](${c.url})`])
);
```