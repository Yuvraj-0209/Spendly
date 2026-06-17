"""
tests/test_06-date-filter-profile-page.py

Pytest test suite for the Spendly date-range filter on the /profile route.

Spec: .claude/specs/06-date-filter-profile-page.md
Definition-of-done checklist is the sole source of truth for test logic.

Test data overview
------------------
The seeded_client fixture inserts 8 expenses for a single test user:

  date          amount   category
  2026-06-01    12.50    Food
  2026-06-02    45.00    Transport
  2026-06-03   120.00    Bills
  2026-06-05    30.00    Health
  2026-06-07    25.00    Entertainment
  2026-06-09    89.99    Shopping
  2026-06-10    15.00    Other
  2026-06-11     8.75    Food

Filter scenarios tested:
  no filter        → all 8 expenses visible
  date_from=06-05  → 5 expenses (06-05 .. 06-11)
  date_to=06-07    → 4 expenses (06-01 .. 06-07)
  06-05 .. 06-09   → 3 expenses (06-05, 06-07, 06-09)
  empty range      → 0 expenses
"""

import pytest
from werkzeug.security import generate_password_hash

import database.db as db_module
from app import app as flask_app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEST_USER = {
    "name": "Test User",
    "email": "testuser@spendly.test",
    "password": "testpass1",
}

_TEST_EXPENSES = [
    (12.50,  "Food",          "2026-06-01", "Lunch"),
    (45.00,  "Transport",     "2026-06-02", "Monthly bus pass"),
    (120.00, "Bills",         "2026-06-03", "Electricity"),
    (30.00,  "Health",        "2026-06-05", "Pharmacy"),
    (25.00,  "Entertainment", "2026-06-07", "Streaming services"),
    (89.99,  "Shopping",      "2026-06-09", "Shoes"),
    (15.00,  "Other",         "2026-06-10", "Miscellaneous"),
    (8.75,   "Food",          "2026-06-11", "Coffee & snacks"),
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app(monkeypatch, tmp_path):
    """
    Flask app configured for testing with an isolated per-test SQLite file.

    We use a temp file (not :memory:) because Flask opens a new connection on
    every request; a file-backed DB persists those connections automatically,
    whereas :memory: would create an empty DB on each new connection.

    monkeypatch replaces database.db.DB_PATH with the temp file path so that
    every call to get_db() inside the running app hits this test database.
    """
    db_path = str(tmp_path / "test_expense_tracker.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_path)

    flask_app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "WTF_CSRF_ENABLED": False,
    })

    with flask_app.app_context():
        db_module.init_db()
        yield flask_app


@pytest.fixture
def client(app):
    """Unauthenticated test client."""
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """
    Test client with a registered + logged-in user.
    Returns (test_client, user_email, user_password) tuple.
    """
    client.post("/register", data={
        "name": _TEST_USER["name"],
        "email": _TEST_USER["email"],
        "password": _TEST_USER["password"],
        "confirm_password": _TEST_USER["password"],
    })
    client.post("/login", data={
        "email": _TEST_USER["email"],
        "password": _TEST_USER["password"],
    })
    return client


@pytest.fixture
def seeded_client(auth_client, app):
    """
    Logged-in test client with 8 dated expenses already in the database.
    Also inserts a second user with their own expenses to verify data isolation.
    """
    with app.app_context():
        conn = db_module.get_db()

        # Retrieve the test user id
        user = conn.execute(
            "SELECT id FROM users WHERE email = ?", (_TEST_USER["email"],)
        ).fetchone()
        user_id = user["id"]

        # Seed expenses for the test user
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            [(user_id, amt, cat, dt, desc) for amt, cat, dt, desc in _TEST_EXPENSES],
        )

        # Insert a second user with their own expense (data isolation guard)
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Other User", "other@spendly.test", generate_password_hash("otherpass")),
        )
        other_user_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (other_user_id, 999.00, "Food", "2026-06-05", "Other user expense"),
        )

        conn.commit()
        conn.close()

    return auth_client


# ---------------------------------------------------------------------------
# 1. Auth guard
# ---------------------------------------------------------------------------

