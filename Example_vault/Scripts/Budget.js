class Budget {

    async create(data) {

        const folder = "Finance/Budgets";

        const filename = data.name ||
            `${data.start_date} to ${data.end_date}`;

        // --------------------------
        // Build category YAML
        // --------------------------

        const catYaml = data.categories.map(c =>
            `  - category: ${c.category}\n    amount: ${c.amount}`
        ).join("\n");

        // --------------------------
        // Build allocations table
        // --------------------------

        const catTable = data.categories.map(c =>
            `| ${c.category} | ${c.amount} |`
        ).join("\n");

        // --------------------------
        // Build markdown
        // --------------------------

        const content =
`---
type: Budget

start_date: ${data.start_date}
end_date: ${data.end_date}

currency: ${data.currency || "INR"}

categories:
${catYaml}

---

# ${filename}

## Allocations

| Category | Budget (${data.currency || "INR"}) |
|----------|-------:|
${catTable}

---

## Progress

See [[Finance/Budget Dashboard]] for budget vs actual progress.

---

## Notes

`;

        const file = await customJS.Vault.createNote(
            folder,
            filename,
            content
        );

        return file;
    }
}

// Budget class — loaded by CustomJS
