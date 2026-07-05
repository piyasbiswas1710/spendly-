# Spec: Add Expense

## Overview

This feature replaces the `/expenses/add` stub with a real "add expense" flow: a logged-in user navigates to a form, enters an amount, category, date, and description, the server validates the input and inserts a new row into the `expenses` table scoped to the logged-in user, and the user is redirected back to `/profile` where the new transaction appears in the recent transactions list (subject to the active date filter).

It belongs at this stage of the Spendly roadmap because Steps 1–6 have already established the `expenses` schema, the session-scoped profile page, and the date-filter machinery. Steps 8 (edit) and 9 (delete) will mirror this step's form-and-validation pattern, so this is the canonical place to define how a write to the `expenses` table is structured, validated, and rendered.

---

## Depends on

- **Step 1 — Database Setup:** `get_db()`, the `expenses` table (`id`, `user_id`, `amount REAL`, `category TEXT`, `date TEXT`, `description TEXT`, `created_at`), and the `CATEGORIES` constant in `database/db.py`.
- **Step 3 — Login and Logout:** `session["user_id"]` is the only way to know which user the new expense belongs to.
- **Step 5 — Profile Page Backend Routes:** `get_recent_transactions()`, `get_profile_stats()`, and `get_category_breakdown()` must keep working with the new row so the profile page reflects the add immediately.
- **Step 6 — Date Filter:** the redirect target `/profile` honors the active `range` filter, so a new expense for a date outside the active range will not appear until the user changes the filter — this is expected behavior, not a bug.

---

## Routes

```text
GET  /expenses/add     — Render the empty "add expense" form            — Logged-in
POST /expenses/add     — Validate input, insert a row, redirect to /profile — Logged-in
```

The existing `add_expense()` placeholder in `app.py` (which currently returns the string `"Add expense — coming in Step 7"`) is extended to `methods=["GET", "POST"]`. No new URL paths are added.

Authentication is required for both verbs — unauthenticated users are redirected to `/login` (same guard as `/profile`).

---

## Database Changes

**No schema changes.** The existing `expenses` table from Step 1 is sufficient.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | INTEGER | `PRIMARY KEY AUTOINCREMENT` — assigned by SQLite |
| `user_id` | INTEGER | `NOT NULL`, set from `session["user_id"]` |
| `amount` | REAL | `NOT NULL`, validated as a positive number |
| `category` | TEXT | `NOT NULL`, validated against `CATEGORIES` |
| `date` | TEXT | `NOT NULL`, stored as `YYYY-MM-DD` |
| `description` | TEXT | Optional, may be empty string or `NULL` |
| `created_at` | TEXT | Filled by `DEFAULT (datetime('now'))` |

**New helper function to add to `database/db.py`** (no SQL in route functions):

### `create_expense(user_id, amount, category, date, description)`

- Runs `INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)` with a fully parameterized query.
- Calls `conn.commit()` and returns the new expense's `id` (`cursor.lastrowid`).
- Reuses the existing `get_db()` (which already sets `row_factory` and `PRAGMA foreign_keys = ON`).
- Performs no validation — that responsibility lives in the route, so the helper can be reused by Step 8 (edit) without re-implementing validation rules.

---

## Templates

### Create

- `templates/add_expense.html` — extends `base.html`; contains:
  1. A page header (e.g. "Add an expense") and a short helper line.
  2. An `auth-card`-style form card with the `auth-error` block at the top, mirroring the visual language of `register.html` / `login.html` for consistency.
  3. Form fields:
     - **Amount** (`<input type="number" name="amount" step="0.01" min="0.01" required>`) with a `₹` prefix label.
     - **Category** (`<select name="category" required>`) populated from `CATEGORIES` in `app.py`, with an empty default option prompting the user to pick one.
     - **Date** (`<input type="date" name="date" required>`) defaulting to today (`YYYY-MM-DD`).
     - **Description** (`<input type="text" name="description" maxlength="200">`) optional.
  4. A primary submit button labeled "Add expense" and a secondary "Cancel" link that goes back to `/profile` (via `url_for('profile')`).
  5. The form posts to `url_for('add_expense')` — never a hardcoded URL.

### Modify

```text
No template changes.
```

`base.html`, `profile.html`, `login.html`, and `register.html` are unchanged. The new template is fully self-contained.

---

## Files to Change

| File             | Purpose |
| --- | --- |
| `app.py`         | Replace the `add_expense()` stub with a real `GET`/`POST` view: guard the route, render the form, validate input, call the new `create_expense()` helper, and redirect to `/profile` on success. Import `CATEGORIES` and `create_expense` from `database/db`. |
| `database/db.py` | Add `create_expense(user_id, amount, category, date, description)`. |

---

## Files to Create

