---
type: Usage Trend
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

const wrapper = container.createDiv({ cls: "usage-trend-wrapper" });

const style = `
  .usage-trend-controls { display:flex; align-items:center; gap:12px; flex-wrap:wrap; margin-bottom: 12px; }
  .usage-trend-select { padding:6px 10px; border-radius:8px; background: var(--background-secondary); border: 1px solid var(--background-modifier-border); color: var(--text-normal); }
  .usage-trend-meta { color: var(--text-muted); font-size: 12px; }
`;

wrapper.insertAdjacentHTML("beforeend", `
  <style>${style}</style>
  <div class="usage-trend-controls">
    <div class="usage-trend-meta">Usage trend</div>
    <label>Pick app: </label>
    <select id="usageTrendSelect" class="usage-trend-select"></select>
  </div>
  <div id="usageTrendMeta" class="usage-trend-meta"></div>
  <div id="usageTrendChart"></div>
`);

const selectEl = wrapper.querySelector("#usageTrendSelect");
const metaEl = wrapper.querySelector("#usageTrendMeta");
const chartEl = wrapper.querySelector("#usageTrendChart");

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

async function render(appName) {
  metaEl.innerHTML = "";
  chartEl.innerHTML = "";

  const appActs = activities
    .where(p => p.app === appName)
    .array();

  const byDate = new Map();
  for (const a of appActs) {
    const dateStr = dv.date(a.start).toFormat("yyyy-MM-dd");
    const focused = Number(a.focused_seconds ?? 0);
    const prev = byDate.get(dateStr) ?? 0;
    byDate.set(dateStr, prev + focused);
  }

  const rows = Array.from(byDate.entries())
    .map(([date, v]) => ({ date, focused: v }))
    .sort((x, y) => x.date.localeCompare(y.date));

  const total = rows.reduce((sum, r) => sum + r.focused, 0);

  metaEl.innerHTML = `
    Total focused: <b>${fmtSeconds(total)}</b> &nbsp;&nbsp; Days: <b>${rows.length}</b>
  `;

  if (!rows.length) {
    chartEl.createEl("div", { text: `No activity found for "${appName}".` });
    return;
  }

  const hoursValues = rows.map(r => Number((r.focused / 3600).toFixed(2)));
  const maxHours = Math.max(...hoursValues);
  const yMax = Math.max(1, Math.ceil(maxHours * 1.1));

  const xLabels = rows.map(r => `"${r.date.slice(5)}"`).join(", ");
  const yValues = hoursValues.join(", ");

  const mermaid = [
    "```mermaid",
    "xychart-beta",
    `    title "Focused hours per day - ${appName}"`,
    `    x-axis [${xLabels}]`,
    `    y-axis "Focused Hours" 0 --> ${yMax}`,
    `    line [${yValues}]`,
    "```"
  ].join("\n");

  await dv.paragraph(mermaid, chartEl);
}

selectEl.addEventListener("change", (e) => render(e.target.value));
render(selectEl.value);
}
```