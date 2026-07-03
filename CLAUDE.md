# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Spendly** is a personal expense tracking web application built with Flask and SQLite. It is structured as a step-by-step learning project — `app.py` currently has placeholder routes for features that "students will implement" in numbered steps (1, 3, 4, 7, 8, 9).

# Tech Stack

* **Backend:** Flask 3.1.3 (Python 3.10+) — no Django, FastAPI, or other web frameworks
* **Database:** SQLite (`expense_tracker.db`) — no PostgreSQL, MySQL, SQLAlchemy ORM, or external databases
* **Frontend:** Server-rendered Jinja2 templates with HTML5, CSS3, and Vanilla JavaScript — no React, jQuery, or npm packages
* **Testing:** pytest 8.3.5, pytest-flask 1.3.0
* **Python Dependencies:** Use only the packages listed in `requirements.txt`; do not install additional pip packages unless explicitly instructed
* **Currency Convention:** Indian Rupee (₹) throughout the application
* **Version Control:** Git, with `expense_tracker.db` excluded via `.gitignore`
## Development Commands

All commands assume you are in the project root directory.

### Create and Activate the Virtual Environment

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run the Development Server

The Flask development server runs on **port 5001**.

```bash
python app.py
```

### Run All Tests

```bash
pytest
```

### Run a Specific Test File

```bash
pytest tests/test_foo.py
```

### Run a Specific Test by Name

```bash
pytest -k "test_name"
```

### Run Tests with Console Output

```bash
pytest -s
```
## Architecture

```
expense-tracker/
├── app.py                  # Flask app + all routes (currently thin)
├── database/
│   ├── __init__.py
│   └── db.py               # TODO: get_db(), init_db(), seed_db() (Step 1)
├── templates/              # Jinja2 templates — all extend base.html
│   ├── base.html           # Nav, footer, DM Serif/Sans fonts, style.css, main.js
│   ├── landing.html        # Hero, features, CTA, YouTube modal
│   ├── login.html          # POST /login form
│   ├── register.html       # POST /register form
│   ├── terms.html          # Static legal page
│   └── privacy.html        # Static legal page
├── static/
│   ├── css/style.css       # Design system: CSS vars, components, auth/hero/legal/modal
│   └── js/main.js          # YouTube modal (landing) — more JS to be added
├── requirements.txt
├── venv/                   # Local venv (gitignored)
└── .claude/settings.local.json
```


**Key architectural points:**

- **Single-file Flask app** in `app.py` — every route lives here. As features are implemented, they will continue to be added to this file (no blueprints yet).
- **SQLite is accessed via `database/db.py`** which is the *only* file that should talk to the DB. Three functions to implement: `get_db()` (connection with `row_factory` and `PRAGMA foreign_keys = ON`), `init_db()` (`CREATE TABLE IF NOT EXISTS`), `seed_db()` (dev fixtures).
- **Templates extend `base.html`** — it provides the navbar, footer (with Terms/Privacy links), the design-system CSS, and `main.js`. Pages use `{% block content %}`, `{% block head %}`, and `{% block scripts %}`.
- **Auth pages** (`login.html`, `register.html`) expect an `error` context variable to render `auth-error`. Forms POST to the same URL they were rendered from.
- **Placeholder routes** in `app.py` return plain strings with step numbers (Step 3 logout, Step 4 profile, Step 7 add expense, Step 8 edit, Step 9 delete) — these are intentional teaching placeholders, not bugs.
- **The YouTube video ID** in `static/js/main.js` (`VIDEO_ID` constant) is a placeholder — replace with the real demo video ID.

## Code Style 

- Python: PEP 8, snake_case for all variables and functions
- Templates: Jinja2 with url_for() for every internal link — never hardcode URLs
- Route functions: one responsibility only — fetch data, render template, done
- DB queries: always use parameterized queries (? placeholders) — never f-strings in SQL
- Error handling: use abort() for HTTP errors, not bare return "error string"

# Subagent Policy

* **Codebase Exploration:** Always use the built-in **Explore** subagent to examine the codebase before implementing any new feature.
* **Test Verification:** Always use a subagent to verify test results after completing any implementation.
* **Planning:** When asked to create a plan, first delegate codebase research to the **Explore** subagent before presenting the plan.
* **Plan Mode:** Always use the built-in **Plan** subagent when operating in plan mode.

# Warnings and Things to Avoid

* **Templates over Raw Strings:** Never return raw strings from routes once a feature has been implemented. Always render a Jinja2 template using `render_template()`.

* **No Hardcoded URLs:** Never hardcode internal URLs in templates. Always generate them using `url_for()`.

* **Keep Database Logic Separate:** Never place database queries or business logic inside route functions. All database operations belong in `database/db.py`.

* **Dependency Management:** Never install new Python packages during feature development without explicitly flagging the change. Keep `requirements.txt` in sync with all approved dependencies.

* **Vanilla JavaScript Only:** Do not use JavaScript frameworks or libraries such as React, Vue, Angular, or jQuery. The frontend is intentionally built with Vanilla JavaScript.

* **Do Not Assume Database Helpers Exist:** `database/db.py` is currently empty. Only use helper functions after they have been implemented as part of the corresponding development step.

* **Enable SQLite Foreign Keys:** SQLite does not enforce foreign key constraints by default. Every database connection created by `get_db()` must execute:

  ```sql
  PRAGMA foreign_keys = ON;
  ```

* **Development Server Port:** The application runs on **port 5001**. Do not change it to Flask's default port **5000**.
# Implemented vs. Stub Routes

| Route                       | Status                                      |
| --------------------------- | ------------------------------------------- |
| `GET /`                     | ✅ **Implemented** — Renders `landing.html`  |
| `GET /register`             | ✅ **Implemented** — Renders `register.html` |
| `GET /login`                | ✅ **Implemented** — Renders `login.html`    |
| `GET /logout`               | 🚧 **Stub** — Step 3                        |
| `GET /profile`              | 🚧 **Stub** — Step 4                        |
| `GET /expenses/add`         | 🚧 **Stub** — Step 7                        |
| `GET /expenses/<id>/edit`   | 🚧 **Stub** — Step 8                        |
| `GET /expenses/<id>/delete` | 🚧 **Stub** — Step 9                        |

> **Important:** Do **not** implement a stub route unless the active task explicitly targets that development step.
