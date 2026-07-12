class Meal {

    async create(data) {

        const folder = "Meals";

        const id = await customJS.Vault.nextId("meal", folder, "Meal");

        const filename =
            `${data.date} ${data.time.replace(":", "-")} ${data.meal_type}`;

        // --------------------------
        // Build food YAML
        // --------------------------

        const foodYaml = data.foods.map(food => `  - food: "[[${food.food}]]"
    amount: ${food.amount}`).join("\n");

        // --------------------------
        // Calculate nutrition
        // --------------------------

        const nutrition = await this.calculateNutrition(data.foods);

        // --------------------------
        // Human readable food table
        // --------------------------

        const foodTable = data.foods.map(food =>
            `| [[${food.food}]] | ${food.amount} |`
        ).join("\n");

        // --------------------------
        // Build markdown
        // --------------------------

        const content =
`---
type: Meal

id: ${id}

date: ${data.date}
time: ${data.time}

meal_type: ${data.meal_type}

location: ${data.location}

foods:
${foodYaml}

nutrition:
  calories: ${nutrition.calories}
  protein: ${nutrition.protein}
  carbs: ${nutrition.carbs}
  fat: ${nutrition.fat}
  fiber: ${nutrition.fiber}
  sugar: ${nutrition.sugar}
  sodium: ${nutrition.sodium}

notes: |
  ${data.notes || ""}

---

# ${filename}

## Nutrition

| Nutrient | Amount |
|----------|-------:|
| Calories | ${nutrition.calories} kcal |
| Protein | ${nutrition.protein} g |
| Carbs | ${nutrition.carbs} g |
| Fat | ${nutrition.fat} g |
| Fiber | ${nutrition.fiber} g |
| Sugar | ${nutrition.sugar} g |
| Sodium | ${nutrition.sodium} mg |

---

## Foods

| Food | Amount |
|------|-------:|
${foodTable}

---

## Notes

${data.notes || "*No notes.*"}

---

\`\`\`dataviewjs
const date = dv.current().file.name.split(" ")[0];
const path = dv.current().file.path;

const btn = dv.el("button", "Delete Meal", {cls: "meal-delete-btn"});

btn.addEventListener("click", async () => {
    if (!confirm("Delete this meal and remove it from the daily note?")) return;

    const meals = await customJS.DailyNote.getMeals(date);
    const meal = meals.find(m => m.path === path);
    if (!meal) return;

    await customJS.DailyNote.removeMeal(date, meal.id);

    const file = app.vault.getAbstractFileByPath(path);
    if (file) {
        await app.vault.delete(file);
    }
});
\`\`\`
`;

        const file = await customJS.Vault.createNote(
            folder,
            filename,
            content
        );

        await customJS.DailyNote.addMeal(data.date, file, id);
        await customJS.DailyNote.build(data.date);
        console.log(`Created meal note: ${data.date} ${data.time} ${data.meal_type}`);

        return file;
    }

    async calculateNutrition(foods) {

        const totals = {
            calories: 0,
            protein: 0,
            carbs: 0,
            fat: 0,
            fiber: 0,
            sugar: 0,
            sodium: 0
        };

        for (const item of foods) {

            const path = `Food/${item.food}.md`;

            const file = app.vault.getAbstractFileByPath(path);

            if (!file)
                continue;

            const text = await app.vault.read(file);

            const cache = app.metadataCache.getFileCache(file);

            if (!cache || !cache.frontmatter)
                continue;

            const fm = cache.frontmatter;

            const base = Number(fm.nutrition_base || 100);

            const scale = Number(item.amount) / base;

            totals.calories += Number(fm.calories || 0) * scale;
            totals.protein += Number(fm.protein || 0) * scale;
            totals.carbs += Number(fm.carbs || 0) * scale;
            totals.fat += Number(fm.fat || 0) * scale;
            totals.fiber += Number(fm.fiber || 0) * scale;
            totals.sugar += Number(fm.sugar || 0) * scale;
            totals.sodium += Number(fm.sodium || 0) * scale;

        }

        // Round to 1 decimal place

        for (const key in totals)
            totals[key] = Math.round(totals[key] * 10) / 10;

        return totals;
    }

}