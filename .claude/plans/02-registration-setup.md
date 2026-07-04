# Plan: Step 2 — Registration

Turn the render-only `GET /register` route into a working account-creation flow: validate input → hash password with Werkzeug → insert into `users` → redirect to `/login`. Based on `.claude/specs/02-registration.md`.

## Context (verified against the code)
- `database/db.py` already has `get_db()` (row_factory + `PRAGMA foreign_keys = ON`), `init_db()` (creates `users` with `id, name, email UNIQUE, password_hash, created_at`), `seed_db()` (seeds `demo@spendly.com`), and already imports `generate_password_hash`.
- `app.py` imports only `Flask, render_template`; `register()` is render-only GET.
- `templates/register.html` extends `base.html`, has the `{% if error %}<div class="auth-error">` block and inputs named `name`/`email`/`password`, with a **hardcoded** `action="/register"`.
- `.auth-error` CSS exists and uses `var(--danger)`/`var(--danger-light)` — no CSS work.
- No schema changes, no new templates, no new dependencies.

## 1. `database/db.py` — add two helpers (parameterized, use `get_db()`)
- `get_user_by_email(email)` → `SELECT * FROM users WHERE email = ?`, return the row or `None`.
- `create_user(name, email, password)` → `INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)` with `generate_password_hash(password)`, commit, return `cursor.lastrowid`.

## 2. `app.py` — extend `register()` to GET+POST
- Import line → `from flask import Flask, render_template, request, redirect, url_for`. (No `flash`: it needs a `secret_key`, which the spec says registration must not depend on. Errors use the existing `error` context var.)
- Import helpers: add `get_user_by_email, create_user` to the `database.db` import.
- `@app.route("/register", methods=["GET", "POST"])`: on POST, read+`.strip()` name/email and read password, validate in order, then `create_user(...)` and `redirect(url_for("login"))`; on GET, render the empty form. No SQL / no `get_db()` in `app.py`.

Validation order and messages:
| Field | Rule | Error |
|---|---|---|
| name | non-empty after strip | `Please enter your name.` |
| email | non-empty after strip | `Please enter your email.` |
| password | len ≥ 8 | `Password must be at least 8 characters.` |
| email | `get_user_by_email()` is `None` | `An account with that email already exists.` |

Any failure re-renders `register.html` with `error=` and creates no row.

## 3. `templates/register.html` — de-hardcode form action
`action="/register"` → `action="{{ url_for('register') }}"`. No other markup change.

## Guardrails
- No login/sessions/secret key/password verification (later steps). Don't touch stub routes. No new pip packages — `requirements.txt` unchanged. App stays on port 5001.

## Verification (post-implementation, delegated to a subagent per policy)
GET /register renders empty form; valid POST → 302 to /login with a new row whose `password_hash` is a Werkzeug hash (not plaintext); each blank/short/duplicate case re-renders the matching error and creates no row; no SQL in `app.py`; form action uses `url_for('register')`.
