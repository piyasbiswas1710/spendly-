# Spec: Edit Expense

## Overview

This feature replaces the `/expenses/<id>/edit` stub with a real "edit expense" flow: a logged-in user navigates to the edit URL, sees the expense's current values pre-populated in a form, changes one or more fields, the server validates the input and updates the row in the `expenses` table (scoped to the logged-in user), and the user is redirected back to `/profile` where the updated transaction appears in the recent transactions list (subject to the active date filter). A user editing an expense that does not belong to them — or that does not exist — is treated as a 404 and never sees or modifies the row.

It belongs at this stage of the Spendly roadmap because Steps 1–7 have established the `expenses` schema, the session-scoped profile page, the date-filter machinery, and the canonical "add" form-and-validation pattern. Step 9 (delete) will mirror this step's row-by-id authorization pattern, so this is the canonical place to define how a write to a specific existing `expenses` row is loaded, ownership-checked, validated, updated, and re-rendered. The edit form is intentionally a near-clone of `add_expense.html` — same fields, same validation rules, same visual language — so users see one consistent form for "add" and "edit".

---

## Depends on

- **Step 1 — Database Setup:** `get_db()`, the `expenses` table (`id`, `user_id`, `amount REAL`, `category TEXT`, `date TEXT`, `description TEXT`, `created_at`), and the `CATEGORIES` constant in `database/db.py`.
- **Step 3 — Login and Logout:** `session["user_id"]` is the only way to know which user the edit belongs to, and the gatekeeper for the route.
- **Step 5 — Profile Page Backend Routes:** `get_recent_transactions()`, `get_profile_stats()`, and `get_category_breakdown()` must keep working with the updated row so the profile page reflects the edit immediately.
- **Step 6 — Date Filter:** the redirect target `/profile` honors the active `range` filter, so an edited expense whose `date` moved outside the active range will not appear until the user changes the filter — this is expected behavior, not a bug.
- **Step 7 — Add Expense:** the validation rules (positive amount, category in `CATEGORIES`, `YYYY-MM-DD` date, trimmed description) and the form template's visual language. This step reuses both verbatim so a user never has to learn two different "edit" rules.

---

## Routes

```text
GET  /expenses/<id>/edit     — Render the form pre-populated with this expense's current values — Logged-in
POST /expenses/<id>/edit     — Validate input, update the row, redirect to /profile        — Logged-in
```

The existing `edit_expense(id)` placeholder in `app.py` (which currently returns the string `"Edit expense — coming in Step 8"`) is extended to `methods=["GET", "POST"]`. No new URL paths are added.

Authentication is required for both verbs — unauthenticated users are redirected to `/login` (same guard as `/profile` and `/expenses/add`).

**Authorization (ownership) rule:** the route must load the expense by `id` AND `user_id = session["user_id"]` in a single query. If the row does not exist OR it exists but belongs to a different user, the route responds with HTTP 404 (`abort(404)`) — the user must not be able to tell the two cases apart. This prevents user A from editing user B's expenses by guessing or enumerating `id` values.

---

## Database Changes

**No schema changes.** The existing `expenses` table from Step 1 is sufficient.

**New helper functions to add to `database/db.py`** (no SQL in route functions):

### `get_expense_by_id(expense_id, user_id)`

- Runs `SELECT * FROM expenses WHERE id = ? AND user_id = ?` with a fully parameterized query.
- Returns the matching `sqlite3.Row` (or `None` if no row matches both the `id` and the `user_id`).
- Used to (a) load the row for the `GET` pre-population and (b) gate the `POST` update on a real ownership check before any write happens.

### `update_expense(expense_id, user_id, amount, category, date, description)`

- Runs `UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? WHERE id = ? AND user_id = ?` with a fully parameterized query.
- Calls `conn.commit()`.
- Returns the number of rows affected (`cursor.rowcount`): `1` if the row was owned by this user and updated, `0` if no row matched (either no such id, or the id belongs to another user). The route must check this and `abort(404)` on `0` — same ownership rule as `get_expense_by_id`.
- Performs no validation — that responsibility lives in the route, mirroring `create_expense()` from Step 7.
- Reuses the existing `get_db()` (which already sets `row_factory` and `PRAGMA foreign_keys = ON`).

The two helpers together keep the route free of any SQL and ensure every read/write is ownership-checked in SQL itself, not in Python.

---

## Templates

### Create

