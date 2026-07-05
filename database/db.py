"""SQLite data layer for Spendly.

This is the only module that talks to the database. It exposes three
helpers used across the application:

    get_db()   — a SQLite connection with row_factory + foreign keys enabled
    init_db()  — creates the schema (CREATE TABLE IF NOT EXISTS)
    seed_db()  — inserts development fixtures once (idempotent)
"""

import os
import sqlite3
from datetime import date, datetime, timedelta

from werkzeug.security import generate_password_hash, check_password_hash

# Resolve the DB file to the project root regardless of the current working
# directory. expense_tracker.db is gitignored.
DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "expense_tracker.db"
)

# The fixed set of expense categories used throughout the application.
CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
]


def get_db():
    """Return a SQLite connection with dict-style rows and FK enforcement."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create the users and expenses tables if they do not already exist."""
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            email         TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at    TEXT DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            amount      REAL NOT NULL,
            category    TEXT NOT NULL,
            date        TEXT NOT NULL,
            description TEXT,
            created_at  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    conn.commit()
    conn.close()


def seed_db():
    """Insert a demo user and sample expenses once, if the DB is empty."""
    conn = get_db()

    # Idempotent: bail out if any user already exists.
    existing = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if existing > 0:
        conn.close()
        return

    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
    )
    user_id = cursor.lastrowid

    # Eight sample expenses spread across the current month. Every category is
    # covered at least once; Food appears twice to reach eight rows. Days are
    # fixed points across the month (all valid in every month) so the fixtures
    # stay spread out regardless of today's date.
    today = date.today()

    def day_in_month(day):
        return today.replace(day=day).strftime("%Y-%m-%d")

    expenses = [
        (user_id, 250.0, "Food", day_in_month(2), "Groceries"),
        (user_id, 80.0, "Transport", day_in_month(4), "Auto ride"),
        (user_id, 1200.0, "Bills", day_in_month(6), "Electricity bill"),
        (user_id, 500.0, "Health", day_in_month(9), "Pharmacy"),
        (user_id, 350.0, "Entertainment", day_in_month(12), "Movie tickets"),
        (user_id, 999.0, "Shopping", day_in_month(15), "New shoes"),
        (user_id, 150.0, "Other", day_in_month(18), "Miscellaneous"),
        (user_id, 420.0, "Food", day_in_month(21), "Dinner out"),
    ]

    conn.executemany(
        """
        INSERT INTO expenses (user_id, amount, category, date, description)
        VALUES (?, ?, ?, ?, ?)
        """,
        expenses,
    )
    conn.commit()
    conn.close()


def get_user_by_email(email):
    """Return the user row with this email, or None if none exists."""
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email,)
    ).fetchone()
    conn.close()
    return user


def create_user(name, email, password):
    """Hash the password, insert a new user, and return its new id."""
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, generate_password_hash(password)),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def verify_user(email, password):
    """Return the user row if the email exists and the password matches.

    Returns None when no user has that email or the password is wrong, so
    callers cannot tell the two failure cases apart.
    """
    user = get_user_by_email(email)
    if user is None:
        return None
    if not check_password_hash(user["password_hash"], password):
        return None
    return user


def create_expense(user_id, amount, category, date, description):
    """Insert a new expense row for this user and return its new id.

    Performs no validation — the route is responsible for verifying the
    inputs so this helper stays reusable for the edit flow.
    """
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


def get_expense_by_id(expense_id, user_id):
    """Return the expense row with this id owned by this user, or None.

    The ownership clause (`AND user_id = ?`) is enforced in SQL so the
    caller cannot tell the difference between "row does not exist" and
    "row exists but belongs to another user" — both surface as `None`.
    Used to (a) pre-populate the edit form on `GET` and (b) gate the
    `POST` update on a real ownership check before any write happens.
    """
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user_id),
    ).fetchone()
    conn.close()
    return row


def update_expense(expense_id, user_id, amount, category, date, description):
    """Update the editable fields of an owned expense row.

    Sets `amount`, `category`, `date`, and `description` only — `id`,
    `user_id`, and `created_at` are never touched. The ownership clause
    (`AND user_id = ?`) means the update affects at most one row, and
    the function returns `cursor.rowcount` so the caller can `abort(404)`
    on a miss. Performs no validation — that responsibility lives in the
    route, mirroring `create_expense()`.
    """
    conn = get_db()
    cursor = conn.execute(
        "UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? "
        "WHERE id = ? AND user_id = ?",
        (amount, category, date, description, expense_id, user_id),
    )
    conn.commit()
    rowcount = cursor.rowcount
    conn.close()
    return rowcount


def delete_expense(expense_id, user_id):
    """Delete an owned expense row.

    The ownership clause (`AND user_id = ?`) means the delete affects at
    most one row, and the function returns `cursor.rowcount` so the caller
    can `abort(404)` on a miss — same pattern as `update_expense()`.
    """
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user_id),
    )
    conn.commit()
    rowcount = cursor.rowcount
    conn.close()
    return rowcount


