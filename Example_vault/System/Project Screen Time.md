---
type: Project Screen Time
---
```dataviewjs
const sessions = dv.pages('"Sessions"')
  .where(s => s.type === "Session" && s.project);

function normalizeKey(p) {
  if (p == null) return null;
  // Handle Dataview Link objects
  if (typeof p === "object" && p.path) {
    const base = p.path.split("/").pop();
    return base.replace(/\.md$/i, "");
  }
  // Handle plain strings that might still be raw wikilinks, e.g. "[[Foo|Bar]]" or "[[Foo]]"
  let s = String(p).trim();
  s = s.replace(/^\[\[|\]\]$/g, "");   // strip [[ ]]
  s = s.split("|").pop();               // drop alias, keep display part
  s = s.split("/").pop();               // drop folder path, keep file name
  return s.replace(/\.md$/i, "");
}

const uniqueProjects = Array.from(
  new Set(
    sessions
      .map(s => normalizeKey(s.project))
      .filter(Boolean)
  )
).sort((a, b) => a.localeCompare(b));

const container = dv.container;
container.innerHTML = "";

if (!uniqueProjects.length) {
  container.createEl("div", { text: "No project sessions found yet." });
} else {

const wrapper = container.createDiv({ cls: "project-screen-time-wrapper" });

const style = `
  .project-screen-time-controls { display:flex; align-items:center; gap:12px; flex-wrap:wrap; margin-bottom: 12px; }
  .project-screen-time-select { padding:6px 10px; border-radius:8px; background: var(--background-secondary); border: 1px solid var(--background-modifier-border); color: var(--text-normal); }
  .project-screen-time-grid { display:grid; grid-template-columns: 1fr; gap: 10px; }
  .project-screen-time-table { width:100%; border-collapse: collapse; }
  .project-screen-time-table th { text-align:left; font-size: 12px; color: var(--text-muted); padding: 8px; border-bottom: 1px solid var(--background-modifier-border); }
  .project-screen-time-table td { padding: 8px; border-bottom: 1px solid var(--background-modifier-border); }
  .project-screen-time-app { font-weight: 600; }
  .project-screen-time-meta { color: var(--text-muted); font-size: 12px; }
  .project-screen-time-bar { height: 10px; background: var(--background-modifier-border); border-radius: 999px; overflow:hidden; }
  .project-screen-time-bar > div { height: 100%; background: var(--text-accent); width: 0%; }
`;

wrapper.insertAdjacentHTML("beforeend", `
  <style>${style}</style>
  <div class="project-screen-time-controls">
    <div class="project-screen-time-meta">Project Screen Time</div>
    <label>Project: </label>
    <select id="projectScreenTimeSelect" class="project-screen-time-select"></select>
  </div>
  <div id="projectScreenTimeBody" class="project-screen-time-grid"></div>
`);

const selectEl = wrapper.querySelector("#projectScreenTimeSelect");
const bodyEl = wrapper.querySelector("#projectScreenTimeBody");

for (const p of uniqueProjects) {
  const opt = document.createElement("option");
  opt.value = p;
  opt.textContent = p;
  selectEl.appendChild(opt);
}

function fmtSeconds(sec) {
  sec = Number(sec || 0);
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

async function render(project) {
  bodyEl.innerHTML = "";

  const projectSessions = sessions
    .where(s => normalizeKey(s.project) === project);

  const sessionList = projectSessions.array();

  const totals = { focused: 0, elapsed: 0 };
  const byApp = new Map();

  const activityLinks = [];
  for (const s of sessionList) {
    totals.focused += Number(s.focused_seconds ?? 0);
    totals.elapsed += Number(s.elapsed_seconds ?? 0);

    const acts = Array.isArray(s.activities) ? s.activities : [];
    for (const link of acts) {
      const name = normalizeKey(link);
      if (name) activityLinks.push(name);
    }
  }

  const activityPages = dv.pages('"Activities"')
    .where(a => activityLinks.includes(a.file.name))
    .array();

  for (const a of activityPages) {
    const app = a.app ?? "(unknown)";
    const focused = Number(a.focused_seconds ?? 0);
    const elapsed = Number(a.elapsed_seconds ?? 0);
    const prev = byApp.get(app) ?? { focused: 0, elapsed: 0 };
    byApp.set(app, { focused: prev.focused + focused, elapsed: prev.elapsed + elapsed });
  }

  const rows = Array.from(byApp.entries())
    .map(([app, v]) => ({ app, focused: v.focused, elapsed: v.elapsed }))
    .sort((x, y) => y.focused - x.focused);

  bodyEl.insertAdjacentHTML("beforeend", `
    <div class="project-screen-time-meta">
      Sessions: <b>${sessionList.length}</b> &nbsp;&nbsp;
      Total focused: <b>${fmtSeconds(totals.focused)}</b> &nbsp;&nbsp;
      Total elapsed: <b>${fmtSeconds(totals.elapsed)}</b>
    </div>
  `);

  const table = document.createElement("table");
  table.className = "project-screen-time-table";
  table.innerHTML = `
    <thead>
      <tr>
        <th style="width: 30%">App</th>
        <th style="width: 15%">Focused</th>
        <th style="width: 15%">Elapsed</th>
        <th style="width: 40%">Share (focused)</th>
      </tr>
    </thead>
    <tbody></tbody>
  `;

  const tbody = table.querySelector("tbody");

  for (const r of rows) {
    const share = totals.focused > 0 ? (r.focused / totals.focused) : 0;

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><span class="project-screen-time-app">${r.app}</span></td>
      <td>${fmtSeconds(r.focused)}</td>
      <td>${fmtSeconds(r.elapsed)}</td>
      <td>
        <div class="project-screen-time-bar" title="${Math.round(share * 100)}%">
          <div style="width:${Math.round(share * 100)}%"></div>
        </div>
        <div class="project-screen-time-meta">${Math.round(share * 100)}%</div>
      </td>
    `;
    tbody.appendChild(tr);
  }

  bodyEl.appendChild(table);
}

selectEl.addEventListener("change", (e) => render(e.target.value));
render(uniqueProjects[0]);
}
```