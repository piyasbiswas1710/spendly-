# Spec: Login and Logout

## Overview

This feature lets a registered user authenticate with their email and password, establishes a server-side session so the application can recognize them across requests, and lets them end that session by logging out. It builds directly on Step 2 (Registration), which already stores users with `werkzeug`-hashed passwords. Login/Logout is the gateway to every logged-in feature that follows (Profile in Step 4, expense management in Steps 7–9), so it belongs here — once a user can sign in and out, the app can start protecting and personalizing routes.

---

## Depends on

- **Step 1 — Database Setup:** `get_db()` connection helper and the `users` table.
- **Step 2 — Registration:** `create_user()` and `get_user_by_email()` in `database/db.py`, the seeded demo user (`demo@spendly.com` / `demo123`), and the existing `login.html` / `register.html` auth templates.

---

## Routes

```text
GET  /login  — Render the sign-in form                         — Public
POST /login  — Authenticate credentials, start session         — Public
GET  /logout — Clear the session and redirect to landing       — Logged-in
```

| Route     | Method | Description                                       | Access     | Current status              |
| --------- | ------ | ------------------------------------------------- | ---------- | --------------------------- |
| `/login`  | GET    | Render `login.html`                               | Public     | ✅ Implemented (render-only) |
| `/login`  | POST   | Verify email + password, set `session["user_id"]` | Public     | 🔨 To implement (Step 3)    |
| `/logout` | GET    | Clear session, redirect to landing                | Logged-in  | 🔨 Stub → implement (Step 3)|

---

## Database Changes

```text
No database changes.
```

The `users` table already has everything login needs (`email UNIQUE NOT NULL`, `password_hash TEXT NOT NULL`), verified against `database/db.py`.

**New helper function (keeps SQL/verification out of routes, matching the Step-2 convention that all DB access lives in `db.py`):**

- `verify_user(email, password)` in `database/db.py` — looks up the user via the existing `get_user_by_email(email)` query, verifies the supplied password against the stored hash using `werkzeug.security.check_password_hash`, and returns the user row on success or `None` on failure (no such email, or wrong password). Import `check_password_hash` alongside the already-present `generate_password_hash`.

---

## Templates

### Create

```text
No new templates.
```

### Modify

| Template     | Change                                                                                                                                                              |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `login.html` | Replace the hardcoded `action="/login"` with `action="{{ url_for('login') }}"`. The email/password fields and the `{% if error %}` block already match the pattern. |
| `base.html`  | Add a logged-in/logged-out conditional to the navbar: when `session.get('user_id')` is set, show **Profile** (`url_for('profile')`) and **Logout** (`url_for('logout')`); otherwise show the existing **Sign in** / **Get started** links. |

---

## Files to Change

| File                     | Purpose                                                                                                                     |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------- |
| `app.py`                 | Add `session` to the Flask import; set `app.secret_key`; add `methods=["GET", "POST"]` + POST logic to `login()`; implement `logout()`; import `verify_user`. |
| `database/db.py`         | Import `check_password_hash`; add the `verify_user(email, password)` helper.                                               |
| `templates/login.html`   | Use `url_for('login')` for the form action.                                                                                |
| `templates/base.html`    | Conditional navbar based on session state.                                                                                  |

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

`werkzeug==3.1.6` is already in `requirements.txt`; `check_password_hash` ships with it. Flask sessions are built in.

---

## Rules for Implementation

- No SQLAlchemy or ORMs.
- Parameterized SQL queries only (reuse `get_user_by_email`'s `?`-placeholder query).
- Hash and verify passwords using `werkzeug` (`generate_password_hash` / `check_password_hash`) — never compare plaintext.
- Use CSS variables; never hardcode hex color values.
- All templates must extend `base.html`.
- No SQL or business logic inside route functions — password verification lives in `database/db.py` (`verify_user`).
- Never return raw strings from routes — use `render_template()` or `redirect()`.
- Never hardcode internal URLs — use `url_for()`.
- Keep the app on **port 5001**.
- `app.secret_key` is required for `session` to work; set it before reading/writing the session.

### Login behavior

| Condition                          | Result                                                                        |
| ---------------------------------- | ----------------------------------------------------------------------------- |
| Empty email or password            | Re-render `login.html` with an `error` message; do not query the DB needlessly.|
| Email not found / wrong password   | Re-render `login.html` with a single generic `error` (e.g. "Invalid email or password.") — do not reveal which field was wrong. |
| Valid credentials                  | Set `session["user_id"]` (and `session["user_name"]`), then `redirect()` to `profile`. |

### Logout behavior

- Clear the session (`session.clear()`), then `redirect()` to the landing page (`url_for('landing')`).

---

## Definition of Done

- [ ] Visiting `GET /login` renders the sign-in form (no hardcoded URL in the form action).
- [ ] Submitting valid credentials (`demo@spendly.com` / `demo123`) logs in and redirects away from the login page.
- [ ] Submitting a wrong password or unknown email re-renders `login.html` with a generic error and does **not** log in.
- [ ] Submitting an empty email or password shows an error and does not crash.
- [ ] After logging in, the navbar shows **Profile** / **Logout** instead of **Sign in** / **Get started**.
- [ ] Visiting `GET /logout` clears the session and returns the navbar to the logged-out state.
- [ ] Passwords are never compared in plaintext — `check_password_hash` is used for verification.
- [ ] No raw strings are returned from `login` or `logout`; both use `render_template()` / `redirect()`.
- [ ] The app still starts and runs on port 5001 with no new pip packages.
- [ ] Visiting `/login` while already logged in redirects to `/profile`.
