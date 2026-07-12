class Debt {

    async create(data) {

        const folder = "Finance/Debts";

        const id = await customJS.Vault.nextId("debt", folder, "Debt");

        const filename = data.name || data.party || "Debt";

        const principal = Number(data.principal) || 0;
        const balance = (data.balance === undefined || data.balance === "")
            ? principal
            : Number(data.balance);

        const content =
`---
type: Debt

id: ${id}

debt_type: ${data.debt_type || "liability"}
party: ${data.party || ""}
principal: ${principal}
balance: ${balance}
interest_rate: ${data.interest_rate || 0}
currency: ${data.currency || "INR"}
start_date: ${data.start_date || ""}
due_date: ${data.due_date || ""}
status: ${data.status || "active"}
account: "${data.account || ""}"

notes: |
  ${data.notes || ""}

---

# ${filename}

## Details

| Field | Value |
|-------|-------|
| Type | ${data.debt_type || "liability"} |
| Party | ${data.party || "-"} |
| Principal | ${principal} ${data.currency || "INR"} |
| Balance | ${balance} ${data.currency || "INR"} |
| Interest Rate | ${data.interest_rate || 0}% |
| Start | ${data.start_date || "-"} |
| Due | ${data.due_date || "-"} |
| Status | ${data.status || "active"} |
| Account | ${data.account ? "[[Finance/Accounts/" + data.account + "]]" : "-" } |

---

## Notes

${data.notes || "*No notes.*"}
`;

        const file = await customJS.Vault.createNote(
            folder,
            filename,
            content
        );

        return file;
    }
}

// Debt class — loaded by CustomJS
// v1
