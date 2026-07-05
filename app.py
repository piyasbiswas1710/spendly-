import os
from datetime import date, datetime

from flask import Flask, abort, render_template, request, redirect, url_for, session

from database.db import (
    get_db,
    get_expense_by_id,
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
    CATEGORIES,
    create_expense,
    update_expense,
    delete_expense as delete_expense_row,
)

app = Flask(__name__)
# Required for signed session cookies. Fine for local development; replace with
# a value loaded from the environment before deploying.
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")


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


def _user_initials(name):
    parts = name.split()
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0][0].upper()
    return (parts[0][0] + parts[-1][0]).upper()


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]
    db_user = get_user_by_id(user_id)

    member_since = datetime.strptime(
        db_user["created_at"], "%Y-%m-%d %H:%M:%S"
    ).strftime("%B %Y")

    user = {
        "name": db_user["name"],
        "email": db_user["email"],
        "initials": _user_initials(db_user["name"]),
        "member_since": member_since,
    }

    range_key = request.args.get("range", "all_time")
    raw_start = request.args.get("start_date", "")
    raw_end = request.args.get("end_date", "")
    start_date, end_date = resolve_date_range(range_key, raw_start, raw_end)

    stats = get_profile_stats(user_id, start_date, end_date)
    transactions = get_recent_transactions(user_id, start_date=start_date, end_date=end_date)
    categories = get_category_breakdown(user_id, start_date, end_date)

    active_range = range_key if range_key in VALID_RANGES else "all_time"
    filters = {
        "range": active_range,
        "start_date": raw_start if active_range == "custom" else (start_date or ""),
        "end_date": raw_end if active_range == "custom" else (end_date or ""),
    }

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
        filters=filters,
    )


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    today = date.today().strftime("%Y-%m-%d")
    context = {
        "error": None,
        "categories": CATEGORIES,
        "today": today,
        "form": {},
    }

    if request.method == "POST":
        form = request.form
        amount_str = form.get("amount", "").strip()
        category = form.get("category", "").strip()
        date_str = form.get("date", "").strip()
        description = form.get("description", "").strip()

        try:
            amount = float(amount_str)
        except ValueError:
            amount = None

        if amount is None or amount <= 0:
            context["error"] = "Please enter a valid amount greater than zero."
        elif category not in CATEGORIES:
            context["error"] = "Please choose a category."
        else:
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                context["error"] = "Please enter a valid date."

        if context["error"] is None:
            create_expense(
                session["user_id"], amount, category, date_str, description
            )
            return redirect(url_for("profile"))

        context["form"] = form

    return render_template("add_expense.html", **context)


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]
    expense = get_expense_by_id(id, user_id)
    if expense is None:
        abort(404)

    today = date.today().strftime("%Y-%m-%d")
    context = {
        "error": None,
        "categories": CATEGORIES,
        "today": today,
        "form": {},
        "expense": expense,
        "id": id,
    }

    if request.method == "POST":
        form = request.form
        amount_str = form.get("amount", "").strip()
        category = form.get("category", "").strip()
        date_str = form.get("date", "").strip()
        description = form.get("description", "").strip()

        try:
            amount = float(amount_str)
        except ValueError:
            amount = None

        if amount is None or amount <= 0:
            context["error"] = "Please enter a valid amount greater than zero."
        elif category not in CATEGORIES:
            context["error"] = "Please choose a category."
        else:
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                context["error"] = "Please enter a valid date."

        if context["error"] is None:
            if update_expense(id, user_id, amount, category, date_str, description) == 0:
                abort(404)
            return redirect(url_for("profile"))

        context["form"] = form

    return render_template("edit_expense.html", **context)


@app.route("/expenses/<int:id>/delete", methods=["GET", "POST"])
def delete_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]
    expense = get_expense_by_id(id, user_id)
    if expense is None:
        abort(404)

    if request.method == "POST":
        if delete_expense_row(id, user_id) == 0:
            abort(404)
        return redirect(url_for("profile"))

    return render_template("delete_expense.html", expense=expense, id=id)


# ------------------------------------------------------------------ #
# Database initialization                                             #
# ------------------------------------------------------------------ #

with app.app_context():
    init_db()
    seed_db()


if __name__ == "__main__":
    app.run(debug=True, port=5001)
