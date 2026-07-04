from flask import Flask, render_template, request, redirect, url_for, session

from database.db import (
    get_db,
    init_db,
    seed_db,
    get_user_by_email,
    create_user,
    verify_user,
)

app = Flask(__name__)
# Required for signed session cookies. Fine for local development; replace with
# a value loaded from the environment before deploying.
app.secret_key = "dev-secret-key-change-in-production"


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name:
            return render_template("register.html", error="Please enter your name.")
        if not email:
            return render_template("register.html", error="Please enter your email.")
        if len(password) < 8:
            return render_template(
                "register.html",
                error="Password must be at least 8 characters.",
            )
        if password != confirm_password:
            return render_template(
                "register.html",
                error="Passwords do not match.",
            )
        if get_user_by_email(email) is not None:
            return render_template(
                "register.html",
                error="An account with that email already exists.",
            )

        create_user(name, email, password)
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            return render_template(
                "login.html",
                error="Please enter your email and password.",
            )

        user = verify_user(email, password)
        if user is None:
            return render_template(
                "login.html",
                error="Invalid email or password.",
            )

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        return redirect(url_for("profile"))

    return render_template("login.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    # Step 4 builds the profile UI in isolation. All data below is hardcoded;
    # Step 5 will replace it with real queries via database/db.py.
    user = {
        "name": "Demo User",
        "email": "demo@spendly.com",
        "initials": "DU",
        "member_since": "January 2026",
    }

    stats = {
        "total_spent": 3949,
        "transaction_count": 8,
        "top_category": "Bills",
    }

    transactions = [
        {"date": "21 Jul 2026", "description": "Dinner out", "category": "Food", "amount": 420},
        {"date": "18 Jul 2026", "description": "Miscellaneous", "category": "Other", "amount": 150},
        {"date": "15 Jul 2026", "description": "New shoes", "category": "Shopping", "amount": 999},
        {"date": "12 Jul 2026", "description": "Movie tickets", "category": "Entertainment", "amount": 350},
        {"date": "09 Jul 2026", "description": "Pharmacy", "category": "Health", "amount": 500},
        {"date": "06 Jul 2026", "description": "Electricity bill", "category": "Bills", "amount": 1200},
        {"date": "04 Jul 2026", "description": "Auto ride", "category": "Transport", "amount": 80},
        {"date": "02 Jul 2026", "description": "Groceries", "category": "Food", "amount": 250},
    ]

    categories = [
        {"name": "Bills", "amount": 1200, "percent": 30},
        {"name": "Shopping", "amount": 999, "percent": 25},
        {"name": "Food", "amount": 670, "percent": 17},
        {"name": "Health", "amount": 500, "percent": 13},
        {"name": "Entertainment", "amount": 350, "percent": 9},
        {"name": "Other", "amount": 150, "percent": 4},
        {"name": "Transport", "amount": 80, "percent": 2},
    ]

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


# ------------------------------------------------------------------ #
# Database initialization                                             #
# ------------------------------------------------------------------ #

with app.app_context():
    init_db()
    seed_db()


if __name__ == "__main__":
    app.run(debug=True, port=5001)
