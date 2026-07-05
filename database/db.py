"""SQLite data layer for Spendly.

This is the only module that talks to the database. It exposes three
helpers used across the application:

    get_db()   — a SQLite connection with row_factory + foreign keys enabled
    init_db()  — creates the schema (CREATE TABLE IF NOT EXISTS)
    seed_db()  — inserts development fixtures once (idempotent)
"""

import os
import sqlite3
from datetime import date, datetime

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


def get_recent_transactions(user_id, limit=10):
    """Return this user's most recent expenses as display-ready dicts."""
    conn = get_db()
    rows = conn.execute(
        """
        SELECT * FROM expenses
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    conn.close()

    transactions = []
    for row in rows:
        parsed = datetime.strptime(row["date"], "%Y-%m-%d")
        transactions.append(
            {
                "date": parsed.strftime("%d %b %Y"),
                "description": row["description"],
                "category": row["category"],
                "amount": _format_amount(row["amount"]),
            }
        )
    return transactions


def get_category_breakdown(user_id):
    """Return per-category totals and percent-of-total for this user.

    Returns [] when the user has no expenses.
    """
    conn = get_db()
    rows = conn.execute(
        """
        SELECT category, SUM(amount) AS total
        FROM expenses
        WHERE user_id = ?
        GROUP BY category
        ORDER BY total DESC, category ASC
        """,
        (user_id,),
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


def get_profile_stats(user_id):
    """Return total spent, transaction count, and top category for this user.

    Returns zero-expense defaults when the user has no expenses.
    """
    conn = get_db()
    row = conn.execute(
        "SELECT SUM(amount) AS total, COUNT(*) AS count FROM expenses WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()

    transaction_count = row["count"] or 0
    if transaction_count == 0:
        return {"total_spent": 0, "transaction_count": 0, "top_category": "—"}

    breakdown = get_category_breakdown(user_id)
    top_category = breakdown[0]["name"] if breakdown else "—"

    return {
        "total_spent": _format_amount(row["total"] or 0),
        "transaction_count": transaction_count,
        "top_category": top_category,
    }
