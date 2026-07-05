"""Tests for the Step 06 "Date Filter" feature.

Written from `.claude/specs/06-date-filter.md` — NOT from reading how
app.py/database/db.py implement the feature. The spec's own contract for
this step is:

  * `GET /profile` gains optional `range` (this_month | last_month |
    last_30_days | all_time | custom, default all_time) and, for
    range=custom, `start_date`/`end_date` (YYYY-MM-DD) query params.
  * `resolve_date_range(range_key, start_date=None, end_date=None)` turns
    those into a `(start_date, end_date)` tuple of YYYY-MM-DD strings (or
    None/None for unbounded), and never crashes on bad input — malformed
    or missing custom dates fall back to all-time bounds.
  * `get_recent_transactions`, `get_profile_stats`, `get_category_breakdown`
    all accept optional `start_date`/`end_date` and apply them as an
    inclusive `date >= ?` / `date <= ?` filter, scoped to `user_id`.
  * Zero expenses in range -> stats `{"total_spent": 0, "transaction_count":
    0, "top_category": "—"}`, category breakdown `[]`.
  * The three data sources (stats / transactions / category breakdown) must
    always agree with each other for the same filter.
  * The filter is a GET form on /profile, so submitted values must be
    re-populated in the rendered page after a reload.

One explicit assumption (spec does not pin this down precisely): "Last 30
Days" is read as a trailing 30-day window ending today (i.e. `today - 29
days` through `today`, inclusive of today). Because the spec text is
ambiguous about the exact boundary, HTTP-level assertions for this preset
only check clearly-inside vs. clearly-outside dates rather than the exact
29/30-day edge, while the direct `resolve_date_range` unit test pins the
assumption down explicitly and is flagged as such.

"This Month", per the spec's Definition of Done ("shows only expenses
dated within the current calendar month"), covers the FULL calendar month
(1st through its last day) — not just "1st through today". Bounding the
end at today would wrongly exclude expenses dated later in the month,
which matters because the seeded demo dataset spreads fixed days across
the whole month regardless of what day it actually is today.
"""

from datetime import date, timedelta

import pytest

from conftest import add_expense, register_and_login
from database.db import (
    get_category_breakdown,
    get_profile_stats,
    get_recent_transactions,
    resolve_date_range,
)

TODAY = date.today()


def _fmt(d):
    return d.strftime("%Y-%m-%d")


def first_day_of_this_month():
    return TODAY.replace(day=1)


def last_day_of_this_month():
    if TODAY.month == 12:
        first_of_next_month = TODAY.replace(year=TODAY.year + 1, month=1, day=1)
    else:
        first_of_next_month = TODAY.replace(month=TODAY.month + 1, day=1)
    return first_of_next_month - timedelta(days=1)


def last_day_of_previous_month():
    return first_day_of_this_month() - timedelta(days=1)


def first_day_of_previous_month():
    return last_day_of_previous_month().replace(day=1)


def last_day_of_month_before_previous():
    return first_day_of_previous_month() - timedelta(days=1)


# --------------------------------------------------------------------------
# Section A — auth guard: /profile (with or without filter params) must
# still require login. This step does not change the login guard.
# --------------------------------------------------------------------------


class TestAuthGuard:
    def test_profile_without_login_redirects_to_login(self, client, urls):
        response = client.get(urls["profile"])
        assert response.status_code == 302, "Unauthenticated /profile should redirect, not 200"
        assert "/login" in response.headers["Location"], "Should redirect to the login page"

    @pytest.mark.parametrize(
        "query_string",
        [
            {"range": "this_month"},
            {"range": "last_month"},
            {"range": "last_30_days"},
            {"range": "all_time"},
            {"range": "custom", "start_date": "2026-01-01", "end_date": "2026-01-31"},
        ],
    )
    def test_profile_with_filter_params_without_login_redirects_to_login(
        self, client, urls, query_string
    ):
        response = client.get(urls["profile"], query_string=query_string)
        assert response.status_code == 302, "A filter query string must not bypass the login guard"
        assert "/login" in response.headers["Location"]


# --------------------------------------------------------------------------
# Section B — resolve_date_range() contract (direct unit tests).
# --------------------------------------------------------------------------


