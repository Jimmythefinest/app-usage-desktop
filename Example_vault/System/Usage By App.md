---
type: Usage By App
---
```dataviewjs
const activities = dv.pages('"Activities"')
  .where(p => p.type === "Activity" && p.start && p.focused_seconds != null);

const apps = Array.from(new Set(activities.map(p => p.app).filter(Boolean)))
  .sort((a, b) => String(a).localeCompare(String(b)));

const container = dv.container;
container.innerHTML = "";

if (!apps.length) {
  container.createEl("div", { text: "No Activity notes found in this vault yet." });
} else {

const wrapper = container.createDiv({ cls: "usage-by-app-wrapper" });

const style = `
  .usage-by-app-controls { display:flex; align-items:center; gap:12px; flex-wrap:wrap; margin-bottom: 12px; }
  .usage-by-app-select { padding:6px 10px; border-radius:8px; background: var(--background-secondary); border: 1px solid var(--background-modifier-border); color: var(--text-normal); }
  .usage-by-app-grid { display:grid; grid-template-columns: 1fr; gap: 10px; }
  .usage-by-app-table { width:100%; border-collapse: collapse; }
  .usage-by-app-table th { text-align:left; font-size: 12px; color: var(--text-muted); padding: 8px; border-bottom: 1px solid var(--background-modifier-border); }
  .usage-by-app-table td { padding: 8px; border-bottom: 1px solid var(--background-modifier-border); }
  .usage-by-app-meta { color: var(--text-muted); font-size: 12px; }
  .usage-by-app-bar { height: 10px; background: var(--background-modifier-border); border-radius: 999px; overflow:hidden; }
  .usage-by-app-bar > div { height: 100%; background: var(--text-accent); width: 0%; }
`;

wrapper.insertAdjacentHTML("beforeend", `
  <style>${style}</style>
  <div class="usage-by-app-controls">
    <div class="usage-by-app-meta">App usage by day</div>
    <label>Pick app: </label>
    <select id="usageByAppSelect" class="usage-by-app-select"></select>
  </div>
  <div id="usageByAppBody" class="usage-by-app-grid"></div>
`);

const selectEl = wrapper.querySelector("#usageByAppSelect");
const bodyEl = wrapper.querySelector("#usageByAppBody");

for (const app of apps) {
  const opt = document.createElement("option");
  opt.value = app;
  opt.textContent = app;
  if (app === "code") opt.selected = true;
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

function render(appName) {
  bodyEl.innerHTML = "";

  const appActs = activities
    .where(p => p.app === appName)
    .array();

  const byDate = new Map();
  for (const a of appActs) {
    const dateStr = dv.date(a.start).toFormat("yyyy-MM-dd");
    const focused = Number(a.focused_seconds ?? 0);
    const elapsed = Number(a.elapsed_seconds ?? 0);
    const prev = byDate.get(dateStr) ?? { focused: 0, elapsed: 0 };
    byDate.set(dateStr, { focused: prev.focused + focused, elapsed: prev.elapsed + elapsed });
  }

  const rows = Array.from(byDate.entries())
    .map(([date, v]) => ({ date, focused: v.focused, elapsed: v.elapsed }))
    .sort((x, y) => y.date.localeCompare(x.date));

  const totalFocused = rows.reduce((sum, r) => sum + r.focused, 0);
  const totalElapsed = rows.reduce((sum, r) => sum + r.elapsed, 0);

  bodyEl.insertAdjacentHTML("beforeend", `
    <div class="usage-by-app-meta">
      Total focused: <b>${fmtSeconds(totalFocused)}</b> &nbsp;&nbsp;
      Total elapsed: <b>${fmtSeconds(totalElapsed)}</b> &nbsp;&nbsp;
      Days: <b>${rows.length}</b>
    </div>
  `);

  const table = document.createElement("table");
  table.className = "usage-by-app-table";
  table.innerHTML = `
    <thead>
      <tr>
        <th style="width: 20%">Date</th>
        <th style="width: 15%">Focused</th>
        <th style="width: 15%">Elapsed</th>
        <th style="width: 50%">Share (focused)</th>
      </tr>
    </thead>
    <tbody></tbody>
  `;

  const tbody = table.querySelector("tbody");

  for (const r of rows) {
    const share = totalFocused > 0 ? (r.focused / totalFocused) : 0;

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${r.date}</td>
      <td>${fmtSeconds(r.focused)}</td>
      <td>${fmtSeconds(r.elapsed)}</td>
      <td>
        <div class="usage-by-app-bar" title="${Math.round(share * 100)}%">
          <div style="width:${Math.round(share * 100)}%"></div>
        </div>
        <div class="usage-by-app-meta">${Math.round(share * 100)}%</div>
      </td>
    `;
    tbody.appendChild(tr);
  }

  bodyEl.appendChild(table);
}

selectEl.addEventListener("change", (e) => render(e.target.value));
render(selectEl.value);
}
```