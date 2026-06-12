# Spec: Registration

## Overview

Implement the user registration flow so new visitors can create a Spendly account. This is the first authenticated-user feature and gates all subsequent steps (login, expense tracking, profile). A visitor fills in their name, email, and password; the server validates the input, checks for a duplicate email, hashes the password, inserts the new user, and redirects to the login page with a success flash message.

---

## Depends on

- **Step 1 — Database Setup:** `users` table and `get_db()` must exist and work correctly.

---

## Routes

| Method | Path | Description | Access |
|--------|------|-------------|--------|
| `GET` | `/register` | Render the registration form | Public |
| `POST` | `/register` | Process form submission, insert user, redirect | Public |

The existing `GET /register` stub in `app.py` already renders `register.html` — it needs to be converted to handle both methods and add POST logic.

---

## Database changes

No new tables or columns. Uses the existing `users` table:

```
users(id, name, email, password_hash, created_at)
```

The `UNIQUE` constraint on `email` already enforces uniqueness at the DB level. The route should also check for duplicates explicitly to return a user-friendly error rather than a raw constraint violation.

---

## Templates

**Modify:**
- `templates/register.html` — currently a static form shell; add:
  - `method="POST"` and `action="/register"` on the `<form>` tag
  - `name` attributes on all inputs (`name`, `email`, `password`, `confirm_password`)
  - Flash message display block (errors and success)
  - Client-side: password and confirm-password match hint (optional, JS)

No new templates needed.

---

## Files to change

- `app.py` — replace the `GET`-only `/register` route with a `GET/POST` route containing full registration logic
- `templates/register.html` — wire up form attributes and flash message rendering

---

## Files to create

None.

---

## New dependencies

No new pip packages.  
Uses:
- `werkzeug.security.generate_password_hash` (already installed)
- `flask.request`, `flask.redirect`, `flask.url_for`, `flask.flash`, `flask.session` (all part of Flask)

---

## Rules for implementation

- No SQLAlchemy or ORMs — use raw `sqlite3` via `get_db()`
- Parameterised queries only — no string formatting in SQL
- Hash passwords with `werkzeug.security.generate_password_hash` before inserting
- Use CSS variables — never hardcode hex values in new styles
- All templates extend `base.html`
- Flash messages must use Flask's `flash()` / `get_flashed_messages()` pattern
- Validate all three fields server-side (non-empty name, valid-looking email, password length ≥ 8, password == confirm_password)
- On duplicate email, show a specific error: "An account with that email already exists."
- On success, redirect to `/login` — do NOT auto-login the user (that is Step 3)
- Set `app.secret_key` in `app.py` (required for `flash()` to work); use a hard-coded dev string for now

---

## Definition of done

- [ ] `GET /register` renders the form with no errors on a fresh load
- [ ] Submitting with all fields blank shows validation errors for each missing field
- [ ] Submitting with a password shorter than 8 characters shows a length error
- [ ] Submitting with mismatched passwords shows a mismatch error
- [ ] Submitting a valid form with a new email inserts a row in `users` and redirects to `/login`
- [ ] The inserted `password_hash` is a werkzeug hash (starts with `scrypt:` or `pbkdf2:`), not plaintext
- [ ] Submitting a duplicate email shows "An account with that email already exists."
- [ ] Submitting the form twice with the same email does not create two users
- [ ] Flash success message is visible on the `/login` page after successful registration
- [ ] App starts without errors (`venv/bin/python3 app.py`)
