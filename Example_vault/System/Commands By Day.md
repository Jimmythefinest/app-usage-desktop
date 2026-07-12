---
type: Commands By Day
---
```dataviewjs
const activities = dv.pages('"Activities"')
  .where(p => p.type === "Activity" && Array.isArray(p.commands) && p.commands.length);

const dates = Array.from(new Set(
  activities
    .flatMap(p => (Array.isArray(p.commands) ? p.commands : []))
    .map(c => {
      const ts = String(c.timestamp || "").split("T")[0];
      return ts;
    })
)).sort().reverse();

const container = dv.container;
container.innerHTML = "";

if (!dates.length) {
  container.createEl("div", { text: "No commands found yet." });
} else {

const wrapper = container.createDiv({ cls: "commands-by-day-wrapper" });

const style = `
  .commands-by-day-controls { display:flex; align-items:center; gap:12px; flex-wrap:wrap; margin-bottom: 12px; }
  .commands-by-day-select { padding:6px 10px; border-radius:8px; background: var(--background-secondary); border: 1px solid var(--background-modifier-border); color: var(--text-normal); }
  .commands-by-day-grid { display:grid; grid-template-columns: 1fr; gap: 10px; }
  .commands-by-day-table { width:100%; border-collapse: collapse; }
  .commands-by-day-table th { text-align:left; font-size: 12px; color: var(--text-muted); padding: 8px; border-bottom: 1px solid var(--background-modifier-border); }
  .commands-by-day-table td { padding: 8px; border-bottom: 1px solid var(--background-modifier-border); }
  .commands-by-day-time { font-family: monospace; color: var(--text-muted); }
  .commands-by-day-cmd { font-family: monospace; }
  .commands-by-day-cwd { color: var(--text-muted); font-size: 12px; }
  .commands-by-day-group { margin-bottom: 12px; }
  .commands-by-day-group-title { font-weight: 600; margin-bottom: 6px; }
`;

wrapper.insertAdjacentHTML("beforeend", `
  <style>${style}</style>
  <div class="commands-by-day-controls">
    <div class="commands-by-day-cmd">Commands by day</div>
    <label>Pick date: </label>
    <select id="commandsByDaySelect" class="commands-by-day-select"></select>
  </div>
  <div id="commandsByDayBody" class="commands-by-day-grid"></div>
`);

const selectEl = wrapper.querySelector("#commandsByDaySelect");
const bodyEl = wrapper.querySelector("#commandsByDayBody");

for (const d of dates) {
  const opt = document.createElement("option");
  opt.value = d;
  opt.textContent = d;
  selectEl.appendChild(opt);
}

function fmtTimestamp(ts) {
  const t = String(ts || "").split("T")[1];
  if (!t) return "";
  return t.split("+")[0].split("Z")[0];
}

function render(dateStr) {
  bodyEl.innerHTML = "";

  const dayActivities = activities
    .where(p => Array.isArray(p.commands))
    .array()
    .filter(a => a.commands.some(c => String(c.timestamp || "").startsWith(dateStr)));

  const rows = [];
  for (const a of dayActivities) {
    for (const c of a.commands || []) {
      const ts = String(c.timestamp || "");
      if (!ts.startsWith(dateStr)) continue;
      rows.push({
        time: fmtTimestamp(ts),
        command: String(c.command || ""),
        cwd: String(c.cwd || ""),
        app: a.app || "(unknown)",
      });
    }
  }

  rows.sort((x, y) => x.time.localeCompare(y.time));

  const byApp = new Map();
  for (const r of rows) {
    const app = r.app;
    if (!byApp.has(app)) byApp.set(app, []);
    byApp.get(app).push(r);
  }

  const total = rows.length;

  bodyEl.insertAdjacentHTML("beforeend", `
    <div class="commands-by-day-cmd">Total commands: <b>${total}</b> &nbsp;&nbsp; Apps: <b>${byApp.size}</b></div>
  `);

  for (const [app, appRows] of byApp) {
    const group = document.createElement("div");
    group.className = "commands-by-day-group";

    const title = document.createElement("div");
    title.className = "commands-by-day-group-title";
    title.textContent = app;
    group.appendChild(title);

    const table = document.createElement("table");
    table.className = "commands-by-day-table";
    table.innerHTML = `
      <thead>
        <tr>
          <th style="width: 15%">Time</th>
          <th style="width: 60%">Command</th>
          <th style="width: 25%">CWD</th>
        </tr>
      </thead>
      <tbody></tbody>
    `;

    const tbody = table.querySelector("tbody");

    for (const r of appRows) {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><span class="commands-by-day-time">${r.time}</span></td>
        <td><span class="commands-by-day-cmd">${r.command}</span></td>
        <td><span class="commands-by-day-cwd">${r.cwd}</span></td>
      `;
      tbody.appendChild(tr);
    }

    group.appendChild(table);
    bodyEl.appendChild(group);
  }
}

selectEl.addEventListener("change", (e) => render(e.target.value));
render(dates[0]);
}
```