class TestResolveDateRange:
    def test_this_month_resolves_to_the_full_current_calendar_month(self):
        # Per the spec's Definition of Done, "This Month" shows everything
        # dated within the current calendar month — not just up to today.
        # Bounding the end at `today` would wrongly exclude later-in-month
        # expenses (e.g. the seeded demo data, which spreads fixed days
        # across the whole month regardless of what day it is today).
        start, end = resolve_date_range("this_month")
        assert start == _fmt(first_day_of_this_month())
        assert end == _fmt(last_day_of_this_month())

    def test_last_month_resolves_to_full_previous_calendar_month(self):
        start, end = resolve_date_range("last_month")
        assert start == _fmt(first_day_of_previous_month())
        assert end == _fmt(last_day_of_previous_month())

    def test_last_30_days_resolves_to_a_trailing_30_day_window(self):
        # Assumption (spec is ambiguous on the exact edge): 30 days total,
        # inclusive of today.
        start, end = resolve_date_range("last_30_days")
        assert end == _fmt(TODAY)
        assert start == _fmt(TODAY - timedelta(days=29))

    def test_all_time_resolves_to_unbounded(self):
        start, end = resolve_date_range("all_time")
        assert start is None
        assert end is None

    def test_custom_with_valid_dates_returns_them_unchanged(self):
        start, end = resolve_date_range("custom", "2026-01-05", "2026-01-20")
        assert (start, end) == ("2026-01-05", "2026-01-20")

    def test_custom_with_malformed_start_date_falls_back_to_all_time(self):
        start, end = resolve_date_range("custom", "not-a-date", "2026-01-20")
        assert (start, end) == (None, None)

    def test_custom_with_malformed_end_date_falls_back_to_all_time(self):
        start, end = resolve_date_range("custom", "2026-01-05", "31/12/2026")
        assert (start, end) == (None, None)

    def test_custom_with_missing_dates_falls_back_to_all_time(self):
        start, end = resolve_date_range("custom", "", "")
        assert (start, end) == (None, None)

    def test_custom_with_start_after_end_falls_back_to_all_time(self):
        start, end = resolve_date_range("custom", "2026-06-15", "2026-01-01")
        assert (start, end) == (None, None)

    def test_custom_with_start_equal_end_is_a_valid_single_day_range(self):
        start, end = resolve_date_range("custom", "2026-03-10", "2026-03-10")
        assert (start, end) == ("2026-03-10", "2026-03-10")

    def test_unrecognized_range_key_does_not_crash_and_falls_back_to_all_time(self):
        # Not explicitly pinned by the spec's happy-path list, but the spec's
        # overarching rule ("malformed input must not crash the page") and
        # its default-to-all_time behavior imply graceful fallback here too.
        start, end = resolve_date_range("not_a_real_range")
        assert (start, end) == (None, None)


# --------------------------------------------------------------------------
# Section C — the three Step 5 helpers, extended with start_date/end_date,
# tested directly against a seeded set of expenses.
# --------------------------------------------------------------------------