- `templates/edit_expense.html` — extends `base.html`; contains:
  1. A page header (e.g. "Edit expense") and a short helper line that includes the expense id (for context, e.g. "Editing expense #12").
  2. An `auth-card`-style form card with the `auth-error` block at the top, mirroring the visual language of `add_expense.html` / `register.html` / `login.html` for consistency.
  3. Form fields — **identical markup to `add_expense.html`** except each field is pre-populated from the loaded expense (or from the previously-submitted `request.form` on a `POST` validation failure):
     - **Amount** (`<input type="number" name="amount" step="0.01" min="0.01" required>`) with a `₹` prefix label.
     - **Category** (`<select name="category" required>`) populated from `CATEGORIES` in `app.py`, with the matching `<option selected>` for the current value.
     - **Date** (`<input type="date" name="date" required>`) pre-populated with the current `YYYY-MM-DD`.
     - **Description** (`<input type="text" name="description" maxlength="200">`) pre-populated with the current description (may be empty string).
  4. A primary submit button labeled "Save changes" and a secondary "Cancel" link that goes back to `/profile` (via `url_for('profile')`).
  5. The form posts to `url_for('edit_expense', id=id)` (passing the `id` explicitly so the path keeps the expense id) — never a hardcoded URL.

### Modify

```text
No template changes.
```

`base.html`, `add_expense.html`, `profile.html`, `login.html`, and `register.html` are unchanged. The new template is fully self-contained.

---

## Files to Change

| File             | Purpose |
| --- | --- |
| `app.py`         | Replace the `edit_expense(id)` stub with a real `GET`/`POST` view: guard the route, load the row with `get_expense_by_id` (aborting 404 if missing), render the form pre-populated with the loaded values (or `request.form` on a `POST` validation failure), validate input, call `update_expense`, check the rowcount and abort 404 on miss, and redirect to `/profile` on success. Import `update_expense` and `get_expense_by_id` from `database/db`. |
| `database/db.py` | Add `get_expense_by_id(expense_id, user_id)` and `update_expense(expense_id, user_id, amount, category, date, description)`. |

---

## Files to Create

| File                         | Purpose |
| --- | --- |
| `templates/edit_expense.html` | The "edit expense" form described above. |

---

## New Dependencies

```text
No new dependencies.
```

`sqlite3` (stdlib), `werkzeug`, and `flask.abort` are already available. No new pip packages are required.

---

## Rules for Implementation

- **No SQLAlchemy or ORMs.** Use `sqlite3` via the existing `get_db()` only.
- **Parameterized SQL queries only** — `?` placeholders, never f-strings or string concatenation in SQL. The `SELECT` in `get_expense_by_id` must use two `?` placeholders; the `UPDATE` in `update_expense` must use six `?` placeholders.
- **All database access lives in `database/db.py`.** The route calls `get_expense_by_id()` / `update_expense()` — no SQL or `get_db()` in `app.py`.
- **Hash passwords using `werkzeug`** — unchanged in this step (no auth logic touched).
- **Use CSS variables; never hardcode hex color values.** The new template reuses the existing `auth-*` / `form-*` / `btn-submit` classes; if any new CSS is needed, it must reference existing variables in `:root` (or add a new variable there).
- **All templates must extend `base.html`.** `edit_expense.html` must.
- **No hardcoded URLs** — the form `action` uses `url_for('edit_expense', id=id)`, the "Cancel" link uses `url_for('profile')`, and the auth-guard redirect uses `url_for('login')`.
- **Never return raw strings from the route** — always `render_template()` (on validation failure) or `redirect()` / `abort()` (on success or 404).
- **Route stays single-responsibility** — load row (with ownership check), render or validate, update, redirect or re-render.
- **Session check first** — if `session.get("user_id")` is missing, redirect to `/login` before doing anything else (including the ownership check, so a logged-out user never sees the form or learns whether the id exists).
- **Ownership check via SQL, not Python** — both the read and the write use `WHERE id = ? AND user_id = ?`. The route must never load a row by `id` alone and then compare `user_id` in Python; that opens a window where the wrong user's data is in memory.
- **404 on missing or not-owned** — `abort(404)` in both the `GET` (no row to pre-populate) and the `POST` (the `update_expense` rowcount is `0`) cases. Use `from flask import abort` in `app.py`.
- **Category whitelist** — only accept categories that are in `CATEGORIES`; reject anything else. Do not trust the form value.
- **Currency** — amounts are stored in rupees (no subunit conversion); the form uses `step="0.01"` so users can enter paise but the stored value is still a single `REAL` column.
- **Date format** — the form uses `<input type="date">` which posts `YYYY-MM-DD`, exactly the format `expenses.date` expects. No parsing or reformatting needed.
- **Description** — trim whitespace; allow empty (store as empty string, not `NULL`, so reads are uniform).
- **Server-side validation only** — no client-side JS validation. The form is functional with JavaScript disabled.

