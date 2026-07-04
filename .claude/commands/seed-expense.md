---
description: Seed realistic dummy expenses for a specific user
argument-hint: <user_id> <count> <months>
allowed-tools: Read, Bash(python3:*)
---
# Seed Dummy Expenses

Use the project's virtual environment Python interpreter (`venv\Scripts\python.exe`) or `python` when running on Windows. Do not use `python3`.

## Objective

Generate and insert realistic dummy expense records for an existing user.

## Instructions

### Step 1 — Read the Database Layer

Read `database/db.py` to understand:

- The `expenses` table schema.
- The `get_db()` helper function.
- The database connection pattern.
- The database filename (do not hardcode it).

User input:

```text
$ARGUMENTS
```

---

### Step 2 — Parse Arguments

Extract the following values from `$ARGUMENTS`:

- `user_id` (integer)
- `count` (integer) — number of expenses to generate
- `months` (integer) — number of past months across which expenses should be distributed

If any argument is missing or is not a valid integer, stop and return:

```text
Usage: /seed-expenses <user_id> <count> <months>

Example:
/seed-expenses 1 50 6
```

---

### Step 3 — Verify the User Exists

Before generating any expenses:

- Query the `users` table using the provided `user_id`.
- If no matching user exists, stop and return:

```text
No user found with id <user_id>.
```

---

### Step 4 — Generate and Insert Expenses

Write and execute a Python script that:

- Generates the requested number of realistic expenses.
- Randomly spreads expense dates across the previous `<months>` months.
- Uses the existing `get_db()` helper.
- Uses parameterized SQL queries only.
- Does **not** hardcode the database filename.
- Inserts all expenses within a single transaction.
- Rolls back the entire transaction if any insert fails.

Use the following categories and amount ranges:

| Category | Amount Range (₹) |
|----------|------------------:|
| Food | 50–800 |
| Transport | 20–500 |
| Bills | 200–3000 |
| Health | 100–2000 |
| Entertainment | 100–1500 |
| Shopping | 200–5000 |
| Other | 50–1000 |

Requirements:

- Use realistic Indian expense descriptions.
- Distribute categories naturally:
  - Food should be the most common.
  - Health and Entertainment should be the least common.

---

### Step 5 — Confirmation

After successful insertion, print:

- Total number of expenses inserted.
- The overall date range covered.
- A sample of five inserted expense records.

Example:

```text
Inserted 50 expenses.

Date Range:
2026-01-05 → 2026-06-28

Sample Records:

2026-06-28 | Food | ₹320 | Lunch at Haldiram's
2026-06-24 | Transport | ₹180 | Metro recharge
2026-06-20 | Bills | ₹1250 | Electricity bill
2026-06-18 | Shopping | ₹2450 | Amazon purchase
2026-06-12 | Food | ₹150 | Tea and snacks
```