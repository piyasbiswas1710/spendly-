# Spec: Delete Expense

## Overview

This feature replaces the `/expenses/<id>/delete` stub with a real "delete expense" flow: a logged-in user clicks "Delete" next to a transaction on `/profile`, lands on a confirmation page showing that expense's details, and confirms the deletion by submitting a form. The server re-validates ownership, removes the row from the `expenses` table, and redirects back to `/profile`, where the deleted transaction no longer appears. A user attempting to delete an expense that does not belong to them — or that does not exist — is treated as a 404 and never sees the confirmation page or deletes anything.

It belongs at this stage of the Spendly roadmap because Steps 1–8 have established the `expenses` schema, the session-scoped profile page, the date-filter machinery, and — critically — Step 8's row-by-id ownership pattern (`get_expense_by_id`, `WHERE id = ? AND user_id = ?`, `abort(404)` on miss). Step 9 reuses that exact pattern for a destructive operation, closing out full CRUD (create, read, update, delete) on the `expenses` table. Delete is intentionally a confirm-then-commit flow (`GET` shows a confirmation page, `POST` performs the delete) rather than a single-click `GET`, so an accidental click, browser prefetch, or crawler cannot silently destroy data.

---

## Depends on

- **Step 1 — Database Setup:** `get_db()`, the `expenses` table (`id`, `user_id`, `amount REAL`, `category TEXT`, `date TEXT`, `description TEXT`, `created_at`).
- **Step 3 — Login and Logout:** `session["user_id"]` is the only way to know which user's expense is being deleted, and the gatekeeper for the route.
- **Step 5 — Profile Page Backend Routes:** `get_recent_transactions()`, `get_profile_stats()`, and `get_category_breakdown()` must reflect the deletion immediately once the row is gone.
- **Step 6 — Date Filter:** the redirect target `/profile` honors the active `range` filter — this is unaffected by a delete, but is noted for consistency with Steps 7–8.
- **Step 7 — Add Expense:** the visual language of the `auth-card`-style form/card layout, reused for the confirmation page.
- **Step 8 — Edit Expense:** `get_expense_by_id(expense_id, user_id)` is reused as-is to load the expense for the confirmation page and to gate the delete. The ownership-check-in-SQL pattern (`WHERE id = ? AND user_id = ?`, `abort(404)` on miss) is mirrored exactly for the new `delete_expense()` helper.

---

## Routes

```text
GET  /expenses/<id>/delete   — Render a confirmation page showing the expense's details — Logged-in
POST /expenses/<id>/delete   — Delete the row, redirect to /profile                      — Logged-in
```

The existing `delete_expense(id)` placeholder in `app.py` (which currently returns the string `"Delete expense — coming in Step 9"`) is extended to `methods=["GET", "POST"]`. No new URL paths are added.

Authentication is required for both verbs — unauthenticated users are redirected to `/login` (same guard as `/profile`, `/expenses/add`, and `/expenses/<id>/edit`).

**Authorization (ownership) rule:** both verbs load/act on the expense by `id` AND `user_id = session["user_id"]` in a single query, exactly as Step 8 does. If the row does not exist OR it exists but belongs to a different user, the route responds with HTTP 404 (`abort(404)`) — the user must not be able to tell the two cases apart.

---

## Database Changes

**No schema changes.** The existing `expenses` table from Step 1 is sufficient.

**New helper function to add to `database/db.py`** (no SQL in route functions):

### `delete_expense(expense_id, user_id)`

- Runs `DELETE FROM expenses WHERE id = ? AND user_id = ?` with a fully parameterized query.
- Calls `conn.commit()`.
- Returns the number of rows affected (`cursor.rowcount`): `1` if the row was owned by this user and deleted, `0` if no row matched (either no such id, or the id belongs to another user). The route must check this and `abort(404)` on `0` — same ownership rule as `get_expense_by_id` and `update_expense`.
- Reuses the existing `get_db()` (which already sets `row_factory` and `PRAGMA foreign_keys = ON`).

**Reused, unchanged helper:**

### `get_expense_by_id(expense_id, user_id)` (from Step 8)

- Used on `GET` to load the row for the confirmation page. No changes needed.

---

## Templates

### Create

- `templates/delete_expense.html` — extends `base.html`; contains:
  1. A page header (e.g. "Delete expense") and a short warning line (e.g. "This action cannot be undone.").
  2. An `auth-card`-style card, mirroring the visual language of `add_expense.html` / `edit_expense.html`, that displays the expense's current values **read-only** (date, category, amount, description) so the user can confirm they are deleting the right row.
  3. A form that `POST`s to `url_for('delete_expense', id=id)` with a single primary "Delete" submit button (styled with the existing `--danger` CSS variable, not a hardcoded hex value) and a secondary "Cancel" link that goes back to `/profile` (via `url_for('profile')`).

### Modify

- `templates/profile.html` — in the `txn-actions` cell of the transactions table (around line 88-90), add a "Delete" link next to the existing "Edit" link, pointing to `url_for('delete_expense', id=t.id)`.

---

## Files to Change

