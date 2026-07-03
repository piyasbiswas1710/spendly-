# Plan: Step 1 — Database Setup

> On execution, also save a copy of this plan to `P:\expense-tracker\.claude\plans\01-database-setup.md` (per the user's request).

## Context

Spendly's data layer is currently a stub. `database/db.py` contains only comments, and `app.py` never touches the database. Every future feature (auth, profile, expense CRUD) depends on a working SQLite foundation. This step implements the three DB helpers (`get_db`, `init_db`, `seed_db`) exactly as defined in `.claude/specs/01-database-setup.md`, and wires database initialization into app startup. Outcome: on `python app.py`, the DB file is auto-created, schema exists, and a demo user with sample expenses is seeded once (idempotently).

## Scope & Constraints

- **Modify only** `database/db.py` and `app.py`. Create no new files. Install no packages.
- Use only `sqlite3` (stdlib) and `werkzeug.security.generate_password_hash`.
- All SQL parameterized (`?` placeholders) — no f-strings/string formatting in SQL.
- `PRAGMA foreign_keys = ON` on **every** connection; `row_factory = sqlite3.Row`.
- DB file: **`expense_tracker.db`** in the project root (already in `.gitignore`; keeps DB untracked).
- Port stays **5001**. Categories are exactly: Food, Transport, Bills, Health, Entertainment, Shopping, Other.

## Implementation

### 1. `database/db.py` (replace stub)

Module-level:
- `import sqlite3`, `import os`, `from datetime import date, timedelta`, `from werkzeug.security import generate_password_hash`.
- `DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "expense_tracker.db")` — resolves to project root regardless of CWD.

**`get_db()`**
- `conn = sqlite3.connect(DB_PATH)`
- `conn.row_factory = sqlite3.Row`
- `conn.execute("PRAGMA foreign_keys = ON")`
- `return conn`

**`init_db()`**
- Open `get_db()`, execute two `CREATE TABLE IF NOT EXISTS` statements:
  - `users(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TEXT DEFAULT (datetime('now')))`
  - `expenses(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, amount REAL NOT NULL, category TEXT NOT NULL, date TEXT NOT NULL, description TEXT, created_at TEXT DEFAULT (datetime('now')), FOREIGN KEY (user_id) REFERENCES users(id))`
- `conn.commit()`, `conn.close()`. (Note: `datetime('now')` default wrapped in parentheses — required by SQLite for function defaults.)

**`seed_db()`**
- Open `get_db()`. Guard: `SELECT COUNT(*) FROM users`; if `> 0`, `close()` and `return` (idempotent).
- Insert demo user via parameterized query: `("Demo User", "demo@spendly.com", generate_password_hash("demo123"))`. Capture `cursor.lastrowid` as `user_id`.
- Build **8 sample expenses** as a list of tuples `(user_id, amount, category, date_str, description)`:
  - Covers all 7 categories at least once (one category gets a 2nd row to reach 8).
  - Dates spread across the **current month**, computed from `date.today().replace(day=...)` → formatted `%Y-%m-%d` (clamped to valid days so it works early in the month).
  - Realistic ₹ amounts (REAL), e.g. Food 250.0, Transport 80.0, Bills 1200.0, Health 500.0, Entertainment 350.0, Shopping 999.0, Other 150.0, + one extra Food 420.0.
- `executemany("INSERT INTO expenses (...) VALUES (?,?,?,?,?)", rows)`, `commit()`, `close()`.

### 2. `app.py`

- Add import after the Flask import: `from database.db import get_db, init_db, seed_db`. (`get_db` imported now for consistency with the spec even though used in later steps.)
- Add a startup block (after routes, before `if __name__ == "__main__":`) so init runs under Flask CLI too:
  ```python
  with app.app_context():
      init_db()
      seed_db()
  ```

## Verification

1. Delete any stale DB: `rm -f expense_tracker.db`.
2. Start the app: `python app.py` — must boot on port 5001 with no errors and create `expense_tracker.db`.
3. Inspect schema & data (read-only), e.g. via `python -c` or `sqlite3`:
   - `SELECT name, email FROM users;` → exactly 1 row, `demo@spendly.com`, `password_hash` is a Werkzeug hash (starts with `pbkdf2:` or `scrypt:`), not plaintext.
   - `SELECT COUNT(*) FROM expenses;` → 8; `SELECT DISTINCT category FROM expenses;` → all 7 categories present.
   - `PRAGMA foreign_keys;` on a `get_db()` connection → 1.
4. Idempotency: restart the app (or call `seed_db()` again) → still 1 user and 8 expenses (no duplicates).
5. FK enforcement: attempt `INSERT INTO expenses(user_id, amount, category, date) VALUES (9999, 1, 'Food', '2026-07-01')` on a `get_db()` connection → raises `sqlite3.IntegrityError` (FOREIGN KEY constraint failed).
6. UNIQUE enforcement: inserting a 2nd user with `demo@spendly.com` → `sqlite3.IntegrityError` (UNIQUE constraint).
7. Confirm `expense_tracker.db` is untracked: `git status` shows it ignored.