### Validation rules (server-side, in the route)

Identical to Step 7 (`add_expense`):

| Field | Rule | Error message on failure |
| --- | --- | --- |
| `amount` | Required, must parse as `float`, must be `> 0` | `"Please enter a valid amount greater than zero."` |
| `category` | Required, must be one of `CATEGORIES` | `"Please choose a category."` |
| `date` | Required, must parse as `YYYY-MM-DD` | `"Please enter a valid date."` |
| `description` | Optional, trimmed, max 200 characters | (silently truncated by the `<input maxlength>` — no server check needed) |

On any failure, re-render `edit_expense.html` with the matching `error` string, **re-populating the form with the previously-submitted values** (so the user only fixes the bad field, not the whole form). The selected `<option>` for `category` and the `value=` for `date` and `description` are re-populated from `request.form`.

On a successful `POST`, the row in `expenses` is updated in place — `id`, `user_id`, and `created_at` are **not** changed. Only `amount`, `category`, `date`, and `description` are overwritten.

---

## Definition of Done

- [ ] `GET /expenses/<id>/edit` while logged in, for an expense owned by the logged-in user, renders the edit form pre-populated with that expense's current `amount`, `category`, `date`, and `description`.
- [ ] `GET /expenses/<id>/edit` while logged out redirects to `/login` (same guard as `/profile`), without performing any DB read.
- [ ] `GET /expenses/<id>/edit` for an `id` that does not exist returns HTTP 404.
- [ ] `GET /expenses/<id>/edit` for an `id` that belongs to a different user returns HTTP 404 (verifiable by registering a second user, creating an expense as that user, and visiting the first user's `id` in the URL — the second user must see 404, not the form).
- [ ] Submitting the form with a valid amount, category, and date updates the row in `expenses` (changing only `amount`, `category`, `date`, `description` — `id`, `user_id`, `created_at` are unchanged) and redirects to `/profile` with HTTP 302.
- [ ] After a successful edit, the updated row appears in the "Recent transactions" table on `/profile` (and its new values contribute to the stats and category breakdown) — provided the (possibly-changed) `date` is inside the active date filter; if it is outside, switching the filter to "All time" reveals it.
- [ ] Submitting with a missing, non-numeric, zero, or negative `amount` re-renders the form with `"Please enter a valid amount greater than zero."` in the error box, performs no `UPDATE`, and preserves the user's other submitted values.
- [ ] Submitting with a category that is not in `CATEGORIES` re-renders the form with `"Please choose a category."` and performs no `UPDATE`.
- [ ] Submitting with a missing or malformed `date` re-renders the form with `"Please enter a valid date."` and performs no `UPDATE`.
- [ ] After any validation failure, the form fields are re-populated with the previously-submitted values (except invalid `amount`, which is left blank) so the user only has to fix the bad field.
- [ ] `POST /expenses/<id>/edit` for an `id` that does not exist returns HTTP 404 and performs no `UPDATE`.
- [ ] `POST /expenses/<id>/edit` for an `id` that belongs to a different user returns HTTP 404, performs no `UPDATE`, and does not leak the other user's data (no error message reveals the existence of the row).
- [ ] The row's `user_id` matches the logged-in user — a second logged-in user cannot edit the first user's expense (verifiable by the same two-user test as the `GET`).
- [ ] `get_expense_by_id()` and `update_expense()` exist in `database/db.py`; both use `WHERE id = ? AND user_id = ?` ownership clauses with parameterized queries; no SQL appears in `app.py`.
- [ ] The form's `action` is generated with `url_for('edit_expense', id=id)`; the "Cancel" link uses `url_for('profile')`. No hardcoded URLs.
- [ ] The new template extends `base.html` and uses only CSS variables for any styling — no inline styles, no hardcoded hex values.
- [ ] The app still starts and runs on port 5001 with no new pip packages, and `requirements.txt` is unchanged.