class TestHelpersRespectDateBounds:
    def _seed(self, user_id):
        add_expense(user_id, 100.0, "Food", "2026-01-10", "January groceries")
        add_expense(user_id, 200.0, "Transport", "2026-02-14", "February cab")
        add_expense(user_id, 300.0, "Bills", "2026-02-20", "February electricity")
        add_expense(user_id, 400.0, "Shopping", "2026-03-01", "March shoes")

    def test_recent_transactions_stats_and_breakdown_filter_consistently(self, client):
        user_id = register_and_login(client)
        self._seed(user_id)

        # Range covering only the two February expenses (inclusive bounds).
        start_date, end_date = "2026-02-14", "2026-02-20"

        transactions = get_recent_transactions(
            user_id, start_date=start_date, end_date=end_date
        )
        stats = get_profile_stats(user_id, start_date=start_date, end_date=end_date)
        breakdown = get_category_breakdown(
            user_id, start_date=start_date, end_date=end_date
        )

        assert len(transactions) == 2, "Only the two February expenses fall in range"
        assert {t["description"] for t in transactions} == {
            "February cab",
            "February electricity",
        }
        assert "January groceries" not in [t["description"] for t in transactions]
        assert "March shoes" not in [t["description"] for t in transactions]

        assert stats["transaction_count"] == 2
        assert float(stats["total_spent"]) == pytest.approx(500.0)

        assert {c["name"] for c in breakdown} == {"Transport", "Bills"}
        breakdown_total = sum(float(c["amount"]) for c in breakdown)
        assert breakdown_total == pytest.approx(float(stats["total_spent"])), (
            "Category breakdown total must agree with the stats total for the same filter"
        )
        assert sum(c["percent"] for c in breakdown) in (99, 100, 101), (
            "Rounded percentages should sum close to 100"
        )

    def test_boundary_dates_are_included_inclusive_range(self, client):
        user_id = register_and_login(client)
        self._seed(user_id)

        # start_date == the date of an expense, end_date == the date of
        # another expense: both boundary expenses must be included.
        transactions = get_recent_transactions(
            user_id, start_date="2026-01-10", end_date="2026-02-14"
        )
        descriptions = {t["description"] for t in transactions}
        assert "January groceries" in descriptions, "start_date boundary must be inclusive"
        assert "February cab" in descriptions, "end_date boundary must be inclusive"
        assert "February electricity" not in descriptions
        assert "March shoes" not in descriptions

    def test_no_bounds_returns_everything_for_the_user(self, client):
        user_id = register_and_login(client)
        self._seed(user_id)

        transactions = get_recent_transactions(user_id)
        stats = get_profile_stats(user_id)
        breakdown = get_category_breakdown(user_id)

        assert len(transactions) == 4
        assert stats["transaction_count"] == 4
        assert float(stats["total_spent"]) == pytest.approx(1000.0)
        assert len(breakdown) == 4

    def test_zero_expenses_in_range_returns_documented_defaults(self, client):
        user_id = register_and_login(client)
        self._seed(user_id)

        # A range with no matching expenses at all.
        stats = get_profile_stats(user_id, start_date="2030-01-01", end_date="2030-01-31")
        transactions = get_recent_transactions(
            user_id, start_date="2030-01-01", end_date="2030-01-31"
        )
        breakdown = get_category_breakdown(
            user_id, start_date="2030-01-01", end_date="2030-01-31"
        )

        assert stats == {
            "total_spent": 0,
            "transaction_count": 0,
            "top_category": "—",
        }
        assert transactions == []
        assert breakdown == []

    def test_filter_is_scoped_to_the_logged_in_user_only(self, client):
        user_a = register_and_login(client, email="a@example.com")
        add_expense(user_a, 50.0, "Food", "2026-04-01", "User A lunch")

        # A second, independent user with an overlapping date range.
        other_client = client.application.test_client()
        user_b = register_and_login(other_client, email="b@example.com")
        add_expense(user_b, 999.0, "Shopping", "2026-04-01", "User B splurge")

        transactions = get_recent_transactions(
            user_a, start_date="2026-04-01", end_date="2026-04-01"
        )
        assert len(transactions) == 1
        assert transactions[0]["description"] == "User A lunch"

        stats = get_profile_stats(user_a, start_date="2026-04-01", end_date="2026-04-01")
        assert float(stats["total_spent"]) == pytest.approx(50.0)


# --------------------------------------------------------------------------
# Section D — GET /profile end-to-end behavior via the Flask test client.
# --------------------------------------------------------------------------


