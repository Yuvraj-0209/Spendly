# Spec: Date Filter For Profile Page

## Overview

Add an optional date-range filter to the profile page so users can narrow their expense view to a specific period. The filter is applied via query parameters on the existing `/profile` route — no new route is needed. When active, all three data sets on the page (summary stats, category breakdown, and the expense list) reflect only the filtered period. A visible filter bar shows the active range and provides a one-click "Clear" button to return to the full view.

---

## Depends on

- **Step 1 — Database Setup:** `expenses` table and `get_db()` must exist.
- **Step 2 — Registration:** At least one user must exist in the DB.
- **Step 3 — Login and Logout:** Session management and `login_required()` must be in place.
- **Step 4 — Profile Page Design:** `profile.html` and all `.profile-*` CSS classes must exist.
- **Step 5 — Backend Routes for Profile Page:** Expense add/edit/delete routes and the full expenses list on the profile page must be working.

---

## Routes

No new routes. The existing `/profile` route is extended to accept optional query parameters:

- `GET /profile?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD` — returns the profile page with all data filtered to the given date range. Both params are optional; omitting either removes that bound.

---

## Database changes

No database changes. All filtering is done via `WHERE` clause additions on the existing `expenses` table using the `date` column (TEXT, stored as `YYYY-MM-DD`).

---

## Templates

**Modify:**
- `templates/profile.html` — add a date filter form above the stats section. The form submits via `GET` to `/profile`. Show an active-filter banner when a range is applied that displays the current `date_from` / `date_to` and a "Clear" link (`href="/profile"`). Pass `date_from`, `date_to` into the template so inputs retain their values after submit.

---

## Files to change

- `app.py` — update the `/profile` route to:
  1. Read `date_from` and `date_to` from `request.args`.
  2. Validate both values: if provided they must be valid `YYYY-MM-DD` strings (use `datetime.date.fromisoformat()`); if invalid, set a flash message and treat that param as absent.
  3. Build an optional SQL snippet `date_filter_sql` and a matching tuple of extra bind params, then append them to all three queries (stats, categories, expenses_list).
  4. Pass `date_from` and `date_to` back into `render_template` so the template can pre-fill inputs and show the active-filter banner.

- `templates/profile.html` — add the filter bar UI (see Templates above).

- `static/css/style.css` — add `.date-filter-bar`, `.date-filter-form`, `.date-filter-inputs`, `.date-filter-active` classes at the bottom of the file. Use CSS variables only — never hardcode hex values.

---

## Files to create

No new files.

---

## New dependencies

No new dependencies.

---

## Rules for implementation

- No SQLAlchemy or ORMs — use raw `sqlite3` via `get_db()`.
- Parameterised queries only — append date bounds as bind params, never via string formatting.
- Use CSS variables — never hardcode hex values in new styles.
- All templates extend `base.html`.
- Guard the `/profile` route with `login_required()` as it already is — do not remove it.
- If `date_from` is provided but `date_to` is not, apply only the lower bound (and vice versa).
- If an invalid date string is supplied, flash an error and ignore that param rather than raising a 500.
- The filter form must use `method="GET"` so the filtered URL is shareable/bookmarkable.
- The "Clear" link must point to `/profile` with no query params, removing the filter entirely.
- Do not re-implement the queries from scratch — keep the existing structure and append `AND date >= ?` / `AND date <= ?` clauses only when the respective param is present.
- The active-filter banner must only render when at least one of `date_from` or `date_to` is set.

---

## Definition of done

- [ ] Visiting `/profile` with no query params shows all expenses (unchanged behaviour).
- [ ] Visiting `/profile?date_from=2026-06-05` shows only expenses on or after 2026-06-05.
- [ ] Visiting `/profile?date_to=2026-06-07` shows only expenses on or before 2026-06-07.
- [ ] Visiting `/profile?date_from=2026-06-05&date_to=2026-06-09` shows only expenses in that range; the stats and category breakdown also reflect only that range.
- [ ] The date filter form is visible on the profile page with two date inputs (From / To) and a "Filter" button.
- [ ] After submitting the filter form, the date inputs retain their submitted values.
- [ ] An active-filter banner is shown when a range is active, displaying the applied bounds.
- [ ] The "Clear" link in the active-filter banner returns to `/profile` with no filters applied.
- [ ] Supplying an invalid date string (e.g. `date_from=not-a-date`) shows a flash error and loads the unfiltered profile rather than a 500.
- [ ] Visiting `/profile` without being logged in still redirects to `/login`.
- [ ] App starts without errors (`venv/bin/python3 app.py`).
- [ ] No existing tests are broken (`venv/bin/pytest`).
