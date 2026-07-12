```dataviewjs

const todos = dv.pages()
    .where(t =>
        t.type == "Todo" &&
        t.status != "done"
    )
    .sort(t => t.priority);
const activities = dv.pages('"Activities"')
    .where(a => !a.session)
    .sort(a => a.focused_seconds, "desc");

const container = dv.el("div", "");
container.style.border = "1px solid var(--background-modifier-border)";
container.style.padding = "1rem";
container.style.borderRadius = "8px";

const h = document.createElement("h2");
h.textContent = "Session Creator";
container.appendChild(h);

const form = document.createElement("div");
form.style.display = "grid";
form.style.gridTemplateColumns = "140px 1fr";
form.style.gap = "8px";
form.style.marginBottom = "1rem";
container.appendChild(form);

function addField(label, type="text"){
  const l=document.createElement("label");
  l.textContent=label;
  const i=type==="textarea"?document.createElement("textarea"):document.createElement("input");
  if(type!=="textarea") i.type=type;
  i.style.width="100%";
  form.appendChild(l); form.appendChild(i);
  return i;
}
const titleInput=addField("Title");
const projectLabel = document.createElement("label");
projectLabel.textContent = "Project";
form.appendChild(projectLabel);

const projectSelect = document.createElement("select");
projectSelect.style.width = "100%";

const blank = document.createElement("option");
blank.value = "";
blank.textContent = "-- Select Project --";
projectSelect.appendChild(blank);

const projects = dv.pages()
    .where(p => p.type == "project")
    .sort(p => p.file.name);

for (const project of projects) {

    const option = document.createElement("option");

    option.value = `[[${project.file.name}]]`;
    option.textContent = project.file.name;

    projectSelect.appendChild(option);

}

form.appendChild(projectSelect);
const taskInput=addField("Task");

const cl=document.createElement("label");cl.textContent="Category";form.appendChild(cl);
const category=document.createElement("select");
["Coding","Research","Learning","Writing","Meeting","Other"].forEach(v=>{
 const o=document.createElement("option");o.value=v;o.textContent=v;category.appendChild(o);
});
form.appendChild(category);

const goalInput=addField("Goal","textarea");
const todoContainer = document.createElement("div");
todoContainer.style.maxHeight = "200px";
todoContainer.style.overflowY = "auto";
todoContainer.style.border = "1px solid var(--background-modifier-border)";
todoContainer.style.padding = "8px";
todoContainer.style.borderRadius = "6px";
form.appendChild(todoContainer);

const selectedTodos = new Set();
for (const todo of todos) {

    const row = document.createElement("div");

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";

    checkbox.onchange = () => {
        const link = `[[${todo.file.name}]]`;

        if (checkbox.checked)
            selectedTodos.add(link);
        else
            selectedTodos.delete(link);
    };

    const label = document.createElement("label");
    label.style.marginLeft = "8px";
    label.textContent = todo.title ?? todo.file.name;

    row.appendChild(checkbox);
    row.appendChild(label);

    todoContainer.appendChild(row);
}
const search=document.createElement("input");
search.placeholder="Search...";
search.style.width="100%";
search.style.marginBottom="1rem";
container.appendChild(search);

const stats=document.createElement("div");
stats.style.marginBottom="1rem";
container.appendChild(stats);

const list=document.createElement("div");
container.appendChild(list);

const btn=document.createElement("button");
btn.textContent="Create Session";
btn.style.marginTop="1rem";
container.appendChild(btn);

const selected=new Set();

function fmt(sec){
 sec=Math.floor(Number(sec||0));
 const h=Math.floor(sec/3600);
 const m=Math.floor((sec%3600)/60);
 const s=sec%60;
 if(h) return `${h}h ${m}m`;
 if(m) return `${m}m ${s}s`;
 return `${s}s`;
}

function render(){
 list.innerHTML="";
 let total=0;
 let totalElapsed=0;

 for(const a of activities){
   const id=a.activity_id??a.file.name;
   const titles=Array.isArray(a.titles)?a.titles:[];
   const focused=Number(a.focused_seconds??0);
   const elapsed=Number(a.elapsed_seconds??0);
   if(focused<300) continue;

   const txt=((a.app??"")+" "+titles.join(" ")).toLowerCase();
   if(!txt.includes(search.value.toLowerCase())) continue;

   const card=document.createElement("div");
   card.style.border="1px solid var(--background-modifier-border)";
   card.style.borderRadius="8px";
   card.style.padding="10px";
   card.style.marginBottom="8px";
   card.style.cursor="pointer";

   if(selected.has(id)){
      card.style.background="var(--interactive-accent)";
      card.style.color="var(--text-on-accent)";
      total+=focused;
      totalElapsed+=elapsed;
   }

   const st=a.start?new Date(a.start).toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"}):"--";
   const en=a.end?new Date(a.end).toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"}):"--";

   card.innerHTML=`
   <div style="display:flex;justify-content:space-between">
      <b>${a.app}</b>
      <span>${fmt(focused)}</span>
   </div>
   <div style="opacity:.7">${st} → ${en}</div>
   <div>${titles.slice(0,3).map(t=>"• "+t).join("<br>")||"<i>No titles</i>"}</div>`;

   card.onclick=()=>{selected.has(id)?selected.delete(id):selected.add(id);render();};
   list.appendChild(card);
 }

 stats.innerHTML=`<b>Selected:</b> ${selected.size} &nbsp;&nbsp; <b>Focused:</b> ${fmt(total)} &nbsp;&nbsp; <b>Elapsed:</b> ${fmt(totalElapsed)}`;
}

search.oninput=render;

btn.onclick = async () => {
  const ids = [...selected];

  // 1. Check the actual title input value
  const sessionTitle = titleInput.value.trim();
  if (!sessionTitle) {
    new Notice("Enter a session title");
    return;
  }

  if (ids.length === 0) {
    new Notice("Select at least one activity");
    return;
  }

  // 2. Sum focused_seconds and elapsed_seconds, and find earliest start / latest end
  //    across the selected activities
  let focusedTotal = 0;
  let elapsedTotal = 0;
  let earliestStart = null;
  let latestEnd = null;

  for (const a of activities) {
    const id = a.activity_id ?? a.file.name;
    if (ids.includes(id)) {
      focusedTotal += Number(a.focused_seconds ?? 0);
      elapsedTotal += Number(a.elapsed_seconds ?? 0);

      if (a.start) {
        const s = new Date(a.start);
        if (!earliestStart || s < earliestStart) earliestStart = s;
      }
      if (a.end) {
        const e = new Date(a.end);
        if (!latestEnd || e > latestEnd) latestEnd = e;
      }
    }
  }

  // Format as local "YYYY-MM-DDTHH:mm:ss" (no timezone conversion, matches activity note style)
  function toLocalIso(d) {
    const pad = n => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  }

   // Session time bounds
   const sessionStart = earliestStart ? toLocalIso(earliestStart) : "";
   const sessionEnd = latestEnd ? toLocalIso(latestEnd) : "";

    // Find commits within this session's time range
    function getCommits(startStr, endStr) {
      const start = new Date(startStr);
      const end = new Date(endStr);
      return dv.pages('"commits"')
        .filter(c => {
		  console.log(c);
          if (!c.date || !c.time) return false;
          const dateStr = c.date ? dv.date(c.date).toFormat("yyyy-MM-dd") : "";
          const timeStr = String(c.time).replace("Z", "");
          const commitTime = new Date(`${dateStr}T${timeStr}`);
          return commitTime >= start && commitTime <= end;
        })
        .array();
    }

    const sessionCommits = getCommits(sessionStart, sessionEnd);

    const now = new Date();
    const date = now.toISOString().slice(0, 10);
    const safe = sessionTitle.replace(/[\\/:*?"<>|]/g, "-");

    const md = `---
