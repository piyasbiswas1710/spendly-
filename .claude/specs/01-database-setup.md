# Database Implementation Specification

## 1. Overview

Replace the stub in `database/db.py` with a working SQLite implementation.

This step establishes the **data layer foundation** for the Spendly application.

All future features (authentication, profile, expense tracking) depend on this being correctly implemented.

---

## 2. Dependencies

- None — this is the first implementation step.

---

## 3. Routes

No new routes are introduced in this step.

The existing placeholder routes in `app.py` remain unchanged.

| Route | Status |
|-------|--------|
| Existing Routes | No changes required |

---

## 4. Database Schema

### A. `users`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `name` | TEXT | NOT NULL |
| `email` | TEXT | UNIQUE, NOT NULL |
| `password_hash` | TEXT | NOT NULL |
| `created_at` | TEXT | DEFAULT `datetime('now')` |

---

### B. `expenses`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `user_id` | INTEGER | NOT NULL, FOREIGN KEY → `users(id)` |
| `amount` | REAL | NOT NULL |
| `category` | TEXT | NOT NULL |
| `date` | TEXT | NOT NULL (`YYYY-MM-DD`) |
| `description` | TEXT | Nullable |
| `created_at` | TEXT | DEFAULT `datetime('now')` |

---

## 5. Functions to Implement (`database/db.py`)

### A. `get_db()`

Implement a helper function that:

- Opens a connection to `spendly.db` (or `expense_tracker.db`) in the project root.
- Sets:

  - `row_factory = sqlite3.Row`
  - `PRAGMA foreign_keys = ON`

- Returns the SQLite connection object.

---

### B. `init_db()`

Implement a function that:

- Creates the `users` table using `CREATE TABLE IF NOT EXISTS`.
- Creates the `expenses` table using `CREATE TABLE IF NOT EXISTS`.
- Is safe to execute multiple times.
- Ensures the database schema exists before the application starts.

---

### C. `seed_db()`

Implement a function that:

1. Checks whether the `users` table already contains data.
   - If data exists, return immediately without inserting anything.

2. Inserts one demo user:

| Field | Value |
|------|-------|
| Name | Demo User |
| Email | demo@spendly.com |
| Password | demo123 (hashed using Werkzeug) |

3. Inserts **8 sample expenses**:

- Linked to the demo user.
- Spread across the current month.
- Cover multiple categories.
- Include at least one expense for every category.

---

## 6. Changes to `app.py`

### Import

```python
from database.db import get_db, init_db, seed_db
```

### Startup Initialization

Call the following inside the application context:

```python
with app.app_context():
    init_db()
    seed_db()
```

This ensures the database is initialized before any routes are accessed.

---

## 7. Files to Modify

| File | Purpose |
|------|---------|
| `database/db.py` | Implement database helper functions |
| `app.py` | Import and initialize the database |

---

## 8. Files to Create

None.

---

## 9. Dependencies

No additional packages should be installed.

Use only:

- `sqlite3` (Python standard library)
- `werkzeug.security`

---

## 10. Fixed Expense Categories

Use **exactly** the following category values:

- Food
- Transport
- Bills
- Health
- Entertainment
- Shopping
- Other

---

## 11. Implementation Rules

- Do **not** use SQLAlchemy or any ORM.
- Use **parameterized SQL queries only**.
- Never use string formatting or f-strings in SQL statements.
- Enable foreign key enforcement by executing:

```sql
PRAGMA foreign_keys = ON;
```

on every database connection.

- Store `amount` as `REAL`.
- Hash passwords using:

```python
from werkzeug.security import generate_password_hash

password_hash = generate_password_hash("demo123")
```

- Prevent duplicate inserts in `seed_db()`.
- Store all dates in the **YYYY-MM-DD** format.

---

## 12. Expected Behavior

### `get_db()`

- Returns a valid SQLite connection.
- Supports dictionary-style row access (`sqlite3.Row`).
- Enforces foreign key constraints.

### `init_db()`

- Creates both database tables if they do not exist.
- Can be executed repeatedly without errors.

### `seed_db()`

- Inserts demo data only once.
- Does not create duplicate users or expenses.
- Seeds one demo user and eight sample expenses.

### Database Constraints

The database should enforce:

- Unique email addresses.
- Valid foreign key relationships.

---

## 13. Error Handling Expectations

The implementation should allow SQLite to raise appropriate errors for:

| Scenario | Expected Result |
|----------|-----------------|
| Duplicate email | UNIQUE constraint error |
| Invalid `user_id` | FOREIGN KEY constraint error |
| Invalid SQL query | Clear SQLite exception for debugging |

---

## 14. Definition of Done

- [ ] Database file is automatically created when the application starts.
- [ ] Both tables exist with the correct schema and constraints.
- [ ] Demo user is created with a hashed password.
- [ ] Eight sample expenses are inserted across the required categories.
- [ ] Running `seed_db()` multiple times does not duplicate data.
- [ ] Application starts successfully without errors.
- [ ] SQLite foreign key enforcement is enabled and working.
- [ ] All SQL statements use parameterized queries.