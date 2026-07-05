"""Tests for the Step 08 "Edit Expense" feature.

Written from `.claude/specs/08-edit-expense.md` — NOT from reading how
app.py/database/db.py implement the feature. The spec's own contract for
this step is:

  * `GET /expenses/<id>/edit` and `POST /expenses/<id>/edit` both require
    `session["user_id"]` (same guard as `/profile` / `/expenses/add`); an
    unauthenticated request redirects to `/login` *before* any ownership
    check or DB read happens, so a logged-out visitor cannot use this route
    to learn whether a given id even exists.
  * Ownership is enforced in SQL, not Python: the expense must be loaded
    (and updated) with `WHERE id = ? AND user_id = ?` in a single query.
    A missing id and an id owned by a different user must be
    indistinguishable to the caller — both surface as HTTP 404
    (`abort(404)`), for both `GET` and `POST`.
  * `GET` pre-populates the form from the loaded row's `amount`, `category`,
    `date`, and `description`.
  * `POST` validation is identical to Step 7 (`add_expense`): `amount` must
    parse as a positive `float`, `category` must be one of `CATEGORIES`,
    `date` must parse as `YYYY-MM-DD`. On failure, the route re-renders the
    form with the matching error string and re-populates fields from the
    *submitted* `request.form`, not the original DB row, and performs no
    `UPDATE`.
  * On success, only `amount`, `category`, `date`, `description` change;
    `id`, `user_id`, and `created_at` are left untouched. The response is a
    302 redirect to `/profile`.
  * `database.db.get_expense_by_id(expense_id, user_id)` and
    `database.db.update_expense(expense_id, user_id, amount, category,
    date, description)` are the only DB entry points this feature adds;
    both take an ownership-scoped `WHERE id = ? AND user_id = ?` and are
    exercised directly (unit-style) in addition to through the route.

Assumptions made where the spec does not pin down an exact detail:

  * The spec does not specify the exact string format used to pre-populate
    the `amount` `<input value=...>` on `GET` (unlike the profile page's
    display values, which are explicitly formatted to two decimals). Tests
    that check amount pre-population therefore seed values whose `str()`
    form is unambiguous (e.g. `123.45`) rather than asserting a specific
    number of decimal places.
  * `add_expense()` (the conftest seeding helper) inserts directly via SQL
    and does not return the new row's id, so a small local helper
    (`_latest_expense_id`) looks the id up afterwards with a parameterized
    `SELECT ... ORDER BY id DESC LIMIT 1` query, mirroring the
    parameterized-SQL style used everywhere else in the test suite.
"""

import pytest
from flask import url_for

import database.db as db_module
from conftest import add_expense, register_and_login
from database.db import get_expense_by_id, update_expense


# --------------------------------------------------------------------------
# Local helpers
# --------------------------------------------------------------------------