class TestProfileRouteHappyPaths:
    def test_no_query_params_shows_all_time_data(self, client, urls):
        user_id = register_and_login(client)
        add_expense(user_id, 111.11, "Food", "2020-01-01", "Ancient expense")
        add_expense(user_id, 222.22, "Bills", _fmt(TODAY), "Recent expense")

        response = client.get(urls["profile"])
        assert response.status_code == 200
        body = response.data.decode()
        assert "111.11" in body, "All-time (default) view must include very old expenses"
        assert "222.22" in body

    def test_all_time_explicit_param_matches_default(self, client, urls):
        user_id = register_and_login(client)
        add_expense(user_id, 75.5, "Food", "2019-05-05", "Old one")

        default_response = client.get(urls["profile"])
        explicit_response = client.get(urls["profile"], query_string={"range": "all_time"})

        assert default_response.status_code == 200
        assert explicit_response.status_code == 200
        assert b"75.50" in default_response.data
        assert b"75.50" in explicit_response.data

    def test_this_month_shows_only_current_month_expenses(self, client, urls):
        user_id = register_and_login(client)
        add_expense(user_id, 55.0, "Food", _fmt(TODAY), "This month lunch")
        add_expense(
            user_id, 88.0, "Bills", _fmt(last_day_of_previous_month()), "Last month bill"
        )

        response = client.get(urls["profile"], query_string={"range": "this_month"})
        body = response.data.decode()

        assert response.status_code == 200
        assert "55.00" in body
        assert "88.00" not in body

    def test_this_month_includes_expenses_later_in_the_month_than_today(
        self, client, urls
    ):
        # Regression guard: "This Month" must show the WHOLE calendar month,
        # including dates after today — not stop at today. A demo dataset
        # with expenses spread across fixed days of the month (some of which
        # fall after "today") must still show all of them under this filter.
        user_id = register_and_login(client)
        add_expense(user_id, 55.0, "Food", _fmt(TODAY), "Today's lunch")
        add_expense(
            user_id, 66.0, "Shopping", _fmt(last_day_of_this_month()), "End of month buy"
        )

        response = client.get(urls["profile"], query_string={"range": "this_month"})
        body = response.data.decode()

        assert response.status_code == 200
        assert "55.00" in body
        assert "66.00" in body, "Expenses later in the current month must not be excluded"

    def test_last_month_shows_only_previous_calendar_month_expenses(self, client, urls):
        user_id = register_and_login(client)
        add_expense(
            user_id, 66.0, "Bills", _fmt(first_day_of_previous_month()), "Prev month bill"
        )
        add_expense(user_id, 33.0, "Food", _fmt(TODAY), "This month lunch")
        add_expense(
            user_id,
            22.0,
            "Other",
            _fmt(last_day_of_month_before_previous()),
            "Two months ago",
        )

        response = client.get(urls["profile"], query_string={"range": "last_month"})
        body = response.data.decode()

        assert response.status_code == 200
        assert "66.00" in body
        assert "33.00" not in body
        assert "22.00" not in body

    def test_last_30_days_includes_recent_and_excludes_old_expenses(self, client, urls):
        user_id = register_and_login(client)
        add_expense(
            user_id, 44.0, "Food", _fmt(TODAY - timedelta(days=10)), "Ten days ago"
        )
        add_expense(
            user_id, 77.0, "Bills", _fmt(TODAY - timedelta(days=90)), "Ninety days ago"
        )

        response = client.get(urls["profile"], query_string={"range": "last_30_days"})
        body = response.data.decode()

        assert response.status_code == 200
        assert "44.00" in body
        assert "77.00" not in body

    def test_custom_range_includes_only_inclusive_bounds(self, client, urls):
        user_id = register_and_login(client)
        add_expense(user_id, 10.0, "Food", "2026-02-09", "Day before start")
        add_expense(user_id, 20.0, "Food", "2026-02-10", "On start boundary")
        add_expense(user_id, 30.0, "Food", "2026-02-15", "Middle of range")
        add_expense(user_id, 40.0, "Food", "2026-02-20", "On end boundary")
        add_expense(user_id, 50.0, "Food", "2026-02-21", "Day after end")

        response = client.get(
            urls["profile"],
            query_string={
                "range": "custom",
                "start_date": "2026-02-10",
                "end_date": "2026-02-20",
            },
        )
        body = response.data.decode()

        assert response.status_code == 200
        assert "10.00" not in body
        assert "20.00" in body
        assert "30.00" in body
        assert "40.00" in body
        assert "50.00" not in body


