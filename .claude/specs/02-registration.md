# Registration Specification

## 1. Overview

This feature turns the existing render-only `GET /register` route into a working account-creation flow. A visitor submits the registration form (full name, email, password); the server validates the input, hashes the password with Werkzeug, stores a new row in the `users` table, and redirects to `/login` so the user can sign in.

It belongs at this stage of the Spendly roadmap because Step 1 already created the `users` table and the database helpers. Registration is the first feature that *writes* a user, and it is a prerequisite for login (later step), the profile page (Step 4), and every expense feature (Steps 7–9), all of which need a real account to exist.

---

## 2. Dependencies

- **Step 1 — Database Setup**: requires `get_db()`, `init_db()`, and the `users` table (`id`, `name`, `email UNIQUE`, `password_hash`, `created_at`). All are already implemented in `database/db.py`.

No other steps are required. Registration does **not** depend on login, sessions, or a secret key — on success it redirects to `/login`, where authentication is handled in a later step.

---

## 3. Routes

| Route | Method | Description | Access | Status |
|---|---|---|---|---|
| `/register` | `GET` | Render the empty registration form | Public | ✅ Already implemented (render-only) |
| `/register` | `POST` | Validate input, create the user, redirect to `/login` | Public | 🔨 To implement (Step 2) |

The existing `register()` function is extended to `methods=["GET", "POST"]`. No new URL paths are added.

---

## 4. Database Changes

**No schema changes.** The `users` table from Step 1 is sufficient:

| Column | Type | Constraints |
|---|---|---|
| `id` | INTEGER | `PRIMARY KEY AUTOINCREMENT` |
| `name` | TEXT | `NOT NULL` |
| `email` | TEXT | `UNIQUE NOT NULL` |
| `password_hash` | TEXT | `NOT NULL` |
| `created_at` | TEXT | `DEFAULT (datetime('now'))` |

Two **new helper functions** are added to `database/db.py` (no SQL is allowed in route functions):

### A. `get_user_by_email(email)`
- Runs `SELECT * FROM users WHERE email = ?` with a parameterized query.
- Returns the matching `sqlite3.Row`, or `None` if no user has that email.
- Used to detect a duplicate email before inserting.

### B. `create_user(name, email, password)`
- Hashes `password` with `werkzeug.security.generate_password_hash`.
- Inserts a new row: `INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)` (parameterized). `id` and `created_at` are filled automatically.
- Commits and returns the new user's `id` (`cursor.lastrowid`).

Both open their connection via the existing `get_db()` (which already sets `row_factory` and `PRAGMA foreign_keys = ON`).

---

## 5. Templates

### Create

None. `templates/register.html` already exists with the correct fields (`name`, `email`, `password`), the `{% if error %}<div class="auth-error">{{ error }}</div>{% endif %}` block, and the `auth-*` wrapper structure.

### Modify

| Template | Change |
|---|---|
| `templates/register.html` | Change the hardcoded `action="/register"` to `action="{{ url_for('register') }}"` to satisfy the "no hardcoded URLs" rule. No other markup changes — the existing `name` / `email` / `password` inputs and `auth-error` block are reused as-is. |

The template already extends `base.html` and uses only `{% block title %}` / `{% block content %}`.

---

## 6. Files to Change

| File | Purpose |
|---|---|
| `app.py` | Extend `register()` to handle `GET` and `POST`; add `request`, `redirect`, `url_for`, and `flash` to the Flask import line; call the new `db.py` helpers; re-render `register.html` with an `error` on validation failure; redirect to `login` on success. |
| `database/db.py` | Add `get_user_by_email()` and `create_user()` helpers. |
| `templates/register.html` | Replace hardcoded form `action` with `url_for('register')`. |

---

## 7. Files to Create

None.

---

## 8. New Dependencies

No new dependencies. Werkzeug (`werkzeug==3.1.6`) is already in `requirements.txt` and already imported in `database/db.py`, so `generate_password_hash` is available.

---

## 9. Rules for Implementation

- **No SQLAlchemy or ORMs.** Use `sqlite3` via the existing `get_db()` only.
- **Parameterized SQL queries only** — `?` placeholders, never f-strings or string concatenation in SQL.
- **All database access lives in `database/db.py`.** The route calls `get_user_by_email()` / `create_user()` — no SQL or `get_db()` in `app.py`.
- **Hash passwords using `werkzeug`** (`generate_password_hash`). Never store or compare a plaintext password.
- **Use CSS variables; never hardcode hex color values.** The existing `auth-error` styling already uses `--danger` / `--danger-light` — no new CSS needed.
- **All templates must extend `base.html`.** `register.html` already does.
- **No hardcoded URLs** — the form action and the success redirect both use `url_for()`.
- **Never return raw strings from the route** — always `render_template()` (on error) or `redirect()` (on success).
- **Route stays single-responsibility** — read form, validate, delegate to `db.py`, redirect or re-render.

### Validation rules (server-side, in the route)

| Field | Rule | Error message on failure |
|---|---|---|
| `name` | Required, non-empty after `.strip()` | `"Please enter your name."` |
| `email` | Required, non-empty after `.strip()` | `"Please enter your email."` |
| `password` | Required, minimum 8 characters | `"Password must be at least 8 characters."` |
| `email` | Must not already exist (`get_user_by_email()` returns `None`) | `"An account with that email already exists."` |

On any failure, re-render `register.html` with the matching `error` string (no redirect). The seeded account `demo@spendly.com` will therefore trigger the duplicate-email error.

---

## 10. Definition of Done

- [ ] `GET /register` still renders the empty registration form (unchanged behavior).
- [ ] Submitting the form with a new name, email, and an 8+ character password creates a row in `users` and redirects to `/login`.
- [ ] The stored `password_hash` is a Werkzeug hash, **not** the plaintext password (verifiable by inspecting `expense_tracker.db`).
- [ ] Submitting with a blank name, blank email, or a password shorter than 8 characters re-renders `register.html` showing the corresponding message in the `auth-error` box, and creates no row.
- [ ] Submitting with an email that already exists (e.g. `demo@spendly.com`) re-renders `register.html` with the duplicate-email error and creates no row.
- [ ] No SQL appears in `app.py`; `get_user_by_email()` and `create_user()` exist in `database/db.py` and use parameterized queries.
- [ ] The registration form's `action` is generated with `url_for('register')` (no hardcoded URL).
- [ ] The app still starts on port 5001 with `python app.py` and `requirements.txt` is unchanged.