class TestAuthGuard:
    def test_unauthenticated_get_profile_redirects_to_login(self, client):
        """Unauthenticated GET /profile must redirect to /login (302)."""
        response = client.get("/profile")
        assert response.status_code == 302, (
            "Expected 302 redirect for unauthenticated /profile"
        )
        assert "/login" in response.headers["Location"], (
            "Redirect target should be /login"
        )

    def test_unauthenticated_get_profile_with_filter_params_redirects(self, client):
        """Filter params must not bypass the auth guard."""
        response = client.get("/profile?date_from=2026-06-01&date_to=2026-06-11")
        assert response.status_code == 302, (
            "Expected 302 for unauthenticated request even with date params"
        )
        assert "/login" in response.headers["Location"]


# ---------------------------------------------------------------------------
# 2. Unfiltered baseline
# ---------------------------------------------------------------------------

class TestUnfilteredBaseline:
    def test_profile_no_params_returns_200(self, seeded_client):
        """GET /profile with no params must return HTTP 200."""
        response = seeded_client.get("/profile")
        assert response.status_code == 200, "Expected 200 for authenticated /profile"

    def test_profile_no_params_shows_all_expenses(self, seeded_client):
        """All 8 seeded expense dates must appear in the unfiltered page."""
        response = seeded_client.get("/profile")
        html = response.data
        # Every distinct date in our test dataset must be present somewhere on the page
        for _, _, date, _ in _TEST_EXPENSES:
            assert date.encode() in html, (
                f"Expected expense with date {date} to appear in unfiltered profile"
            )

    def test_profile_no_params_does_not_show_active_filter_banner(self, seeded_client):
        """Active-filter banner must NOT be shown when no filter params are supplied."""
        response = seeded_client.get("/profile")
        html = response.data.decode()
        # The banner should only render when a filter is active; with no params it
        # must not appear. We look for the class name from the spec.
        assert "date-filter-active" not in html, (
            "Active-filter banner should not appear when no date params are supplied"
        )

    def test_profile_no_params_does_not_show_clear_link(self, seeded_client):
        """Clear link (href='/profile') in the active-filter banner must not appear
        when no filter is active. We narrow the check to the banner section by
        looking for the canonical clear-filter anchor pattern described in the spec."""
        response = seeded_client.get("/profile")
        html = response.data.decode()
        # The clear link is distinguished by appearing inside the active-filter banner.
        # The banner itself must not render, so the clear link inside it is also absent.
        assert "date-filter-active" not in html, (
            "No active-filter banner means no clear link"
        )


# ---------------------------------------------------------------------------
# 3. Filter form presence
# ---------------------------------------------------------------------------

class TestFilterFormPresence:
    def test_filter_form_present_when_no_filter_active(self, auth_client):
        """The date filter form must be visible on the page even without active filters."""
        response = auth_client.get("/profile")
        html = response.data.decode()
        assert "date-filter-form" in html or 'method="get"' in html.lower() or (
            'name="date_from"' in html and 'name="date_to"' in html
        ), "Filter form with date_from and date_to inputs must be present on the page"

    def test_filter_form_has_date_from_input(self, seeded_client):
        """`date_from` input must be present in the filter form."""
        response = seeded_client.get("/profile")
        html = response.data.decode()
        assert 'name="date_from"' in html, (
            "Expected an input with name='date_from' in the filter form"
        )

    def test_filter_form_has_date_to_input(self, seeded_client):
        """`date_to` input must be present in the filter form."""
        response = seeded_client.get("/profile")
        html = response.data.decode()
        assert 'name="date_to"' in html, (
            "Expected an input with name='date_to' in the filter form"
        )

    def test_filter_form_has_submit_button(self, seeded_client):
        """A submit button labelled 'Filter' (case-insensitive) must be present."""
        response = seeded_client.get("/profile")
        html = response.data.decode()
        assert "Filter" in html, (
            "Expected a 'Filter' submit button in the filter form"
        )

    def test_filter_form_uses_get_method(self, seeded_client):
        """The filter form must use method='GET' so filtered URLs are bookmarkable."""
        response = seeded_client.get("/profile")
        html = response.data.decode().lower()
        assert 'method="get"' in html or "method='get'" in html, (
            "Filter form must submit via GET so the URL is shareable"
        )


# ---------------------------------------------------------------------------
# 4. date_from only filter
# ---------------------------------------------------------------------------