class TestProfileRouteValidationAndEdgeCases:
    def test_malformed_custom_dates_do_not_crash_and_fall_back_to_all_time(
        self, client, urls
    ):
        user_id = register_and_login(client)
        add_expense(user_id, 12.34, "Food", "2015-06-15", "Very old expense")

        response = client.get(
            urls["profile"],
            query_string={
                "range": "custom",
                "start_date": "not-a-date",
                "end_date": "also-not-a-date",
            },
        )
        assert response.status_code == 200, "Malformed custom dates must not crash the page"
        assert "12.34" in response.data.decode(), "Should fall back to all-time data"

    def test_missing_custom_dates_do_not_crash_and_fall_back_to_all_time(
        self, client, urls
    ):
        user_id = register_and_login(client)
        add_expense(user_id, 99.99, "Food", "2018-01-01", "Old expense")

        response = client.get(urls["profile"], query_string={"range": "custom"})
        assert response.status_code == 200
        assert "99.99" in response.data.decode()

    def test_start_after_end_falls_back_to_all_time(self, client, urls):
        user_id = register_and_login(client)
        add_expense(user_id, 44.44, "Food", "2017-03-03", "Old expense")

        response = client.get(
            urls["profile"],
            query_string={
                "range": "custom",
                "start_date": "2026-06-01",
                "end_date": "2026-01-01",
            },
        )
        assert response.status_code == 200
        assert "44.44" in response.data.decode(), "start > end should fall back to all-time"

    def test_unrecognized_range_value_does_not_crash(self, client, urls):
        user_id = register_and_login(client)
        add_expense(user_id, 66.66, "Food", "2016-07-07", "Old expense")

        response = client.get(urls["profile"], query_string={"range": "banana"})
        assert response.status_code == 200, "An unknown range value must not crash the page"
        assert "66.66" in response.data.decode()

    def test_empty_result_set_renders_gracefully(self, client, urls):
        user_id = register_and_login(client)
        add_expense(user_id, 10.0, "Food", "2026-01-01", "Not in range")

        response = client.get(
            urls["profile"],
            query_string={
                "range": "custom",
                "start_date": "2030-01-01",
                "end_date": "2030-01-31",
            },
        )
        body = response.data.decode()

        assert response.status_code == 200
        assert "Not in range" not in body
        assert "—" in body, "Top category should render as the em-dash placeholder"
        # The out-of-range expense's amount must not leak into the totals.
        assert "10.00" not in body

    def test_empty_result_set_shows_an_explicit_empty_state_message(self, client, urls):
        # An empty range must not "silently" render a blank table — the page
        # should tell the user there's nothing to show for this filter.
        user_id = register_and_login(client)
        add_expense(user_id, 10.0, "Food", "2026-01-01", "Not in range")

        response = client.get(
            urls["profile"],
            query_string={
                "range": "custom",
                "start_date": "2030-01-01",
                "end_date": "2030-01-31",
            },
        )
        body = response.data.decode()

        assert response.status_code == 200
        assert "no transactions" in body.lower() or "no expenses" in body.lower(), (
            "An empty range should render a visible empty-state message"
        )


class TestProfileFormRepopulation:
    def test_custom_filter_values_are_repopulated_on_reload(self, client, urls):
        user_id = register_and_login(client)
        add_expense(user_id, 15.0, "Food", "2026-05-05", "Mid-range expense")

        response = client.get(
            urls["profile"],
            query_string={
                "range": "custom",
                "start_date": "2026-05-01",
                "end_date": "2026-05-31",
            },
        )
        body = response.data.decode()

        assert response.status_code == 200
        assert 'value="2026-05-01"' in body, "start_date should be re-populated into the form"
        assert 'value="2026-05-31"' in body, "end_date should be re-populated into the form"
        assert "custom" in body and "selected" in body, (
            "The custom option should be marked as the active selection"
        )

    def test_preset_range_is_repopulated_on_reload(self, client, urls):
        user_id = register_and_login(client)
        add_expense(user_id, 15.0, "Food", _fmt(TODAY), "Some expense")

        response = client.get(urls["profile"], query_string={"range": "this_month"})
        body = response.data.decode()

        assert response.status_code == 200
        assert "this_month" in body and "selected" in body

    def test_preset_selection_syncs_the_from_to_inputs_to_resolved_bounds(
        self, client, urls
    ):
        # The From/To inputs must stay in sync with whatever range is
        # actually applied — not just for "custom" but also when a preset
        # is active, so a user switching to "Custom" sees where they're
        # starting from instead of blank fields.
        user_id = register_and_login(client)
        add_expense(user_id, 15.0, "Food", _fmt(TODAY), "Some expense")

        response = client.get(urls["profile"], query_string={"range": "this_month"})
        body = response.data.decode()

        assert response.status_code == 200
        assert f'value="{_fmt(first_day_of_this_month())}"' in body
        assert f'value="{_fmt(last_day_of_this_month())}"' in body
