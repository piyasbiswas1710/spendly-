# Plan: Add Expense

## Goal

Replace the `/expenses/add` stub in `app.py` with a working `GET`/`POST` route that lets a logged-in user create an `expenses` row, scoped to `session["user_id"]`, and redirects to `/profile`. Implement a `create_expense()` helper in `database/db.py` and a new `templates/add_expense.html` form.

---

## Architecture Summary

- **Route** (`app.py`): `add_expense()` is upgraded from a stub to a `methods=["GET", "POST"]` view with the same `/login` guard pattern as `profile()`. Reads form, validates, calls `create_expense()`, redirects on success or re-renders with an error and re-populated form values on failure.
- **Helper** (`database/db.py`): new `create_expense(user_id, amount, category, date, description)` performs a single parameterized `INSERT` and returns `cursor.lastrowid`. No validation logic.
- **Template** (`templates/add_expense.html`, new): `auth-card`-styled form extending `base.html`. Fields: amount (number), category (select from `CATEGORIES`), date (date, default today), description (text, optional). Submits to `url_for('add_expense')`; "Cancel" link to `url_for('profile')`.
- **No CSS changes** — the existing `.form-group`, `.form-input`, `.auth-card`, `.auth-error`, `.btn-submit`, `.auth-switch` classes in `static/css/style.css` cover the visual needs. No new hex values, no new variables.

---

## Files to Touch

| File | Change |
| --- | --- |
| `app.py` | Import `CATEGORIES` and `create_expense` from `database.db`. Replace `add_expense()` stub with the `GET`/`POST` view. |
| `database/db.py` | Add `create_expense()` helper (single parameterized `INSERT`, commit, return `lastrowid`). |
| `templates/add_expense.html` | **New file** — extends `base.html`, renders the form, error block, and Cancel link. |

No other files change. `base.html`, `profile.html`, `static/css/style.css`, `static/js/main.js`, `requirements.txt` stay untouched.

---

## Step-by-Step Implementation

### Step 1 — Add `create_expense()` to `database/db.py`

Append after `verify_user()` (around line 156, after the auth helpers and before the `_format_amount` / display helpers section). The function:

- Opens a connection via `get_db()`.
- Runs `INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)` with a tuple of the five arguments — five `?` placeholders, no f-strings.
- Calls `conn.commit()`, captures `cursor.lastrowid`, closes the connection, returns the id.
- Performs no validation — that lives in the route, so the helper is reusable for Step 8 (edit).

```python
def create_expense(user_id, amount, category, date, description):
    """Insert a new expense row and return its new id."""
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date, description),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id
```

### Step 2 — Wire up `app.py`

**Imports** — extend the existing import from `database.db` to add `CATEGORIES` and `create_expense`:

```python
from database.db import (
    get_db,
    init_db,
    seed_db,
    get_user_by_email,
    create_user,
    verify_user,
    get_user_by_id,
    get_recent_transactions,
    get_profile_stats,
    get_category_breakdown,
    resolve_date_range,
    VALID_RANGES,
    CATEGORIES,        # new
    create_expense,    # new
)
```

**Replace the stub** at lines 175–177. The new view:

1. **Guard first** — `if not session.get("user_id"): return redirect(url_for("login"))`. (Mirrors the `profile()` guard; do this before any other work so a logged-out user never sees the form.)
2. **GET branch** — render `add_expense.html` with `categories=CATEGORIES`, today's date as `today`, and `form={}` (no previously-submitted values).
3. **POST branch** — read form fields with `.get()` and `.strip()` where noted, validate, then either:
   - On any failure: re-render `add_expense.html` with `error=<message>`, `categories=CATEGORIES`, `today=<YYYY-MM-DD>`, and `form=request.form` so the template can re-populate fields.
   - On success: call `create_expense(session["user_id"], amount, category, date, description)` and `return redirect(url_for("profile"))`.

**Validation rules** (server-side, in the route, in this order):

| Check | On failure |
| --- | --- |
| `amount_str = request.form.get("amount", "").strip()`; `try: amount = float(amount_str); except ValueError` | `"Please enter a valid amount greater than zero."` |
| `amount > 0` | same message |
| `category = request.form.get("category", "").strip()` not in `CATEGORIES` | `"Please choose a category."` |
| `date_str = request.form.get("date", "").strip()`; `try: datetime.strptime(date_str, "%Y-%m-%d")` | `"Please enter a valid date."` |
| `description = request.form.get("description", "").strip()` (max 200, silently truncated by `<input maxlength>`) | (no server check) |

After all four checks pass, call `create_expense(session["user_id"], amount, category, date_str, description)` and redirect.

Import note: `datetime` is already imported at the top of `app.py` (line 1), so `datetime.strptime` is available. `date.today()` requires importing `date` from `datetime` — add `from datetime import date, datetime` (replacing the existing `from datetime import datetime`).

### Step 3 — Create `templates/add_expense.html`

Modeled on `login.html` / `register.html` for visual consistency. Structure:

