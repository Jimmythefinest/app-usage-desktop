---
type: Usage By Day
---
```dataviewjs
const ACTIVITIES_PATH = "Activities"; // folder containing Activity notes
const typeName = "Activity";

const activities = dv.pages(`"${ACTIVITIES_PATH}"`)
  .where(p => p.type === typeName && p.start && p.focused_seconds != null);

// Extract unique dates (YYYY-MM-DD) from each Activity note's `start`, most recent first
const dates = Array.from(new Set(
  activities
    .map(p => dv.date(p.start).toFormat("yyyy-MM-dd"))
    .array()
)).sort().reverse();

const container = dv.container;
container.innerHTML = "";

const todayStr = dv.date("today").toFormat("yyyy-MM-dd");
const defaultDate = dates.includes(todayStr) ? todayStr : (dates[0] ?? "");

if (!defaultDate) {
  container.createEl("div", { text: "No Activity notes found in this vault yet." });
} else {


// Dropdown + body
const wrapper = container.createDiv({ cls: "usage-by-day-wrapper" });

const style = `
  .usage-by-day-controls { display:flex; align-items:center; gap:12px; flex-wrap:wrap; margin-bottom: 12px; }
  .usage-by-day-select { padding:6px 10px; border-radius:8px; background: var(--background-secondary); border: 1px solid var(--background-modifier-border); color: var(--text-normal); }
  .usage-by-day-grid { display:grid; grid-template-columns: 1fr; gap: 10px; }
  .usage-by-day-table { width:100%; border-collapse: collapse; }
  .usage-by-day-table th { text-align:left; font-size: 12px; color: var(--text-muted); padding: 8px; border-bottom: 1px solid var(--background-modifier-border); }
  .usage-by-day-table td { padding: 8px; border-bottom: 1px solid var(--background-modifier-border); }
  .usage-by-day-app { font-weight: 600; }
  .usage-by-day-meta { color: var(--text-muted); font-size: 12px; }
  .usage-by-day-bar { height: 10px; background: var(--background-modifier-border); border-radius: 999px; overflow:hidden; }
  .usage-by-day-bar > div { height: 100%; background: var(--text-accent); width: 0%; }
`;

wrapper.insertAdjacentHTML("beforeend", `
  <style>${style}</style>
  <div class="usage-by-day-controls">
    <div class="usage-by-day-meta">App usage by day</div>
    <label>Pick date: </label>
    <select id="usageByDaySelect" class="usage-by-day-select"></select>
  </div>
  <div id="usageByDayBody" class="usage-by-day-grid"></div>
`);

const selectEl = wrapper.querySelector("#usageByDaySelect");
const bodyEl = wrapper.querySelector("#usageByDayBody");

for (const d of dates) {
  const opt = document.createElement("option");
  opt.value = d;
  opt.textContent = d;
  if (d === defaultDate) opt.selected = true;
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

function render(dateStr) {
  bodyEl.innerHTML = "";

  const dayActs = activities
    .where(p => dv.date(p.start).toFormat("yyyy-MM-dd") === dateStr);

  // Aggregate focused and elapsed time by app
  const byApp = new Map();
  for (const a of dayActs.values) {
    const app = a.app ?? "(unknown)";
    const focused = Number(a.focused_seconds ?? 0);
    const elapsed = Number(a.elapsed_seconds ?? 0);
    const prev = byApp.get(app) ?? { focused: 0, elapsed: 0 };
    byApp.set(app, { focused: prev.focused + focused, elapsed: prev.elapsed + elapsed });
  }

  const rows = Array.from(byApp.entries())
    .map(([app, v]) => ({ app, focused: v.focused, elapsed: v.elapsed }))
    .sort((x, y) => y.focused - x.focused);

  const totalFocused = rows.reduce((sum, r) => sum + r.focused, 0);
  const totalElapsed = rows.reduce((sum, r) => sum + r.elapsed, 0);

  // Total header
  bodyEl.insertAdjacentHTML("beforeend", `
    <div class="usage-by-day-meta">Total focused time: <b>${fmtSeconds(totalFocused)}</b> &nbsp;&nbsp; Total elapsed time: <b>${fmtSeconds(totalElapsed)}</b></div>
  `);

  // Table
  const table = document.createElement("table");
  table.className = "usage-by-day-table";
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
    const share = totalFocused > 0 ? (r.focused / totalFocused) : 0;

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><span class="usage-by-day-app">${r.app}</span></td>
      <td>${fmtSeconds(r.focused)}</td>
      <td>${fmtSeconds(r.elapsed)}</td>
      <td>
        <div class="usage-by-day-bar" title="${Math.round(share * 100)}%">
          <div style="width:${Math.round(share * 100)}%"></div>
        </div>
        <div class="usage-by-day-meta">${Math.round(share * 100)}%</div>
      </td>
    `;
    tbody.appendChild(tr);
  }

  bodyEl.appendChild(table);
}

selectEl.addEventListener("change", (e) => render(e.target.value));
render(defaultDate);
}
```