def _format_amount(value):
    """Format a monetary value to exactly two decimal places for display.

    SUM(amount) over SQLite REAL columns can accumulate float error (e.g.
    717.9300000000001); rounding to a fixed-precision string is the only way
    to guarantee the UI never shows that noise.
    """
    return f"{value:.2f}"


def get_user_by_id(user_id):
    """Return the user row with this id, or None if none exists."""
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return user


def _date_range_clause(start_date, end_date):
    """Build an optional ' AND date >= ? AND date <= ?' fragment.

    Returns (sql_fragment, params_list). Either or both bounds may be None,
    in which case that half of the clause (or the whole thing) is omitted.
    Callers append sql_fragment after a `WHERE user_id = ?` clause and
    extend their params with params_list.
    """
    fragment = ""
    params = []
    if start_date is not None:
        fragment += " AND date >= ?"
        params.append(start_date)
    if end_date is not None:
        fragment += " AND date <= ?"
        params.append(end_date)
    return fragment, params


VALID_RANGES = {"this_month", "last_month", "last_30_days", "all_time", "custom"}


def _parse_iso_date(value):
    """Return a date object if value is a valid 'YYYY-MM-DD' string, else None."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def resolve_date_range(range_key, start_date=None, end_date=None):
    """Resolve a preset/custom range key into concrete (start, end) bounds.

    Returns a (start_date, end_date) tuple of 'YYYY-MM-DD' strings, or
    (None, None) for 'all_time' and any unrecognized/invalid input. This is
    the only function that performs date-range math; callers pass the
    result straight into the query helpers below.
    """
    today = date.today()

    if range_key == "this_month":
        start = today.replace(day=1)
        if today.month == 12:
            first_of_next_month = today.replace(year=today.year + 1, month=1, day=1)
        else:
            first_of_next_month = today.replace(month=today.month + 1, day=1)
        end = first_of_next_month - timedelta(days=1)
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

    if range_key == "last_month":
        last_day_prev_month = today.replace(day=1) - timedelta(days=1)
        first_day_prev_month = last_day_prev_month.replace(day=1)
        return (
            first_day_prev_month.strftime("%Y-%m-%d"),
            last_day_prev_month.strftime("%Y-%m-%d"),
        )

    if range_key == "last_30_days":
        start = today - timedelta(days=29)
        return start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")

    if range_key == "custom":
        parsed_start = _parse_iso_date(start_date)
        parsed_end = _parse_iso_date(end_date)
        if parsed_start is None or parsed_end is None or parsed_start > parsed_end:
            return None, None
        return start_date, end_date

    return None, None


def get_recent_transactions(user_id, limit=10, start_date=None, end_date=None):
    """Return this user's most recent expenses as display-ready dicts."""
    conn = get_db()
    clause, range_params = _date_range_clause(start_date, end_date)
    rows = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ?" + clause +
        " ORDER BY date DESC, id DESC LIMIT ?",
        (user_id, *range_params, limit),
    ).fetchall()
    conn.close()

    transactions = []
    for row in rows:
        parsed = datetime.strptime(row["date"], "%Y-%m-%d")
        transactions.append(
            {
                "id": row["id"],
                "date": parsed.strftime("%d %b %Y"),
                "description": row["description"],
                "category": row["category"],
                "amount": _format_amount(row["amount"]),
            }
        )
    return transactions


def get_category_breakdown(user_id, start_date=None, end_date=None):
    """Return per-category totals and percent-of-total for this user.

    Returns [] when the user has no expenses in range.
    """
    conn = get_db()
    clause, range_params = _date_range_clause(start_date, end_date)
    rows = conn.execute(
        "SELECT category, SUM(amount) AS total FROM expenses "
        "WHERE user_id = ?" + clause +
        " GROUP BY category ORDER BY total DESC, category ASC",
        (user_id, *range_params),
    ).fetchall()
    conn.close()

    if not rows:
        return []

    grand_total = sum(row["total"] for row in rows)
    breakdown = []
    for row in rows:
        percent = round(row["total"] / grand_total * 100) if grand_total else 0
        breakdown.append(
            {
                "name": row["category"],
                "amount": _format_amount(row["total"]),
                "percent": percent,
            }
        )
    return breakdown


def get_profile_stats(user_id, start_date=None, end_date=None):
    """Return total spent, transaction count, and top category for this user.

    Returns zero-expense defaults when the user has no expenses in range.
    """
    conn = get_db()
    clause, range_params = _date_range_clause(start_date, end_date)
    row = conn.execute(
        "SELECT SUM(amount) AS total, COUNT(*) AS count FROM expenses "
        "WHERE user_id = ?" + clause,
        (user_id, *range_params),
    ).fetchone()
    conn.close()

    transaction_count = row["count"] or 0
    if transaction_count == 0:
        return {"total_spent": 0, "transaction_count": 0, "top_category": "—"}

    breakdown = get_category_breakdown(user_id, start_date, end_date)
    top_category = breakdown[0]["name"] if breakdown else "—"

    return {
        "total_spent": _format_amount(row["total"] or 0),
        "transaction_count": transaction_count,
        "top_category": top_category,
    }