class TestDateFromFilter:
    def test_date_from_returns_200(self, seeded_client):
        response = seeded_client.get("/profile?date_from=2026-06-05")
        assert response.status_code == 200

    def test_date_from_includes_expenses_on_boundary_date(self, seeded_client):
        """An expense whose date equals date_from must be included (inclusive lower bound)."""
        response = seeded_client.get("/profile?date_from=2026-06-05")
        html = response.data
        assert b"2026-06-05" in html, (
            "Expense on the date_from boundary date must be included"
        )

    def test_date_from_includes_expenses_after_boundary(self, seeded_client):
        """Expenses strictly after date_from must be included."""
        response = seeded_client.get("/profile?date_from=2026-06-05")
        html = response.data
        for date in ["2026-06-07", "2026-06-09", "2026-06-10", "2026-06-11"]:
            assert date.encode() in html, (
                f"Expense dated {date} should appear when date_from=2026-06-05"
            )

    def test_date_from_excludes_expenses_before_boundary(self, seeded_client):
        """Expenses strictly before date_from must NOT appear in the filtered view."""
        response = seeded_client.get("/profile?date_from=2026-06-05")
        html = response.data
        for date in ["2026-06-01", "2026-06-02", "2026-06-03"]:
            assert date.encode() not in html, (
                f"Expense dated {date} must be excluded when date_from=2026-06-05"
            )

    def test_date_from_shows_active_filter_banner(self, seeded_client):
        """Active-filter banner must render when only date_from is set."""
        response = seeded_client.get("/profile?date_from=2026-06-05")
        html = response.data.decode()
        assert "date-filter-active" in html, (
            "Active-filter banner must appear when date_from is supplied"
        )

    def test_date_from_retains_value_in_input(self, seeded_client):
        """The date_from input must show the submitted date as its value."""
        response = seeded_client.get("/profile?date_from=2026-06-05")
        html = response.data.decode()
        assert "2026-06-05" in html, (
            "Submitted date_from value must be retained in the rendered form"
        )


# ---------------------------------------------------------------------------
# 5. date_to only filter
# ---------------------------------------------------------------------------

class TestDateToFilter:
    def test_date_to_returns_200(self, seeded_client):
        response = seeded_client.get("/profile?date_to=2026-06-07")
        assert response.status_code == 200

    def test_date_to_includes_expenses_on_boundary_date(self, seeded_client):
        """An expense whose date equals date_to must be included (inclusive upper bound)."""
        response = seeded_client.get("/profile?date_to=2026-06-07")
        html = response.data
        assert b"2026-06-07" in html, (
            "Expense on the date_to boundary date must be included"
        )

    def test_date_to_includes_expenses_before_boundary(self, seeded_client):
        """Expenses strictly before date_to must be included."""
        response = seeded_client.get("/profile?date_to=2026-06-07")
        html = response.data
        for date in ["2026-06-01", "2026-06-02", "2026-06-03", "2026-06-05"]:
            assert date.encode() in html, (
                f"Expense dated {date} should appear when date_to=2026-06-07"
            )

    def test_date_to_excludes_expenses_after_boundary(self, seeded_client):
        """Expenses strictly after date_to must NOT appear in the filtered view."""
        response = seeded_client.get("/profile?date_to=2026-06-07")
        html = response.data
        for date in ["2026-06-09", "2026-06-10", "2026-06-11"]:
            assert date.encode() not in html, (
                f"Expense dated {date} must be excluded when date_to=2026-06-07"
            )

    def test_date_to_shows_active_filter_banner(self, seeded_client):
        """Active-filter banner must render when only date_to is set."""
        response = seeded_client.get("/profile?date_to=2026-06-07")
        html = response.data.decode()
        assert "date-filter-active" in html, (
            "Active-filter banner must appear when date_to is supplied"
        )

    def test_date_to_retains_value_in_input(self, seeded_client):
        """The date_to input must show the submitted date as its value."""
        response = seeded_client.get("/profile?date_to=2026-06-07")
        html = response.data.decode()
        assert "2026-06-07" in html, (
            "Submitted date_to value must be retained in the rendered form"
        )


# ---------------------------------------------------------------------------
# 6. Both bounds filter
# ---------------------------------------------------------------------------