| File                         | Purpose |
| --- | --- |
| `templates/add_expense.html` | The "add expense" form described above. |

---

## New Dependencies

```text
No new dependencies.
```

`sqlite3` (stdlib) and `werkzeug` are already available. No new pip packages are required.

---

## Rules for Implementation

- **No SQLAlchemy or ORMs.** Use `sqlite3` via the existing `get_db()` only.
- **Parameterized SQL queries only** — `?` placeholders, never f-strings or string concatenation in SQL. The single `INSERT` in `create_expense` must use five `?` placeholders.
- **All database access lives in `database/db.py`.** The route calls `create_expense()` — no SQL or `get_db()` in `app.py`.
- **Hash passwords using `werkzeug`** — unchanged in this step (no auth logic touched).
- **Use CSS variables; never hardcode hex color values.** The new template reuses the existing `auth-*` / `form-*` / `btn-submit` classes; if any new CSS is needed, it must reference existing variables in `:root` (or add a new variable there).
- **All templates must extend `base.html`.** `add_expense.html` must.
- **No hardcoded URLs** — the form `action` and every link in the template use `url_for()`.
- **Never return raw strings from the route** — always `render_template()` (on validation failure) or `redirect()` (on success).
- **Route stays single-responsibility** — read form, validate, delegate to `db.py`, redirect or re-render.
- **Session check first** — if `session.get("user_id")` is missing, redirect to `/login` before doing anything else (including rendering the form, so a logged-out user never sees it).
- **Category whitelist** — only accept categories that are in `CATEGORIES`; reject anything else. Do not trust the form value.
- **Currency** — amounts are stored in rupees (no subunit conversion); the form uses `step="0.01"` so users can enter paise but the stored value is still a single `REAL` column.
- **Date format** — the form uses `<input type="date">` which posts `YYYY-MM-DD`, exactly the format `expenses.date` expects. No parsing or reformatting needed.
- **Description** — trim whitespace; allow empty (store as empty string, not `NULL`, so reads are uniform).
- **Server-side validation only** — no client-side JS validation. The form is functional with JavaScript disabled.

### Validation rules (server-side, in the route)

| Field | Rule | Error message on failure |
| --- | --- | --- |
| `amount` | Required, must parse as `float`, must be `> 0` | `"Please enter a valid amount greater than zero."` |
| `category` | Required, must be one of `CATEGORIES` | `"Please choose a category."` |
| `date` | Required, must parse as `YYYY-MM-DD` | `"Please enter a valid date."` |
| `description` | Optional, trimmed, max 200 characters | (silently truncated by the `<input maxlength>` — no server check needed) |

On any failure, re-render `add_expense.html` with the matching `error` string, **re-populating the form with the previously-submitted values** (except the password-style `amount`, which is re-rendered as a string). The selected `<option>` for `category` and the `value=` for `date` and `description` are re-populated from `request.form` so the user only fixes the bad field.

---

## Definition of Done

- [ ] `GET /expenses/add` while logged in renders the empty add-expense form (amount, category, date, description).
- [ ] `GET /expenses/add` while logged out redirects to `/login` (same guard as `/profile`).
- [ ] Submitting the form with a valid amount, category, and date inserts a new row in `expenses` with `user_id = session["user_id"]` and redirects to `/profile` with HTTP 302.
- [ ] After a successful add, the new row appears in the "Recent transactions" table on `/profile` (and contributes to the stats and category breakdown) — provided the new row's date is inside the active date filter; if it is outside, switching the filter to "All time" reveals it.
- [ ] Submitting with a missing, non-numeric, zero, or negative `amount` re-renders the form with `"Please enter a valid amount greater than zero."` in the error box, and inserts no row.
- [ ] Submitting with a category that is not in `CATEGORIES` (e.g. a value injected via devtools) re-renders the form with `"Please choose a category."` and inserts no row.
- [ ] Submitting with a missing or malformed `date` re-renders the form with `"Please enter a valid date."` and inserts no row.
- [ ] After any validation failure, the form fields are re-populated with the previously-submitted values (except invalid `amount`, which is left blank) so the user only has to fix the bad field.
- [ ] The new row's `user_id` matches `session["user_id"]` — a second logged-in user cannot see or be charged for the first user's expense (verifiable by registering a second user, adding an expense, and confirming the first user's `/profile` is unchanged).
- [ ] `create_expense()` exists in `database/db.py` and uses a single parameterized `INSERT`; no SQL appears in `app.py`.
- [ ] The form's `action` is generated with `url_for('add_expense')`; the "Cancel" link uses `url_for('profile')`. No hardcoded URLs.
- [ ] The new template extends `base.html` and uses only CSS variables for any styling — no inline styles, no hardcoded hex values.
- [ ] The app still starts and runs on port 5001 with no new pip packages, and `requirements.txt` is unchanged.