```jinja
{% extends "base.html" %}

{% block title %}Add expense — Spendly{% endblock %}

{% block content %}

<section class="auth-section">
    <div class="auth-container">

        <div class="auth-header">
            <h1 class="auth-title">Add an expense</h1>
            <p class="auth-subtitle">Log a new transaction to your Spendly account</p>
        </div>

        <div class="auth-card">
            {% if error %}
            <div class="auth-error">{{ error }}</div>
            {% endif %}

            <form method="POST" action="{{ url_for('add_expense') }}">
                <div class="form-group">
                    <label for="amount">Amount (₹)</label>
                    <input type="number" id="amount" name="amount"
                           class="form-input" step="0.01" min="0.01"
                           placeholder="0.00" required autofocus
                           value="{{ form.amount|default('') }}">
                </div>
                <div class="form-group">
                    <label for="category">Category</label>
                    <select id="category" name="category" class="form-input" required>
                        <option value="" disabled {% if not form.category %}selected{% endif %}>Choose a category</option>
                        {% for c in categories %}
                        <option value="{{ c }}" {% if form.category == c %}selected{% endif %}>{{ c }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="form-group">
                    <label for="date">Date</label>
                    <input type="date" id="date" name="date"
                           class="form-input" required
                           value="{{ form.date|default(today) }}">
                </div>
                <div class="form-group">
                    <label for="description">Description (optional)</label>
                    <input type="text" id="description" name="description"
                           class="form-input" maxlength="200"
                           placeholder="e.g. Lunch with team"
                           value="{{ form.description|default('') }}">
                </div>
                <button type="submit" class="btn-submit">Add expense</button>
            </form>
        </div>

        <p class="auth-switch">
            <a href="{{ url_for('profile') }}">Cancel and go back</a>
        </p>

    </div>
</section>

{% endblock %}
```

Template context contract (what `app.py` must always pass):

| Key | Type | When |
| --- | --- | --- |
| `error` | `str | None` | Always pass; `None` on GET, error string on POST failure. Template uses `{% if error %}` guard. |
| `categories` | `list[str]` | Always pass `CATEGORIES`. |
| `today` | `str` (`YYYY-MM-DD`) | Pass `date.today().strftime("%Y-%m-%d")`. Used as default for the date input when `form.date` is empty. |
| `form` | `dict | ImmutableMultiDict` | Pass `request.form` on POST failure (so re-population works); pass `{}` (or just `request.form` for an empty form, which is fine) on GET. |

### Step 4 — Manual verification

After the three edits, run `python app.py` and verify against the Definition of Done checklist in the spec:

1. `GET /expenses/add` while logged out → redirects to `/login`.
2. `GET /expenses/add` while logged in → empty form, today prefilled, category select shows "Choose a category" + 7 options.
3. Submit valid form (e.g. amount=120, category=Food, date=today, description="Lunch") → row in `expenses`, redirect to `/profile` (302), new row visible in "Recent transactions".
4. Submit with empty amount → error "Please enter a valid amount greater than zero.", no row.
5. Submit with amount=0 or amount=-5 → same error.
6. Submit with category="Hack" (devtools-injected) → error "Please choose a category.", no row.
7. Submit with date="not-a-date" → error "Please enter a valid date.", no row.
8. Register a second user, log in as them, add an expense → first user's `/profile` unchanged.
9. `grep -n "INSERT\|SELECT\|UPDATE\|DELETE" app.py` → no SQL in route layer.

---

## Test Strategy

The spec is light on test requirements (no test file is mandated in "Files to Create"), but pytest must keep passing. After implementation, run `pytest` to confirm nothing in the existing suite regresses (Steps 1–6's tests should still pass). The `spendly-test-writer` and `spendly-test-runner` subagents can be invoked after this implementation if the user wants formal coverage for Step 7, but they are not part of this plan.

---

## Risk / Edge Cases

- **`amount` round-trip on re-render** — if the user submits `"abc"`, `form.amount` is `"abc"`, which is invalid HTML inside a `<input type="number" value=...>`. The spec says re-rendering a bad `amount` is fine (just leave the field blank). Use `{{ form.amount|default('') }}` and accept that an invalid string will be ignored by the browser; the user retypes it.
- **Empty category on first render** — `form.category` is `None` on GET, which would compare as not-equal to any string, so the `disabled selected` default option wins. `{% if not form.category %}` handles this cleanly.
- **Date input browser differences** — `<input type="date">` already posts `YYYY-MM-DD` in every modern browser. No parsing/formatting logic needed in the route beyond `strptime` validation.
- **`session["user_id"]` typing** — Flask sessions are JSON, so the value is an `int`. `create_expense()` receives it as the `user_id` parameter; SQLite will store it as `INTEGER`. No conversion needed.
- **`expense_tracker.db` is gitignored** — the new row from manual verification stays in the local DB. No commit risk.

---

## Out of Scope

- No edit (Step 8) or delete (Step 9) routes.
- No changes to the date filter or profile page.
- No new CSS, no JS, no pip packages.
- No "flash" messages (the spec re-renders the form on error, not flash).
- No client-side validation; the form works with JS disabled.
