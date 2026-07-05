# Spec: Date Filter

## Overview

Step 5 wired `/profile` up to real `users`/`expenses` data, but the transaction history and stats always cover the user's *entire* history (or the 10 most recent rows) with no way to narrow the view to a specific time range. This step adds a date filter to the profile page — a small form with preset ranges (This Month, Last Month, Last 30 Days, All Time) plus a Custom option with explicit start/end date inputs — so the transaction list, the stats row, and the category breakdown all reflect only expenses inside the selected range. It belongs here because it is the natural next enhancement to the profile page once real data is flowing (Step 5), and it must land before Steps 7–9 (add/edit/delete expense) so that newly added/edited/deleted expenses are exercised against a page that already supports date-scoped views.

---

## Depends on

- **Step 1 — Database Setup:** `get_db()`, the `expenses` table's `date` column (`YYYY-MM-DD` text, sortable lexicographically).
- **Step 3 — Login and Logout:** `session["user_id"]`, used to scope every filtered query to the logged-in user.
- **Step 4 — Profile Page:** `templates/profile.html` structure (stats row, transaction table, category breakdown) that the filter form will sit above and whose sections it will re-render with filtered data.
- **Step 5 — Profile Page Backend Routes:** `get_recent_transactions()`, `get_profile_stats()`, `get_category_breakdown()` in `database/db.py`, which this step extends with optional date-range parameters rather than replacing.

---

## Routes

```text
No new routes.
```

`GET /profile` (existing, Step 3/4/5) is extended to read optional query-string parameters — `range` (one of `this_month`, `last_month`, `last_30_days`, `all_time`, `custom`; defaults to `all_time`) and, when `range=custom`, `start_date` and `end_date` (`YYYY-MM-DD`) — and passes the resolved date bounds to the Step 5 helpers. The route path, method, and login guard are unchanged.

---

## Database Changes

```text
No new tables or columns.
```

**Modify existing helpers in `database/db.py`** to accept optional `start_date` and `end_date` (`YYYY-MM-DD` strings, inclusive; `None` means unbounded on that side):

1. `get_recent_transactions(user_id, limit=10, start_date=None, end_date=None)` — adds `AND date >= ?` / `AND date <= ?` clauses (only when the corresponding argument is not `None`) to the existing `WHERE user_id = ?` query, still parameterized, still ordered `date DESC, id DESC`.
2. `get_profile_stats(user_id, start_date=None, end_date=None)` — applies the same optional bounds before aggregating `SUM(amount)` / `COUNT(*)`; zero-expense-in-range behavior stays identical to today's zero-expense behavior (`{"total_spent": 0, "transaction_count": 0, "top_category": "—"}`).
3. `get_category_breakdown(user_id, start_date=None, end_date=None)` — applies the same optional bounds before the `GROUP BY category` aggregation; returns `[]` when no expenses fall in range.

Add one new helper:

4. `resolve_date_range(range_key, start_date=None, end_date=None)` — given `range_key` (`this_month`, `last_month`, `last_30_days`, `all_time`, `custom`) and, for `custom`, the raw `start_date`/`end_date` strings, returns a `(start_date, end_date)` tuple of `YYYY-MM-DD` strings or `None` values ready to pass straight into the three helpers above. Keeps all date-math (month boundaries, "last 30 days" from today, validating/falling back on malformed custom dates) out of `app.py`.

---

## Templates

### Create

```text
No new templates.
```

### Modify

- `templates/profile.html` — add a filter form directly above the "Recent transactions" card: a `<select>` of preset ranges plus two `<input type="date">` fields for the custom range (hidden unless "Custom" is selected). The form submits via `GET` to `url_for('profile')` so filtering works without JavaScript; the currently-selected range/dates are re-populated from the values `app.py` passes back into the template so the page reflects the active filter on reload.

---

## Files to Change

| File                  | Purpose                                                                                                          |
| --------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `app.py`              | Read `range`/`start_date`/`end_date` query params in `profile()`, call `resolve_date_range()`, pass resolved bounds into the Step 5 helpers, and pass the active filter values back to the template. |
| `database/db.py`      | Add optional `start_date`/`end_date` params to `get_recent_transactions`, `get_profile_stats`, `get_category_breakdown`; add `resolve_date_range()`. |
| `templates/profile.html` | Add the date-filter form above the transaction history card.                                                   |
| `static/js/main.js`   | Add a small handler to show/hide the custom start/end date inputs when the range `<select>` changes, and to auto-submit the filter form on select change. |
| `static/css/style.css`  | Add styling for the new filter form using existing CSS variables — no hardcoded hex values.                      |

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
- Parameterized SQL queries only — never f-strings or string concatenation in SQL, including the new optional `date >= ?` / `date <= ?` clauses.
- Hash passwords using `werkzeug` — unchanged in this step (no auth logic touched).
- Use CSS variables; never hardcode hex color values.
- All templates must extend `base.html` — `profile.html` already does; unchanged.
- Keep all date-range resolution and SQL filtering inside `database/db.py`; `profile()` in `app.py` only reads query params, calls helpers, and renders the template.
- Never return raw strings from `/profile` — continue using `render_template()`.
- Never hardcode internal URLs — continue using `url_for()`.
- Keep the app on port 5001.
- Malformed or missing custom dates must not crash the page — `resolve_date_range()` falls back to `all_time` bounds in that case.

---

## Definition of Done

- [ ] Visiting `/profile` with no query params shows all-time data, identical to today's behavior.
- [ ] Selecting "This Month" shows only expenses dated within the current calendar month.
- [ ] Selecting "Last Month" shows only expenses dated within the previous calendar month.
- [ ] Selecting "Last 30 Days" shows only expenses within the last 30 days of today.
- [ ] Selecting "Custom" and entering a start/end date shows only expenses within that inclusive range.
- [ ] The stats row (total spent, transaction count, top category) and the category breakdown both update to match the selected range, not just the transaction table.
- [ ] Reloading the page (or following a link back to it) with the same query params preserves the selected filter, including re-populating the custom date inputs.
- [ ] An empty result set for the selected range renders gracefully — stats show `0`/`"—"`, transaction table and category breakdown render empty, no errors.
- [ ] Submitting an invalid/malformed custom date does not crash the page — it falls back to all-time data.
- [ ] No SQL queries or date-range logic appear inside `app.py`.
- [ ] The app still starts and runs on port 5001 with no new pip packages.
