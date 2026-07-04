# Plan: Step 3 — Login and Logout

Turn the render-only `GET /login` and the `GET /logout` stub into a working session-based auth flow: verify email+password with Werkzeug → store `user_id` in the Flask session → let the user log out → reflect auth state in the navbar. Based on `.claude/specs/03-login-logout.md`.

## Context (verified against the code)
- `database/db.py` already has `get_db()` (row_factory + `PRAGMA foreign_keys = ON`), the `users` table (`id, name, email UNIQUE, password_hash, created_at`), `get_user_by_email()` (returns the full row incl. `password_hash`), and `create_user()`. It imports `generate_password_hash` **but not** `check_password_hash`.
- `app.py` imports `Flask, render_template, request, redirect, url_for` — **no `session`, no `app.secret_key`**. `login()` is render-only GET; `logout()` returns the raw string `"Logout — coming in Step 3"`.
- `templates/login.html` extends `base.html`, has the `{% if error %}<div class="auth-error">` block and inputs named `email`/`password`, with a **hardcoded** `action="/login"`.
- `templates/base.html` navbar always shows Sign in / Get started — no session conditional. `session` is available in Jinja automatically once `secret_key` is set.
- Seed user for testing: `demo@spendly.com` / `demo123`.
- No schema changes, no new templates, no new dependencies (Werkzeug 3.1.6 already in `requirements.txt`).

## 1. `database/db.py` — add `verify_user()` (keeps verification out of routes)
- Extend the import: `from werkzeug.security import generate_password_hash, check_password_hash`.
- `verify_user(email, password)`:
  - `user = get_user_by_email(email)` (reuses the existing parameterized query).
  - `if user is None: return None`.
  - `if not check_password_hash(user["password_hash"], password): return None`.
  - `return user`.
- No plaintext comparison; no new SQL string (delegates to `get_user_by_email`).

## 2. `app.py` — sessions + real `login()` / `logout()`
- Import line → `from flask import Flask, render_template, request, redirect, url_for, session`.
- Add `verify_user` to the `database.db` import group.
- After `app = Flask(__name__)`: `app.secret_key = "dev-secret-key-change-in-production"` (required for `session`; a fixed dev key is fine for this learning project — flag before shipping).
- `@app.route("/login", methods=["GET", "POST"])`:
  - On POST: read `email` (`.strip()`) and `password`; if either is empty → re-render `login.html` with `error="Please enter your email and password."`; else `user = verify_user(email, password)`; if `None` → re-render with a **generic** `error="Invalid email or password."`; on success set `session["user_id"] = user["id"]`, `session["user_name"] = user["name"]`, then `redirect(url_for("profile"))`.
  - On GET: `return render_template("login.html")` (unchanged).
  - No SQL / no `get_db()` in the route.
- `@app.route("/logout")` → `session.clear()` then `redirect(url_for("landing"))`. No raw string.

Login outcomes:
| Condition | Result |
|---|---|
| empty email or password | re-render with `Please enter your email and password.` |
| unknown email or wrong password | re-render with generic `Invalid email or password.` |
| valid credentials | set session, 302 → `profile` |

## 3. `templates/login.html` — de-hardcode form action
`action="/login"` → `action="{{ url_for('login') }}"`. No other markup change (fields + error block already match).

## 4. `templates/base.html` — session-aware navbar
Replace the `.nav-links` body with a conditional:
```html
<div class="nav-links">
    {% if session.get('user_id') %}
    <a href="{{ url_for('profile') }}">Profile</a>
    <a href="{{ url_for('logout') }}" class="nav-cta">Logout</a>
    {% else %}
    <a href="{{ url_for('login') }}">Sign in</a>
    <a href="{{ url_for('register') }}" class="nav-cta">Get started</a>
    {% endif %}
</div>
```
Reuses existing nav CSS classes — no CSS work, no hardcoded colors.

## Guardrails
- Don't touch other stub routes (`profile` stays a Step-4 stub — login redirecting to it will show its placeholder for now; Step 4 fills it in).
- No new pip packages — `requirements.txt` unchanged. App stays on **port 5001**. Parameterized queries only. All templates extend `base.html`.

## Verification (post-implementation, delegated to a subagent per policy)
- `GET /login` renders the form; action uses `url_for('login')`.
- POST `demo@spendly.com`/`demo123` → 302 away from login and `session["user_id"]` set; navbar then shows Profile / Logout.
- Wrong password / unknown email → re-renders `login.html` with the generic error, no session set.
- Empty email or password → error shown, no crash.
- `GET /logout` → session cleared, navbar back to Sign in / Get started.
- No SQL in `app.py`; `verify_user` uses `check_password_hash`; no plaintext comparison anywhere.