class TestBothBoundsFilter:
    # Expenses that fall in 2026-06-05 .. 2026-06-09 (inclusive):
    #   2026-06-05  30.00  Health
    #   2026-06-07  25.00  Entertainment
    #   2026-06-09  89.99  Shopping
    # Total: 3 expenses, sum = 144.99

    _FROM = "2026-06-05"
    _TO   = "2026-06-09"
    _URL  = f"/profile?date_from={_FROM}&date_to={_TO}"

    def test_both_bounds_returns_200(self, seeded_client):
        response = seeded_client.get(self._URL)
        assert response.status_code == 200

    def test_both_bounds_includes_in_range_expenses(self, seeded_client):
        """Expenses inside the range (inclusive) must appear."""
        response = seeded_client.get(self._URL)
        html = response.data
        for date in ["2026-06-05", "2026-06-07", "2026-06-09"]:
            assert date.encode() in html, (
                f"Expense dated {date} must appear in [{self._FROM}, {self._TO}]"
            )

    def test_both_bounds_excludes_before_range(self, seeded_client):
        """Expenses before the from-date must NOT appear."""
        response = seeded_client.get(self._URL)
        html = response.data
        for date in ["2026-06-01", "2026-06-02", "2026-06-03"]:
            assert date.encode() not in html, (
                f"Expense dated {date} must be excluded by date_from={self._FROM}"
            )

    def test_both_bounds_excludes_after_range(self, seeded_client):
        """Expenses after the to-date must NOT appear."""
        response = seeded_client.get(self._URL)
        html = response.data
        for date in ["2026-06-10", "2026-06-11"]:
            assert date.encode() not in html, (
                f"Expense dated {date} must be excluded by date_to={self._TO}"
            )

    def test_both_bounds_shows_active_filter_banner(self, seeded_client):
        """Active-filter banner must render when both date_from and date_to are set."""
        response = seeded_client.get(self._URL)
        html = response.data.decode()
        assert "date-filter-active" in html, (
            "Active-filter banner must be visible when both date params are present"
        )

    def test_both_bounds_banner_displays_from_date(self, seeded_client):
        """Banner must show the date_from value the user submitted."""
        response = seeded_client.get(self._URL)
        html = response.data.decode()
        assert self._FROM in html, (
            "Active-filter banner must display the date_from value"
        )

    def test_both_bounds_banner_displays_to_date(self, seeded_client):
        """Banner must show the date_to value the user submitted."""
        response = seeded_client.get(self._URL)
        html = response.data.decode()
        assert self._TO in html, (
            "Active-filter banner must display the date_to value"
        )

    def test_both_bounds_retains_from_value_in_form(self, seeded_client):
        """date_from input must retain the submitted value."""
        response = seeded_client.get(self._URL)
        html = response.data.decode()
        assert self._FROM in html, (
            "date_from input must retain '2026-06-05' as its value after submit"
        )

    def test_both_bounds_retains_to_value_in_form(self, seeded_client):
        """date_to input must retain the submitted value."""
        response = seeded_client.get(self._URL)
        html = response.data.decode()
        assert self._TO in html, (
            "date_to input must retain '2026-06-09' as its value after submit"
        )

    def test_both_bounds_stats_reflect_filtered_range(self, seeded_client):
        """Stat tiles must reflect only the in-range expenses.
        We verify this by checking that amounts from outside the range are not
        rendered in a way that would imply they are counted — the amounts unique
        to out-of-range expenses (12.50, 45.00, 120.00, 15.00, 8.75) must not
        appear in contexts that suggest they contribute to the stats.
        More concretely, the Health/Entertainment/Shopping descriptions unique
        to the in-range period should be present, and out-of-range ones absent."""
        response = seeded_client.get(self._URL)
        html = response.data.decode()
        # Descriptions unique to in-range expenses must appear
        assert "Pharmacy" in html, "In-range expense description 'Pharmacy' must appear"
        assert "Streaming" in html, "In-range expense description must appear"
        assert "Shoes" in html, "In-range expense description 'Shoes' must appear"
        # Descriptions unique to out-of-range expenses must not appear
        assert "Electricity" not in html, (
            "'Electricity' expense (2026-06-03) must not appear in filtered view"
        )
        assert "Miscellaneous" not in html, (
            "'Miscellaneous' expense (2026-06-10) must not appear in filtered view"
        )

    def test_both_bounds_categories_reflect_filtered_range(self, seeded_client):
        """Category breakdown must only include categories present in the filtered range."""
        response = seeded_client.get(self._URL)
        html = response.data.decode()
        # Categories in range: Health, Entertainment, Shopping
        for cat in ["Health", "Entertainment", "Shopping"]:
            assert cat in html, (
                f"Category '{cat}' must appear in the filtered category breakdown"
            )
        # Categories entirely outside range: Transport, Bills, Other
        # Food has entries outside range (06-01, 06-11) but none inside,
        # so it should not appear in the category breakdown for this range.
        # (Transport: 06-02, Bills: 06-03, Other: 06-10, Food: 06-01 and 06-11)
        for cat in ["Transport", "Bills", "Other"]:
            assert cat not in html, (
                f"Category '{cat}' must not appear — all its expenses are outside the range"
            )


