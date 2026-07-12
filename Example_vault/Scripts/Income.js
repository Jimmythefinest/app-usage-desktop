class Income {

    async create(data) {

        const folder = "Finance/Income";

        const id = await customJS.Vault.nextId("income", folder, "Income");

        const filename =
            `${data.date} ${data.source} ${data.category}`;

        // --------------------------
        // Build markdown
        // --------------------------

        const content =
`---
type: Income

id: ${id}

date: ${data.date}

category: "${data.category}"

source: ${data.source}

account: "${data.account}"

amount: ${data.amount}
currency: ${data.currency || "INR"}

notes: |
  ${data.notes || ""}

---

# ${filename}

## Details

| Field | Value |
|-------|-------|
| Date | ${data.date} |
| Category | [[Finance/Income Categories/${data.category}]] |
| Source | ${data.source} |
| Account | [[Finance/Accounts/${data.account}]] |
| Amount | ${data.amount} ${data.currency || "INR"} |

---

## Notes

${data.notes || "*No notes.*"}
`;

        const file = await customJS.Vault.createNote(
            folder,
            filename,
            content
        );

        await customJS.DailyNote.addIncome(data.date, file);
        await customJS.DailyNote.build(data.date);

        return file;
    }
}

// Income class — loaded by CustomJS
