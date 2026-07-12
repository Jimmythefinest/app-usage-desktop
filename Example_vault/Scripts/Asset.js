class Asset {

    async create(data) {

        const folder = "Finance/Assets";

        const filename = data.name || data.category || "Asset";

        const content =
`---
type: Asset

category: ${data.category || ""}
value: ${Number(data.value) || 0}
currency: ${data.currency || "INR"}
acquired_date: ${data.acquired_date || ""}
location: ${data.location || ""}
status: ${data.status || "active"}

notes: |
  ${data.notes || ""}

---

# ${filename}

## Details

| Field | Value |
|-------|-------|
| Category | ${data.category || "-"} |
| Value | ${Number(data.value) || 0} ${data.currency || "INR"} |
| Acquired | ${data.acquired_date || "-"} |
| Location | ${data.location || "-"} |
| Status | ${data.status || "active"} |

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

// Asset class — loaded by CustomJS
// v1
