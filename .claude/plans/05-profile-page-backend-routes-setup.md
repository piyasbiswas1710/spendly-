# Implementation Plan: Profile Page Backend Routes (Step 5)

## Goal
Replace the hardcoded data in the `/profile` view (built in Step 4) with real
queries against the `users` and `expenses` tables, so the profile page reflects
the actual logged-in user's data.

## Why This Step Exists
- Step 4 built the `/profile` UI with fixed/fake data to validate design in isolation.
- `app.py`'s Step 4 comment already flags this: *"Step 5 will replace it with real queries via database/db.py"*.
- This must land before Steps 7–9 (add/edit/delete expense), since those steps
  need the same query helpers to reflect updated data on the profile page.

---

## Prerequisites (Already Done)

| Step | What it provides |
|---|---|
| Step 1 — Database Setup | `get_db()`, `users` table, `expenses` table, `CATEGORIES` constant |
| Step 2 — Registration | `create_user()` — real users with real `created_at` timestamps |
| Step 3 — Login/Logout | `session["user_id"]` set on login; `/profile` already guarded |
| Step 4 — Profile Page | `templates/profile.html` exists, expects `user`, `stats`, `transactions`, `categories` |

---

## Routes
**No new routes.**
`GET /profile` already exists and is already guarded:
```python
if not session.get("user_id"):
    redirect(url_for("login"))
```
Only the *data* the view fetches changes — path, method, and guard stay the same.

---

## Database Layer — New Helpers to Add to `database/db.py`

All helpers must:
- Use parameterized SQL only (no f-strings/string concatenation)
- Return `sqlite3.Row` objects or plain dicts/lists built from them
- Contain **all** SQL/aggregation logic (none of it belongs in `app.py`)

### 1. `get_user_by_id(user_id)`
- `SELECT * FROM users WHERE id = ?`
- Returns the `Row`, or `None` if not found

### 2. `get_recent_transactions(user_id, limit=10)`
- `SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT ?`
- Returns a list of dicts:
  ```python
  {"date": "<DD Mon YYYY>", "description": ..., "category": ..., "amount": ...}
  ```
- Converts stored ISO date (`YYYY-MM-DD`) → display format (`21 Jul 2026`) **inside this helper**

### 3. `get_profile_stats(user_id)`
- Runs aggregates: `SUM(amount)`, `COUNT(*)`, and `GROUP BY category` (to find top category)
- Returns:
  ```python
  {"total_spent": <float>, "transaction_count": <int>, "top_category": <str>}
  ```
- Zero-expense case returns:
  ```python
  {"total_spent": 0, "transaction_count": 0, "top_category": "—"}
  ```

### 4. `get_category_breakdown(user_id)`
- `SELECT category, SUM(amount) AS total FROM expenses WHERE user_id = ? GROUP BY category ORDER BY total DESC`
- Computes each category's % of grand total (rounded to nearest whole number)
- Returns a list of dicts:
  ```python
  {"name": ..., "amount": ..., "percent": ...}
  ```
- Zero-expense case returns `[]`

---

## `app.py` Changes

The `profile()` view should:
1. Call the four new helper functions above
2. Build a small `user` display dict:
   - `name`, `email`
   - `initials` — derived from `name`
   - `member_since` — formatted from `created_at` as `"Month YYYY"`
3. Call `render_template("profile.html", ...)` with all context

**No SQL, aggregation, or `GROUP BY` logic should live in the route itself.**

---

## Templates
**No changes.** `templates/profile.html` already consumes `user`, `stats`,
`transactions`, `categories` in the exact shapes the new helpers will produce.

---

## Files Summary

| File | Change |
|---|---|
| `app.py` | Replace hardcoded `user`/`stats`/`transactions`/`categories` in `profile()` with calls to new `db.py` helpers |
| `database/db.py` | Add `get_user_by_id`, `get_recent_transactions`, `get_profile_stats`, `get_category_breakdown` |

**No new files. No new dependencies.**

---

## Implementation Rules

- ❌ No SQLAlchemy or ORMs
- ✅ Parameterized SQL queries only
- ✅ Password hashing via `werkzeug` — unchanged, not touched in this step
- ✅ Use CSS variables, never hardcoded hex colors — unchanged, no CSS touched
- ✅ All templates extend `base.html` — unchanged, no template edits
- ✅ All DB queries/aggregation stay inside `database/db.py`
- ✅ `profile()` in `app.py` only calls helpers, formats the small `user` dict, renders template
- ✅ Always use `render_template()` — never return raw strings
- ✅ Always use `url_for()` — never hardcode internal URLs
- ✅ Keep app running on port 5001
- ✅ Handle zero-expenses gracefully — no crashes, no divide-by-zero

---

## Definition of Done — Checklist

- [ ] `/profile` without login → redirects to `/login`
- [ ] `/profile` while logged in as seeded demo user (`demo@spendly.com` / `demo123`) → HTTP 200, shows real name/email/initials (not hardcoded "Demo User")
- [ ] "Total spent" and "Transactions" stats match actual sum/count from `expenses` table
- [ ] "Top category" stat matches the category with highest total for that user
- [ ] Transaction history table shows real expenses, most recent first, dates as `DD Mon YYYY`
- [ ] Category breakdown shows only categories the user actually has, percentages sum to ~100
- [ ] New user with zero expenses → `/profile` renders without errors (stats `0`/`"—"`, empty sections)
- [ ] No SQL/aggregation logic appears inside `app.py`
- [ ] App still starts/runs on port 5001, no new pip packages