# Spec: Backend Routes For Profile Page

## Overview

Implement the three stub routes that currently return plain strings — `POST /expenses/add`, `GET/POST /expenses/<id>/edit`, and `POST /expenses/<id>/delete` — so that logged-in users can create, update, and remove their own expense records. This step also updates `profile.html` to surface an "Add expense" button and per-row Edit / Delete controls inside the existing expense list modal, wiring the UI to the newly live routes.

---

## Depends on

- **Step 1 — Database Setup:** `expenses` table and `get_db()` must exist.
- **Step 2 — Registration:** At least one user must exist in the DB.
- **Step 3 — Login and Logout:** Session management and `login_required()` must be in place.
- **Step 4 — Profile Page Design:** `profile.html` and all `.profile-*` CSS classes must exist; the expense list modal is already rendered.

---

## Routes

| Method | Path | Description | Access |
|--------|------|-------------|--------|
| `GET` | `/expenses/add` | Render the add-expense form | Logged-in only |
| `POST` | `/expenses/add` | Validate and insert a new expense row | Logged-in only |
| `GET` | `/expenses/<int:id>/edit` | Render the edit-expense form pre-filled with current values | Logged-in only |
| `POST` | `/expenses/<int:id>/edit` | Validate and update the expense row | Logged-in only |
| `POST` | `/expenses/<int:id>/delete` | Delete the expense row and redirect | Logged-in only |

> **Note:** the existing stubs in `app.py` (lines 146–158) accept only `GET`. All three must be changed to also accept `POST` via `methods=["GET", "POST"]`. The delete route becomes `POST`-only to prevent accidental deletion via link prefetch.

---

## Database changes

No schema changes. All reads and writes target the existing `expenses` table:

- **Insert:** `INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)`
- **Select by id + owner:** `SELECT * FROM expenses WHERE id = ? AND user_id = ?`
- **Update:** `UPDATE expenses SET amount=?, category=?, date=?, description=? WHERE id=? AND user_id=?`
- **Delete:** `DELETE FROM expenses WHERE id=? AND user_id=?`

The `AND user_id = ?` clause in every write query is the ownership guard — it prevents one user from modifying another user's data.

---

## Templates

**Create:**
- `templates/add-expense.html` — form with fields: amount, category (dropdown), date, description (optional). Shows validation errors inline.
- `templates/edit-expense.html` — same form fields as add, pre-populated with the existing expense values.

**Modify:**
- `templates/profile.html` — inside the existing expense list modal (`#listModal`):
  - Add an "Add expense" button above the expense rows that links to `url_for('add_expense')`.
  - Add Edit and Delete controls to each `.expense-row`. Edit is an anchor to `url_for('edit_expense', id=e.id)`. Delete is a `<form method="POST">` with a submit button (no JS confirm needed).
  - Update the expenses query in `app.py` to also fetch `id` so the template can build these URLs.

---

## Files to change

- `app.py` — replace stub bodies for `add_expense`, `edit_expense`, `delete_expense` with full implementations; update `methods` on all three; update `expenses_list` query in `/profile` to include `id`.
- `templates/profile.html` — add "Add expense" link above the list; add Edit/Delete controls per row.
- `static/css/style.css` — add `.expense-actions`, `.expense-edit-btn`, `.expense-delete-btn`, `.expense-delete-form` classes at the bottom of the file using CSS variables only.

---

## Files to create

- `templates/add-expense.html`
- `templates/edit-expense.html`

---

## New dependencies

No new dependencies.

---

## Rules for implementation

- No SQLAlchemy or ORMs — use raw `sqlite3` via `get_db()`.
- Parameterised queries only — never format user-supplied values into SQL strings.
- Passwords hashed with werkzeug (not applicable here, but maintain the pattern).
- Use CSS variables — never hardcode hex values in new styles.
- All templates extend `base.html`.
- Guard every route with `login_required()` — call it at the very top and `return` its result if not `None`.
- **Ownership check is mandatory on every DB write.** Always include `AND user_id = ?` bound to `session['user_id']`. If the row is not found (wrong owner or non-existent id), return a 404 via `abort(404)`.
- Import `abort` from Flask at the top of `app.py`.
- Amount validation: must be a positive number. Reject zero or negative values with an inline error.
- Date validation: must be a valid `YYYY-MM-DD` string. Use Python's `datetime.date.fromisoformat()` — catch `ValueError` and return an error.
- Category validation: must be one of the seven fixed values — Food, Transport, Bills, Health, Entertainment, Shopping, Other. Reject anything else.
- After a successful insert, edit, or delete, redirect to `url_for('profile')` with an appropriate `flash()` message.
- Flash messages must be rendered. Add a flash block to `base.html` inside `<main>` above `{% block content %}` if not already present.
- The delete action must use `<form method="POST">` — never a plain `<a>` tag, to avoid GET-based deletion.

---

## Definition of done

- [ ] `GET /expenses/add` redirects to `/login` when not logged in.
- [ ] `GET /expenses/add` renders the add form for a logged-in user.
- [ ] Submitting the add form with valid data inserts a row in `expenses` and redirects to `/profile` with a success flash.
- [ ] Submitting the add form with a negative or zero amount shows an inline error and does not insert.
- [ ] Submitting the add form with an invalid date shows an inline error and does not insert.
- [ ] Submitting the add form with an invalid category shows an inline error and does not insert.
- [ ] `GET /expenses/<id>/edit` redirects to `/login` when not logged in.
- [ ] `GET /expenses/<id>/edit` returns 404 when the expense belongs to a different user.
- [ ] `GET /expenses/<id>/edit` renders the edit form pre-filled with current values.
- [ ] Submitting the edit form with valid data updates the row and redirects to `/profile` with a success flash.
- [ ] Submitting the edit form with invalid data shows an inline error and does not update.
- [ ] `POST /expenses/<id>/delete` redirects to `/login` when not logged in.
- [ ] `POST /expenses/<id>/delete` returns 404 when the expense belongs to a different user.
- [ ] `POST /expenses/<id>/delete` removes the row and redirects to `/profile` with a success flash.
- [ ] The profile expense list modal shows Edit and Delete controls for each expense row.
- [ ] The profile page shows an "Add expense" button/link.
- [ ] App starts without errors (`venv/bin/python3 app.py`).
- [ ] No existing tests are broken (`venv/bin/pytest`).
