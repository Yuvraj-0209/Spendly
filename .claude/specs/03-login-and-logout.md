# Spec: Login and Logout

## Overview

Implement session-based authentication so registered users can sign in and sign out. On successful login, the user's `id` and `name` are stored in the Flask session; all subsequent requests can read these values to personalise the UI and guard protected routes. Logout clears the session and redirects to the landing page. This step also updates the navbar in `base.html` so it is session-aware — showing "Sign in / Get started" to guests and "Hi, {name} / Logout" to authenticated users.

---

## Depends on

- **Step 1 — Database Setup:** `users` table and `get_db()` must exist.
- **Step 2 — Registration:** At least one user must exist in the DB to test login.

---

## Routes

| Method | Path | Description | Access |
|--------|------|-------------|--------|
| `GET` | `/login` | Render the login form | Public (redirect to `/profile` if already logged in) |
| `POST` | `/login` | Validate credentials, set session, redirect | Public |
| `GET` | `/logout` | Clear session, redirect to `/` | Logged-in (safe to call as guest too) |

The existing GET-only `/login` stub and the "Logout — coming in Step 3" placeholder both need to be replaced.

---

## Database changes

No database changes. Uses existing `users` table:
```
users(id, name, email, password_hash)
```
Login queries by `email`, then verifies `password_hash` with `check_password_hash`.

---

## Templates

**Modify:**
- `templates/login.html` — add `method="POST"` (already present), wire up both GET and POST in route (already has form structure and `{% if error %}` block — no template change needed beyond confirming form fields are correct)
- `templates/base.html` — make the navbar session-aware:
  - **Guest:** show `Sign in` link + `Get started` CTA (current hardcoded state)
  - **Logged in:** show `Hi, {{ session['user_name'] }}` (non-linked) + `Logout` link

**Create:** None.

---

## Files to change

- `app.py` — add `check_password_hash` import, `session` import, convert `/login` to GET+POST, implement `/logout`, add `login_required` helper
- `templates/base.html` — conditional navbar based on `session`

---

## Files to create

None.

---

## New dependencies

No new pip packages.
Uses:
- `werkzeug.security.check_password_hash` (already installed)
- `flask.session` (part of Flask)

---

## Rules for implementation

- No SQLAlchemy or ORMs — use raw `sqlite3` via `get_db()`
- Parameterised queries only — no string formatting in SQL
- Passwords verified with `werkzeug.security.check_password_hash` — never compare plaintext
- Use CSS variables — never hardcode hex values in new styles
- All templates extend `base.html`
- Store only `user_id` (int) and `user_name` (str) in the session — never store the password hash or full user object
- On successful login, redirect to `/profile` (the next stub to be implemented)
- On failed login, use `render_template('login.html', error="...")` — consistent with existing error pattern
- `login_required` — implement as a simple helper function (not a decorator) that checks `session.get('user_id')` and returns a redirect if missing; call it at the top of protected route functions
- `/login` GET — if user is already logged in (`session.get('user_id')`), redirect to `/profile` immediately
- `/logout` — use `session.clear()`, then redirect to `url_for('landing')`

---

## Definition of done

- [ ] `GET /login` renders the form for guests
- [ ] `GET /login` redirects to `/profile` if the user is already logged in
- [ ] Submitting with a non-existent email shows "Invalid email or password."
- [ ] Submitting with a correct email but wrong password shows "Invalid email or password."
- [ ] Submitting valid credentials sets `session['user_id']` and `session['user_name']` and redirects to `/profile`
- [ ] After login, the navbar shows "Hi, {name}" and a "Logout" link instead of "Sign in / Get started"
- [ ] `GET /logout` clears the session and redirects to the landing page (`/`)
- [ ] After logout, the navbar reverts to the guest state
- [ ] Visiting `/logout` as a guest (no session) does not raise an error — it just redirects to `/`
- [ ] App starts without errors (`venv/bin/python3 app.py`)