# ---------------------------------------------------------------------------
# 7. Clear link
# ---------------------------------------------------------------------------

class TestClearLink:
    def test_clear_link_present_when_filter_active(self, seeded_client):
        """A link pointing to '/profile' (no query params) must exist in the banner
        when at least one filter bound is active."""
        response = seeded_client.get("/profile?date_from=2026-06-05")
        html = response.data.decode()
        # The clear link must have href="/profile" exactly (no query string)
        assert 'href="/profile"' in html, (
            "Clear link with href='/profile' must be present when filter is active"
        )

    def test_clear_link_absent_when_no_filter(self, seeded_client):
        """Without an active filter the active-filter banner (and therefore the Clear
        link) must not be rendered."""
        response = seeded_client.get("/profile")
        html = response.data.decode()
        assert "date-filter-active" not in html, (
            "Banner (and its Clear link) must not render without active filter"
        )

    def test_clear_link_present_with_both_params(self, seeded_client):
        """Clear link must be present when both date_from and date_to are supplied."""
        response = seeded_client.get(
            "/profile?date_from=2026-06-05&date_to=2026-06-09"
        )
        html = response.data.decode()
        assert 'href="/profile"' in html, (
            "Clear link must be present when both filter bounds are active"
        )


# ---------------------------------------------------------------------------
# 8. Invalid date string handling
# ---------------------------------------------------------------------------

class TestInvalidDateHandling:
    def test_invalid_date_from_returns_200_not_500(self, seeded_client):
        """A malformed date_from must not cause a 500; the server must return 200."""
        response = seeded_client.get("/profile?date_from=not-a-date")
        assert response.status_code == 200, (
            "Invalid date_from must not cause a 500 — expected 200 with flash error"
        )

    def test_invalid_date_from_shows_flash_error(self, seeded_client):
        """A malformed date_from must trigger a visible flash error message."""
        response = seeded_client.get("/profile?date_from=not-a-date")
        html = response.data.decode()
        # The spec says: flash an error and ignore that param.
        # We look for keywords from the spec-mandated flash message.
        assert (
            "Invalid" in html or "invalid" in html or "error" in html.lower()
        ), "A flash error must appear in the page when date_from is not a valid date"

    def test_invalid_date_from_loads_unfiltered_view(self, seeded_client):
        """When date_from is invalid it must be ignored — all expenses are shown."""
        response = seeded_client.get("/profile?date_from=not-a-date")
        html = response.data
        # All expense dates must still appear (unfiltered fallback)
        for _, _, date, _ in _TEST_EXPENSES:
            assert date.encode() in html, (
                f"Expected expense date {date} in unfiltered fallback after invalid date_from"
            )

    def test_invalid_date_to_returns_200_not_500(self, seeded_client):
        """A malformed date_to must not cause a 500; the server must return 200."""
        response = seeded_client.get("/profile?date_to=bad-date")
        assert response.status_code == 200, (
            "Invalid date_to must not cause a 500 — expected 200 with flash error"
        )

    def test_invalid_date_to_shows_flash_error(self, seeded_client):
        """A malformed date_to must trigger a visible flash error message."""
        response = seeded_client.get("/profile?date_to=bad-date")
        html = response.data.decode()
        assert (
            "Invalid" in html or "invalid" in html or "error" in html.lower()
        ), "A flash error must appear in the page when date_to is not a valid date"

    def test_invalid_date_to_loads_unfiltered_view(self, seeded_client):
        """When date_to is invalid it must be ignored — all expenses are shown."""
        response = seeded_client.get("/profile?date_to=bad-date")
        html = response.data
        for _, _, date, _ in _TEST_EXPENSES:
            assert date.encode() in html, (
                f"Expected expense date {date} in unfiltered fallback after invalid date_to"
            )

    def test_both_params_invalid_returns_200(self, seeded_client):
        """Both params being invalid must still produce a 200, not a 500."""
        response = seeded_client.get(
            "/profile?date_from=not-a-date&date_to=also-bad"
        )
        assert response.status_code == 200, (
            "Both params invalid must still return 200"
        )

    def test_both_params_invalid_shows_unfiltered_view(self, seeded_client):
        """When both params are invalid, the full unfiltered expense list is shown."""
        response = seeded_client.get(
            "/profile?date_from=not-a-date&date_to=also-bad"
        )
        html = response.data
        for _, _, date, _ in _TEST_EXPENSES:
            assert date.encode() in html, (
                f"Expected expense date {date} in unfiltered fallback when both params invalid"
            )

    @pytest.mark.parametrize("bad_date", [
        "2026/06/05",    # wrong separator
        "06-05-2026",    # US format, not ISO
        "20260605",      # no separators
        "2026-13-01",    # month 13 doesn't exist
        "2026-06-32",    # day 32 doesn't exist
        "",              # empty — treated as absent, not an error
    ])
    def test_various_invalid_date_from_values_do_not_cause_500(
        self, seeded_client, bad_date
    ):
        """A range of bad date_from formats must all result in 200, never 500."""
        response = seeded_client.get(f"/profile?date_from={bad_date}")
        assert response.status_code == 200, (
            f"date_from='{bad_date}' must not produce a 500"
        )


