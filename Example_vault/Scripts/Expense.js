class Expense {

    async create(data) {

        const folder = "Finance/Expenses";

        const id = await customJS.Vault.nextId("expense", folder, "Expense");

        const filename =
            `${data.date} ${data.merchant} ${data.category}`;

        // --------------------------
        // Build markdown
        // --------------------------

        const content =
`---
type: Expense

id: ${id}

date: ${data.date}

category: "${data.category}"

merchant: "${data.merchant}"

account: "${data.account}"

amount: ${data.amount}
currency: ${data.currency || "INR"}

payment_method: ${data.payment_method || ""}

notes: |
  ${data.notes || ""}

---

# ${filename}

## Details

| Field | Value |
|-------|-------|
| Date | ${data.date} |
| Category | [[Finance/Categories/${data.category}]] |
| Merchant | [[Finance/Merchants/${data.merchant}]] |
| Account | [[Finance/Accounts/${data.account}]] |
| Amount | ${data.amount} ${data.currency || "INR"} |
| Payment | ${data.payment_method || "-"} |

---

## Notes

${data.notes || "*No notes.*"}
`;

        const file = await customJS.Vault.createNote(
            folder,
            filename,
            content
        );

        await customJS.DailyNote.addExpense(data.date, file);
        await customJS.DailyNote.build(data.date);

        return file;
    }
}

// Expense class — loaded by CustomJS