def _latest_expense_id(user_id):
    """Look up the id of the most recently inserted expense for this user."""
    conn = db_module.get_db()
    row = conn.execute(
        "SELECT id FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    conn.close()
    return row["id"]


def _edit_url(app, expense_id):
    """Build the edit-expense URL via url_for (never hardcoded)."""
    with app.test_request_context():
        return url_for("edit_expense", id=expense_id)


# --------------------------------------------------------------------------
# Section A — auth guard: both verbs require a logged-in session, and the
# guard must run before any ownership check (so a logged-out visitor can't
# distinguish "no such id" from "not logged in").
# --------------------------------------------------------------------------


class TestAuthGuard:
    def test_get_while_logged_out_redirects_to_login(self, client, app):
        user_id = register_and_login(client)
        add_expense(user_id, 50.0, "Food", "2026-01-01", "Lunch")
        expense_id = _latest_expense_id(user_id)
        client.get("/logout")

        response = client.get(_edit_url(app, expense_id))
        assert response.status_code == 302, "Unauthenticated GET must redirect, not 200"
        assert "/login" in response.headers["Location"]

    def test_get_while_logged_out_for_nonexistent_id_still_redirects_not_404(
        self, client, app
    ):
        response = client.get(_edit_url(app, 999999))
        assert response.status_code == 302, (
            "The login guard must run before the ownership/existence check, "
            "so a logged-out request never resolves to a 404"
        )
        assert "/login" in response.headers["Location"]

    def test_post_while_logged_out_redirects_to_login_and_does_not_update(
        self, client, app
    ):
        user_id = register_and_login(client)
        add_expense(user_id, 50.0, "Food", "2026-01-01", "Lunch")
        expense_id = _latest_expense_id(user_id)
        client.get("/logout")

        response = client.post(
            _edit_url(app, expense_id),
            data={
                "amount": "999.99",
                "category": "Bills",
                "date": "2026-02-02",
                "description": "Hacked",
            },
        )

        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

        row = get_expense_by_id(expense_id, user_id)
        assert float(row["amount"]) == 50.0, "Logged-out POST must not update the row"
        assert row["category"] == "Food"

    def test_post_while_logged_out_for_nonexistent_id_still_redirects_not_404(
        self, client, app
    ):
        response = client.post(
            _edit_url(app, 999999),
            data={
                "amount": "1.00",
                "category": "Food",
                "date": "2026-01-01",
                "description": "x",
            },
        )
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


# --------------------------------------------------------------------------
# Section B — GET pre-population happy path.
# --------------------------------------------------------------------------


class TestGetPrepopulation:
    def test_get_renders_form_prepopulated_with_current_values(self, client, app):
        user_id = register_and_login(client)
        add_expense(user_id, 123.45, "Transport", "2026-03-15", "Cab to airport")
        expense_id = _latest_expense_id(user_id)

        response = client.get(_edit_url(app, expense_id))
        body = response.data.decode()

        assert response.status_code == 200
        assert f"#{expense_id}" in body, "Should show the expense id for context"
        assert "123.45" in body, "Amount should be pre-populated"
        assert "2026-03-15" in body, "Date should be pre-populated"
        assert "Cab to airport" in body, "Description should be pre-populated"
        assert "Transport" in body, "Category should be pre-populated"

    def test_get_marks_the_current_category_as_the_selected_option(self, client, app):
        user_id = register_and_login(client)
        add_expense(user_id, 10.0, "Health", "2026-01-01", "Meds")
        expense_id = _latest_expense_id(user_id)

        response = client.get(_edit_url(app, expense_id))
        body = response.data.decode()

        assert response.status_code == 200
        assert 'value="Health"' in body
        assert "selected" in body, "The current category's <option> must be marked selected"

    def test_get_prepopulates_empty_description_as_empty_string(self, client, app):
        user_id = register_and_login(client)
        add_expense(user_id, 15.0, "Other", "2026-01-01", "")
        expense_id = _latest_expense_id(user_id)

        response = client.get(_edit_url(app, expense_id))
        assert response.status_code == 200, "An empty description must not break the form"


# --------------------------------------------------------------------------
# Section C — GET ownership / 404 behavior.
# --------------------------------------------------------------------------


class TestGetOwnershipAnd404:
    def test_get_nonexistent_id_returns_404(self, client, app):
        register_and_login(client)
        response = client.get(_edit_url(app, 999999))
        assert response.status_code == 404

    def test_get_another_users_expense_returns_404(self, client, app):
        register_and_login(client, email="a@example.com")

        other_client = client.application.test_client()
        user_b = register_and_login(other_client, email="b@example.com")
        add_expense(user_b, 77.0, "Shopping", "2026-04-01", "User B's purchase")
        expense_id = _latest_expense_id(user_b)

        # `client` is still logged in as user A.
        response = client.get(_edit_url(app, expense_id))
        assert response.status_code == 404, (
            "A different user's expense id must 404, not render the form"
        )
        assert b"User B's purchase" not in response.data


# --------------------------------------------------------------------------
# Section D — POST happy path: update + redirect + DB side effects.
# --------------------------------------------------------------------------


class TestPostHappyPath:
    def test_post_valid_data_updates_row_and_redirects_to_profile(
        self, client, app, urls
    ):
        user_id = register_and_login(client)
        add_expense(user_id, 100.0, "Food", "2026-01-01", "Original desc")
        expense_id = _latest_expense_id(user_id)
        original = get_expense_by_id(expense_id, user_id)

        response = client.post(
            _edit_url(app, expense_id),
            data={
                "amount": "250.75",
                "category": "Bills",
                "date": "2026-02-10",
                "description": "Updated desc",
            },
        )

        assert response.status_code == 302
        assert urls["profile"] in response.headers["Location"]

        updated = get_expense_by_id(expense_id, user_id)
        assert float(updated["amount"]) == pytest.approx(250.75)
        assert updated["category"] == "Bills"
        assert updated["date"] == "2026-02-10"
        assert updated["description"] == "Updated desc"

        # id, user_id, and created_at must never change.
        assert updated["id"] == original["id"]
        assert updated["user_id"] == original["user_id"]
        assert updated["created_at"] == original["created_at"]

    def test_successful_edit_appears_on_profile_page(self, client, app, urls):
        user_id = register_and_login(client)
        add_expense(user_id, 100.0, "Food", "2026-01-01", "Original desc")
        expense_id = _latest_expense_id(user_id)

        client.post(
            _edit_url(app, expense_id),
            data={
                "amount": "42.00",
                "category": "Entertainment",
                "date": "2026-01-01",
                "description": "Movie night",
            },
        )

        response = client.get(urls["profile"])
        body = response.data.decode()

        assert response.status_code == 200
        assert "Movie night" in body
        assert "42.00" in body

    def test_description_is_trimmed_of_surrounding_whitespace(self, client, app):
        user_id = register_and_login(client)
        add_expense(user_id, 10.0, "Food", "2026-01-01", "orig")
        expense_id = _latest_expense_id(user_id)

        client.post(
            _edit_url(app, expense_id),
            data={
                "amount": "10.00",
                "category": "Food",
                "date": "2026-01-01",
                "description": "   padded description   ",
            },
        )

        updated = get_expense_by_id(expense_id, user_id)
        assert updated["description"] == "padded description"

    def test_empty_description_is_allowed_and_stored_as_empty_string(
        self, client, app
    ):
        user_id = register_and_login(client)
        add_expense(user_id, 10.0, "Food", "2026-01-01", "orig")
        expense_id = _latest_expense_id(user_id)

        response = client.post(
            _edit_url(app, expense_id),
            data={
                "amount": "10.00",
                "category": "Food",
                "date": "2026-01-01",
                "description": "",
            },
        )

        assert response.status_code == 302
        updated = get_expense_by_id(expense_id, user_id)
        assert updated["description"] == "", "Empty description must be '' not NULL"


# --------------------------------------------------------------------------
# Section E — POST validation failures: correct error text, no UPDATE, and
# fields re-populated from the submitted values (not the original row).
# --------------------------------------------------------------------------


class TestPostValidation:
    @pytest.mark.parametrize("bad_amount", ["", "not-a-number", "0", "-5", "-0.01"])
    def test_invalid_amount_rerenders_with_error_and_does_not_update(
        self, client, app, bad_amount
    ):
        user_id = register_and_login(client)
        add_expense(user_id, 100.0, "Food", "2026-01-01", "Original")
        expense_id = _latest_expense_id(user_id)

        response = client.post(
            _edit_url(app, expense_id),
            data={
                "amount": bad_amount,
                "category": "Food",
                "date": "2026-01-01",
                "description": "Original",
            },
        )

        assert response.status_code == 200
        assert (
            "Please enter a valid amount greater than zero." in response.data.decode()
        )

        unchanged = get_expense_by_id(expense_id, user_id)
        assert float(unchanged["amount"]) == 100.0, "No UPDATE should occur on failure"

    def test_invalid_category_rerenders_with_error_and_does_not_update(
        self, client, app
    ):
        user_id = register_and_login(client)
        add_expense(user_id, 100.0, "Food", "2026-01-01", "Original")
        expense_id = _latest_expense_id(user_id)

        response = client.post(
            _edit_url(app, expense_id),
            data={
                "amount": "50.00",
                "category": "NotARealCategory",
                "date": "2026-01-01",
                "description": "Original",
            },
        )

        assert response.status_code == 200
        assert "Please choose a category." in response.data.decode()

        unchanged = get_expense_by_id(expense_id, user_id)
        assert unchanged["category"] == "Food"
        assert float(unchanged["amount"]) == 100.0

    @pytest.mark.parametrize(
        "bad_date", ["", "not-a-date", "31/12/2026", "2026-13-40"]
    )
    def test_invalid_date_rerenders_with_error_and_does_not_update(
        self, client, app, bad_date
    ):
        user_id = register_and_login(client)
        add_expense(user_id, 100.0, "Food", "2026-01-01", "Original")
        expense_id = _latest_expense_id(user_id)

        response = client.post(
            _edit_url(app, expense_id),
            data={
                "amount": "50.00",
                "category": "Food",
                "date": bad_date,
                "description": "Original",
            },
        )

        assert response.status_code == 200
        assert "Please enter a valid date." in response.data.decode()

        unchanged = get_expense_by_id(expense_id, user_id)
        assert unchanged["date"] == "2026-01-01"

    def test_validation_failure_repopulates_submitted_values_not_original(
        self, client, app
    ):
        user_id = register_and_login(client)
        add_expense(user_id, 100.0, "Food", "2026-01-01", "Original desc")
        expense_id = _latest_expense_id(user_id)

        response = client.post(
            _edit_url(app, expense_id),
            data={
                "amount": "not-a-number",
                "category": "Bills",
                "date": "2026-05-05",
                "description": "New submitted desc",
            },
        )
        body = response.data.decode()

        assert response.status_code == 200
        assert 'value="Bills"' in body and "selected" in body, (
            "The submitted category (Bills), not the original (Food), must be selected"
        )
        assert "2026-05-05" in body, "The submitted date must be re-populated"
        assert "New submitted desc" in body, (
            "The submitted description must be re-populated"
        )

        # The underlying row itself must remain completely untouched.
        unchanged = get_expense_by_id(expense_id, user_id)
        assert unchanged["category"] == "Food"
        assert unchanged["date"] == "2026-01-01"
        assert unchanged["description"] == "Original desc"


# --------------------------------------------------------------------------
# Section F — POST ownership / 404 behavior.
# --------------------------------------------------------------------------


class TestPostOwnershipAnd404:
    def test_post_nonexistent_id_returns_404_and_performs_no_update(self, client, app):
        register_and_login(client)
        response = client.post(
            _edit_url(app, 999999),
            data={
                "amount": "10.00",
                "category": "Food",
                "date": "2026-01-01",
                "description": "x",
            },
        )
        assert response.status_code == 404

    def test_post_another_users_expense_returns_404_and_does_not_update_it(
        self, client, app
    ):
        register_and_login(client, email="a@example.com")

        other_client = client.application.test_client()
        user_b = register_and_login(other_client, email="b@example.com")
        add_expense(user_b, 500.0, "Bills", "2026-01-01", "User B's bill")
        expense_id = _latest_expense_id(user_b)

        # `client` is still logged in as user A, attempting to edit B's row.
        response = client.post(
            _edit_url(app, expense_id),
            data={
                "amount": "1.00",
                "category": "Other",
                "date": "2020-01-01",
                "description": "Hacked by A",
            },
        )

        assert response.status_code == 404
        assert b"Hacked by A" not in response.data, (
            "No trace of the attempted write should leak into the response"
        )

        untouched = get_expense_by_id(expense_id, user_b)
        assert float(untouched["amount"]) == 500.0
        assert untouched["category"] == "Bills"
        assert untouched["date"] == "2026-01-01"
        assert untouched["description"] == "User B's bill"


# --------------------------------------------------------------------------
# Section G — database.db helpers, exercised directly (unit-style), per the
# spec's explicit "New helper functions" contract.
# --------------------------------------------------------------------------


class TestDatabaseHelpersDirect:
    def test_get_expense_by_id_returns_row_when_owned(self, client):
        user_id = register_and_login(client)
        add_expense(user_id, 20.0, "Food", "2026-01-01", "Snack")
        expense_id = _latest_expense_id(user_id)

        row = get_expense_by_id(expense_id, user_id)
        assert row is not None
        assert row["amount"] == 20.0
        assert row["category"] == "Food"
        assert row["date"] == "2026-01-01"
        assert row["description"] == "Snack"

    def test_get_expense_by_id_returns_none_for_nonexistent_id(self, client):
        user_id = register_and_login(client)
        assert get_expense_by_id(999999, user_id) is None

    def test_get_expense_by_id_returns_none_when_id_belongs_to_another_user(
        self, client
    ):
        user_a = register_and_login(client, email="a@example.com")

        other_client = client.application.test_client()
        user_b = register_and_login(other_client, email="b@example.com")
        add_expense(user_b, 30.0, "Food", "2026-01-01", "Not yours")
        expense_id = _latest_expense_id(user_b)

        assert get_expense_by_id(expense_id, user_a) is None, (
            "Ownership must be enforced in the query itself"
        )

    def test_update_expense_returns_1_and_updates_the_row_when_owned(self, client):
        user_id = register_and_login(client)
        add_expense(user_id, 20.0, "Food", "2026-01-01", "Snack")
        expense_id = _latest_expense_id(user_id)

        rowcount = update_expense(
            expense_id, user_id, 99.99, "Bills", "2026-02-02", "Renamed"
        )
        assert rowcount == 1

        row = get_expense_by_id(expense_id, user_id)
        assert row["amount"] == 99.99
        assert row["category"] == "Bills"
        assert row["date"] == "2026-02-02"
        assert row["description"] == "Renamed"

    def test_update_expense_does_not_touch_id_user_id_or_created_at(self, client):
        user_id = register_and_login(client)
        add_expense(user_id, 20.0, "Food", "2026-01-01", "Snack")
        expense_id = _latest_expense_id(user_id)
        original = get_expense_by_id(expense_id, user_id)

        update_expense(expense_id, user_id, 5.0, "Other", "2026-03-03", "Changed")

        updated = get_expense_by_id(expense_id, user_id)
        assert updated["id"] == original["id"]
        assert updated["user_id"] == original["user_id"]
        assert updated["created_at"] == original["created_at"]

    def test_update_expense_returns_0_for_nonexistent_id(self, client):
        user_id = register_and_login(client)
        rowcount = update_expense(999999, user_id, 1.0, "Food", "2026-01-01", "x")
        assert rowcount == 0

    def test_update_expense_returns_0_and_does_not_modify_row_when_not_owned(
        self, client
    ):
        user_a = register_and_login(client, email="a@example.com")

        other_client = client.application.test_client()
        user_b = register_and_login(other_client, email="b@example.com")
        add_expense(user_b, 30.0, "Food", "2026-01-01", "Not yours")
        expense_id = _latest_expense_id(user_b)

        rowcount = update_expense(
            expense_id, user_a, 1.0, "Other", "2020-01-01", "Hacked"
        )
        assert rowcount == 0, "Updating by the wrong user_id must affect zero rows"

        untouched = get_expense_by_id(expense_id, user_b)
        assert untouched["amount"] == 30.0
        assert untouched["category"] == "Food"
        assert untouched["description"] == "Not yours"