| File                    | Purpose |
| --- | --- |
| `app.py`                | Replace the `delete_expense(id)` stub with a real `GET`/`POST` view: guard the route, load the row with `get_expense_by_id` (aborting 404 if missing) to render the confirmation page on `GET`, and on `POST` call `delete_expense`, check the rowcount and abort 404 on miss, then redirect to `/profile` on success. Import `delete_expense` from `database/db` (`get_expense_by_id` is already imported from Step 8). |
| `database/db.py`        | Add `delete_expense(expense_id, user_id)`. |
| `templates/profile.html`| Add a "Delete" link in the `txn-actions` cell, next to "Edit". |
| `static/css/style.css`  | Add a `.txn-delete-link` style (using `var(--danger)`) alongside the existing `.txn-edit-link`, and a danger-styled submit button class for the confirmation page's "Delete" button if `.btn-submit` needs a red variant. |

---

## Files to Create

| File                             | Purpose |
| --- | --- |
| `templates/delete_expense.html` | The delete-confirmation page described above. |

---

## New Dependencies

```text
No new dependencies.
```

`sqlite3` (stdlib) and `flask.abort` are already available. No new pip packages are required.

---

## Rules for Implementation

- **No SQLAlchemy or ORMs.** Use `sqlite3` via the existing `get_db()` only.
- **Parameterized SQL queries only** — `?` placeholders, never f-strings or string concatenation in SQL. The `DELETE` in `delete_expense` must use two `?` placeholders.
- **All database access lives in `database/db.py`.** The route calls `get_expense_by_id()` / `delete_expense()` — no SQL or `get_db()` in `app.py`.
- **Hash passwords using `werkzeug`** — unchanged in this step (no auth logic touched).
- **Use CSS variables; never hardcode hex color values.** Any new "danger" styling (delete link, delete button) must reference the existing `--danger` / `--danger-light` variables in `:root` — never a raw hex value.
- **All templates must extend `base.html`.** `delete_expense.html` must.
- **No hardcoded URLs** — the confirmation form's `action` uses `url_for('delete_expense', id=id)`, the "Cancel" link and post-delete redirect use `url_for('profile')`, the auth-guard redirect uses `url_for('login')`, and the new link in `profile.html` uses `url_for('delete_expense', id=t.id)`.
- **Never return raw strings from the route** — always `render_template()` (on `GET`) or `redirect()` / `abort()` (on `POST` success or 404).
- **Route stays single-responsibility** — load row (with ownership check), render confirmation or delete, redirect or abort.
- **Session check first** — if `session.get("user_id")` is missing, redirect to `/login` before doing anything else (including the ownership check, so a logged-out user never sees the confirmation page or learns whether the id exists).
- **Ownership check via SQL, not Python** — both the `GET` read and the `POST` delete use `WHERE id = ? AND user_id = ?`. The route must never load a row by `id` alone and then compare `user_id` in Python.
- **404 on missing or not-owned** — `abort(404)` in both the `GET` (no row to confirm) and the `POST` (the `delete_expense` rowcount is `0`) cases.
- **Destructive action requires POST** — the actual delete only happens on `POST`, never on `GET`. `GET` only ever renders a read-only confirmation page; it must not delete anything, even if visited repeatedly (e.g. by a crawler or browser prefetch).
- **No confirmation JavaScript required** — the confirmation is the dedicated `GET` page itself (a real, separate step the user must submit a form on), not a client-side `confirm()` dialog. The form is functional with JavaScript disabled.

---

## Definition of Done

- [ ] `GET /expenses/<id>/delete` while logged in, for an expense owned by the logged-in user, renders a confirmation page showing that expense's date, category, amount, and description (read-only).
- [ ] `GET /expenses/<id>/delete` while logged out redirects to `/login` (same guard as `/profile`), without performing any DB read.
- [ ] `GET /expenses/<id>/delete` for an `id` that does not exist returns HTTP 404.
- [ ] `GET /expenses/<id>/delete` for an `id` that belongs to a different user returns HTTP 404 (verifiable by registering a second user, creating an expense as that user, and visiting the first user's `id` in the URL — the second user must see 404, not the confirmation page).
- [ ] `GET /expenses/<id>/delete`, visited any number of times, never deletes the row — the row still exists in `expenses` afterward.
- [ ] Submitting the confirmation form (`POST /expenses/<id>/delete`) for an owned, existing expense removes the row from `expenses` and redirects to `/profile` with HTTP 302.
- [ ] After a successful delete, the deleted transaction no longer appears in the "Recent transactions" table on `/profile`, and it no longer contributes to the stats or category breakdown.
- [ ] `POST /expenses/<id>/delete` for an `id` that does not exist returns HTTP 404 and deletes no row.
- [ ] `POST /expenses/<id>/delete` for an `id` that belongs to a different user returns HTTP 404, deletes no row, and does not leak the other user's data.
- [ ] `POST /expenses/<id>/delete` while logged out redirects to `/login` without deleting any row.
- [ ] `delete_expense()` exists in `database/db.py` and uses a single parameterized `DELETE` with a `WHERE id = ? AND user_id = ?` ownership clause; no SQL appears in `app.py`.
- [ ] The confirmation form's `action` is generated with `url_for('delete_expense', id=id)`; the "Cancel" link uses `url_for('profile')`. No hardcoded URLs.
- [ ] `profile.html` shows a "Delete" link next to "Edit" for each transaction, generated with `url_for('delete_expense', id=t.id)`.
- [ ] The new template extends `base.html` and uses only CSS variables for any styling (including the danger/delete color) — no inline styles, no hardcoded hex values.
- [ ] The app still starts and runs on port 5001 with no new pip packages, and `requirements.txt` is unchanged.
