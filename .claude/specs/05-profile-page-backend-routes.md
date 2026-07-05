# Spec: Profile Page Backend Routes

## Overview

Step 4 built the `/profile` page UI with fully hardcoded data (a fixed user, fixed stats, fixed transactions, fixed category breakdown) so the design could be validated in isolation. This step replaces every hardcoded value in the `profile()` view with real queries against the `users` and `expenses` tables via `database/db.py`, so the profile page reflects the actual logged-in user's data. It belongs here because it is the natural "wire it up" step referenced directly in `app.py`'s Step 4 comment ("Step 5 will replace it with real queries via database/db.py") and because it must land before Steps 7–9 (add/edit/delete expense), which need the same query helpers to show updated data.

---

## Depends on

- **Step 1 — Database Setup:** `get_db()`, the `users` and `expenses` tables, the `CATEGORIES` constant.
- **Step 2 — Registration:** `create_user()`, so real users with real `created_at` timestamps exist.
- **Step 3 — Login and Logout:** `session["user_id"]` is set on login; `/profile` is already guarded by the session check.
- **Step 4 — Profile Page:** `templates/profile.html` already exists and expects `user`, `stats`, `transactions`, and `categories` context variables in the exact shapes below.

---

## Routes

```text
No new routes.
```

`GET /profile` already exists (Step 3/4) and is already guarded by `if not session.get("user_id"): redirect(url_for("login"))`. This step only changes what data the view fetches and passes to the template — the route path, method, and guard stay the same.

---

## Database Changes

No new tables or columns — the existing `users` and `expenses` tables (verified in `database/db.py`) are sufficient.

**New helper functions to add to `database/db.py`** (all parameterized, all returning `sqlite3.Row` objects or plain dicts/lists built from them — no SQL or aggregation logic in `app.py`):

1. `get_user_by_id(user_id)` — `SELECT * FROM users WHERE id = ?`; returns the `Row`, or `None` if not found.
2. `get_recent_transactions(user_id, limit=10)` — `SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT ?`; returns a list of dicts `{"date": "<DD Mon YYYY>", "description": ..., "category": ..., "amount": ...}`, converting the stored ISO date (`YYYY-MM-DD`) to the `profile.html`-expected display format (e.g. `21 Jul 2026`) inside this helper.
3. `get_profile_stats(user_id)` — runs aggregate queries (`SUM(amount)`, `COUNT(*)`, and a `GROUP BY category` to find the highest-total category) and returns `{"total_spent": <float>, "transaction_count": <int>, "top_category": <str>}`. When the user has zero expenses, returns `{"total_spent": 0, "transaction_count": 0, "top_category": "—"}`.
4. `get_category_breakdown(user_id)` — `SELECT category, SUM(amount) AS total FROM expenses WHERE user_id = ? GROUP BY category ORDER BY total DESC`; computes each category's percent of the grand total (rounded to the nearest whole number) and returns a list of dicts `{"name": ..., "amount": ..., "percent": ...}`. Returns `[]` when the user has zero expenses.

`app.py`'s `profile()` view calls these four functions, builds the small `user` dict expected by the template (`name`, `email`, `initials` derived from `name`, `member_since` formatted from `created_at` as `"Month YYYY"`), and renders `profile.html` — no SQL, aggregation, or `GROUP BY` logic lives in the route itself.

---

## Templates

### Create

```text
No new templates.
```

### Modify

```text
No template changes.
```

`templates/profile.html` already consumes `user`, `stats`, `transactions`, and `categories` in the exact shapes the new `db.py` helpers will produce — no markup changes needed.

---

## Files to Change

| File              | Purpose                                                                                                   |
| ----------------- | ----------------------------------------------------------------------------------------------------------|
| `app.py`           | Replace the hardcoded `user`/`stats`/`transactions`/`categories` in `profile()` with calls to the new `database/db.py` helpers. |
| `database/db.py`   | Add `get_user_by_id`, `get_recent_transactions`, `get_profile_stats`, `get_category_breakdown`.             |

---

## Files to Create

```text
No new files.
```

---

## New Dependencies

```text
No new dependencies.
```

---

## Rules for Implementation

- No SQLAlchemy or ORMs.
- Parameterized SQL queries only — never f-strings or string concatenation in SQL.
- Hash/verify passwords using `werkzeug` — unchanged in this step (no auth logic touched).
- Use CSS variables; never hardcode hex color values — unchanged in this step (no CSS touched).
- All templates must extend `base.html` — unchanged, no template edits in this step.
- Keep all DB queries and aggregation inside `database/db.py`; `profile()` in `app.py` only calls helpers, formats the tiny `user` display dict, and renders the template.
- Never return raw strings from `/profile` — continue using `render_template()`.
- Never hardcode internal URLs — continue using `url_for()`.
- Keep the app on port 5001.
- Handle the zero-expenses case gracefully (new user with no transactions yet): stats show `0` / `"—"`, transactions table is empty, category breakdown is empty — no crashes, no divide-by-zero.

---

## Definition of Done

- [ ] Visiting `/profile` without being logged in still redirects to `/login`.
- [ ] Visiting `/profile` while logged in as the seeded demo user (`demo@spendly.com` / `demo123`) returns HTTP 200 and shows that user's real name, email, and initials (not "Demo User" hardcoded text).
- [ ] The "Total spent" and "Transactions" stats match the actual sum/count of that user's rows in the `expenses` table.
- [ ] The "Top category" stat matches the category with the highest total for that user.
- [ ] The transaction history table lists that user's actual expenses, most recent first, with dates in `DD Mon YYYY` format.
- [ ] The category breakdown section shows only categories the user actually has expenses in, with percentages that sum to (approximately) 100.
- [ ] Registering a brand-new user and visiting `/profile` immediately after (zero expenses) renders without errors — stats show `0`/`"—"`, and the transaction/category sections render empty instead of crashing.
- [ ] No SQL queries or aggregation logic appear inside `app.py`.
- [ ] The app still starts and runs on port 5001 with no new pip packages.
