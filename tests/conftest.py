"""Shared pytest fixtures for the Spendly test suite.

Safety note on the database
----------------------------
`database/db.py` resolves a single hardcoded `DB_PATH` (project-root
`expense_tracker.db`) and `app.py` calls `init_db()` / `seed_db()` against
that path the moment it is imported. To make sure the test suite never
reads or writes the real development database, this conftest redirects
`database.db.DB_PATH` to a private temporary file *before* `app` is
imported anywhere in the test session. Because `get_db()` re-reads the
module-level `DB_PATH` on every call (rather than capturing it at import
time), patching the attribute before the first import of `app` is enough
to keep every subsequent `get_db()` call — from route code, from helper
functions, and from these fixtures — pointed at the temp file.

Each test gets a clean slate: the `app` fixture wipes the `users` and
`expenses` tables before (and after) every test, so tests never see each
other's data even though they share one temp DB file for the process.
"""

import atexit
import os
import tempfile

import pytest

import database.db as db_module

# --- Redirect DB_PATH before app.py (and its module-level init_db/seed_db
# call) is ever imported. ---------------------------------------------------
_fd, _TEST_DB_PATH = tempfile.mkstemp(prefix="spendly_test_", suffix=".db")
os.close(_fd)
db_module.DB_PATH = _TEST_DB_PATH
atexit.register(lambda: os.path.exists(_TEST_DB_PATH) and os.remove(_TEST_DB_PATH))

from app import app as flask_app  # noqa: E402  (must follow the DB_PATH patch)
from flask import url_for  # noqa: E402


def _wipe_tables():
    """Delete all rows from expenses/users (FK-safe order), keep the schema."""
    conn = db_module.get_db()
    conn.execute("DELETE FROM expenses")
    conn.execute("DELETE FROM users")
    conn.commit()
    conn.close()


@pytest.fixture
def app():
    """The real Spendly Flask app, pointed at an isolated temp SQLite file."""
    flask_app.config.update({"TESTING": True})
    _wipe_tables()
    yield flask_app
    _wipe_tables()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def urls(app):
    """A handful of resolved endpoint URLs, computed via url_for (never
    hardcoded), for use in assertions that need to know a route's path."""
    with app.test_request_context():
        return {
            "profile": url_for("profile"),
            "login": url_for("login"),
            "register": url_for("register"),
        }


def register_and_login(
    client,
    name="Test User",
    email="testuser@example.com",
    password="password123",
):
    """Register + log in a fresh user through the real routes.

    Returns the new user's id (looked up from the DB after registration)
    so tests can seed expenses directly for that user.
    """
    client.post(
        "/register",
        data={
            "name": name,
            "email": email,
            "password": password,
            "confirm_password": password,
        },
    )
    client.post("/login", data={"email": email, "password": password})
    user = db_module.get_user_by_email(email)
    assert user is not None, "Fixture setup failed: /register did not create the user"
    return user["id"]


def add_expense(user_id, amount, category, date_str, description="Test expense"):
    """Insert an expense row directly.

    There is no "Add Expense" route yet (Step 7 is still a stub per
    CLAUDE.md), so seeding test data for the date-filter feature has to go
    straight through the DB layer, using the same parameterized-SQL style
    as the rest of `database/db.py`.
    """
    conn = db_module.get_db()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date_str, description),
    )
    conn.commit()
    conn.close()