type: Session
title: "${sessionTitle}"
date: ${date}
project: "${projectSelect.value}"
task: "${taskInput.value}"
category: ${category.value}
goal: |
  ${goalInput.value}
todos:
${[...selectedTodos].map(t => `  - "${t}"`).join("\n")}

activities:
${ids.map(i => `  - "[[${i}]]"`).join("\n")}

start: "${sessionStart}"
end: "${sessionEnd}"
focused_seconds: ${focusedTotal}
elapsed_seconds: ${elapsedTotal}
activity_count: ${ids.length}
commits:
${sessionCommits.map(c => `  - "[[${c.file.name}]]"`).join("\n")}
---

# ${sessionTitle}

## Outcome

## Next Session

## Commits

${sessionCommits.length > 0 ? sessionCommits.map(c => `- [${c.short_sha}](${c.url}) - ${c.message} (${c.author})`).join("\n") : "_No commits during this session._"}

`;

   // 3. Uses the safe title name to create the note via CustomJS
   const sessionLink = `[[${safe}]]`;
   await customJS.Vault.createNote("Sessions", safe, md);

   // 4. Link each commit back to this session
   for (const c of sessionCommits) {
     try {
       const file = app.vault.getFileByPath(`commits/${c.file.name}.md`);
       if (!file) continue;
       let text = await app.vault.read(file);
       const sessionEntry = `  - "${sessionLink}"\n`;
       if (text.includes('sessions: []')) {
         text = text.replace('sessions: []', `sessions:\n${sessionEntry}`);
       } else {
         const re = /^sessions:\n((?:  - .+\n)*)/m;
         if (re.test(text) && !text.split('sessions:')[1].includes(sessionLink)) {
           text = text.replace(re, (match, entries) => `sessions:\n${entries}${sessionEntry}`);
         }
       }
       await app.vault.modify(file, text);
     } catch (e) {
       console.error(`Could not update commit ${c.file.name}:`, e);
     }
   }

   new Notice(`Session created with ${sessionCommits.length} commit(s)`);
};

render();

```
