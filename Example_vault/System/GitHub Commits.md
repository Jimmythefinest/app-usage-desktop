---
type: GitHub Commits
---
```dataviewjs
const commits = await dv.pages('"commits"');
commits.sort((a, b) => {
  const da = new Date(`${a.date}T${a.time}`);
  const db = new Date(`${b.date}T${b.time}`);
  return db - da;
});
dv.table(
  ['Date', 'Time', 'Message', 'Author', 'Session', 'Commit'],
  commits.map(c => [c.date, c.time, c.message, c.author, c.session, `[${c.short_sha}](${c.url})`])
);
```