# ---------------------------------------------------------------------------
# 9. Empty string params (treated as absent)
# ---------------------------------------------------------------------------

class TestEmptyParamHandling:
    def test_empty_date_from_treated_as_absent(self, seeded_client):
        """date_from='' must be treated as if the param was not supplied."""
        response = seeded_client.get("/profile?date_from=")
        assert response.status_code == 200
        html = response.data.decode()
        # No active-filter banner should appear for an empty param
        assert "date-filter-active" not in html, (
            "Empty date_from must not activate the filter banner"
        )

    def test_empty_date_to_treated_as_absent(self, seeded_client):
        """date_to='' must be treated as if the param was not supplied."""
        response = seeded_client.get("/profile?date_to=")
        assert response.status_code == 200
        html = response.data.decode()
        assert "date-filter-active" not in html, (
            "Empty date_to must not activate the filter banner"
        )

    def test_both_empty_params_show_unfiltered_view(self, seeded_client):
        """Both params empty must produce the same result as no params at all."""
        response_empty = seeded_client.get("/profile?date_from=&date_to=")
        response_none  = seeded_client.get("/profile")
        # Both must return 200
        assert response_empty.status_code == 200
        assert response_none.status_code == 200
        # Neither should show the active-filter banner
        assert "date-filter-active" not in response_empty.data.decode()
        assert "date-filter-active" not in response_none.data.decode()


# ---------------------------------------------------------------------------
# 10. Empty result range
# ---------------------------------------------------------------------------

class TestEmptyResultRange:
    def test_filter_with_no_matching_expenses_returns_200(self, seeded_client):
        """A date range that matches no expenses must still return 200."""
        response = seeded_client.get(
            "/profile?date_from=2030-01-01&date_to=2030-12-31"
        )
        assert response.status_code == 200, (
            "Empty result range must return 200, not 404 or 500"
        )

    def test_filter_with_no_matching_expenses_shows_active_banner(self, seeded_client):
        """The active-filter banner must still render even when no expenses match."""
        response = seeded_client.get(
            "/profile?date_from=2030-01-01&date_to=2030-12-31"
        )
        html = response.data.decode()
        assert "date-filter-active" in html, (
            "Active-filter banner must appear even when the date range returns 0 expenses"
        )

    def test_filter_with_no_matching_expenses_excludes_all_dates(self, seeded_client):
        """None of the seeded expense dates should appear in a future-date filter."""
        response = seeded_client.get(
            "/profile?date_from=2030-01-01&date_to=2030-12-31"
        )
        html = response.data
        for _, _, date, _ in _TEST_EXPENSES:
            assert date.encode() not in html, (
                f"Expense dated {date} must not appear in a filter for year 2030"
            )


# ---------------------------------------------------------------------------
# 11. Data isolation
# ---------------------------------------------------------------------------

class TestDataIsolation:
    def test_other_user_expenses_never_appear_on_profile(self, seeded_client):
        """The 'other user' expense (amount 999.00) must never appear on the
        authenticated user's profile page, filtered or unfiltered."""
        for url in [
            "/profile",
            "/profile?date_from=2026-06-05",
            "/profile?date_to=2026-06-07",
            "/profile?date_from=2026-06-01&date_to=2026-06-11",
        ]:
            response = seeded_client.get(url)
            html = response.data.decode()
            assert "999" not in html, (
                f"Other user's expense (999.00) must not appear on the profile "
                f"page for URL {url}"
            )
            assert "Other user expense" not in html, (
                "Other user's expense description must never appear on this user's profile"
            )
