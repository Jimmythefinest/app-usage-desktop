```dataview
TABLE WITHOUT ID
	title AS "Title",
    date AS "Date",
    category AS "Category",
    elapsed_seconds/60 as "Length/min"
FROM "Sessions"
WHERE type="Session"
SORT date DESC
```