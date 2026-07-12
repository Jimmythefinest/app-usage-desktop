class MealManager {

    async showDeleteModal(date) {

        const meals = await customJS.DailyNote.getMeals(date);

        if (!meals || meals.length === 0) {
            console.log("No meals found for date:", date);
            return;
        }

        const overlay = document.createElement("div");
        overlay.className = "mm-overlay";

        const modal = document.createElement("div");
        modal.className = "mm-modal";

        let itemsHtml = meals.map((m, i) => `
            <div class="mm-item" data-index="${i}" data-id="${m.id}" data-path="${m.path}">
                <span class="mm-item-name">${m.name}</span>
                <button class="mm-delete-btn">Delete</button>
            </div>
        `).join("");

        modal.innerHTML = `
            <div class="mm-header">
                <h3>Manage Meals — ${date}</h3>
                <button class="mm-close">&times;</button>
            </div>
            <div class="mm-body">
                <div class="mm-list">
                    ${itemsHtml}
                </div>
            </div>
        `;

        overlay.appendChild(modal);
        document.body.appendChild(overlay);

        modal.querySelector(".mm-close").addEventListener("click", () => {
            document.body.removeChild(overlay);
        });

        overlay.addEventListener("click", (e) => {
            if (e.target === overlay) {
                document.body.removeChild(overlay);
            }
        });

        modal.querySelectorAll(".mm-delete-btn").forEach(btn => {
            btn.addEventListener("click", async (e) => {
                const item = e.target.closest(".mm-item");
                const mealId = item.dataset.id;
                const mealPath = item.dataset.path;

                await customJS.DailyNote.removeMeal(date, mealId);

                const file = app.vault.getAbstractFileByPath(mealPath);
                if (file) {
                    await app.vault.delete(file);
                }

                item.remove();
            });
        });
    }
}

// MealManager class — loaded by CustomJS
