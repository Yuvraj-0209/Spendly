# Spec: Profile Page Design

## Overview

Build the `/profile` page so logged-in users can see their account information at a glance. The page fetches the user's `name`, `email`, and `created_at` from the database and renders a clean, on-brand profile card. It also surfaces lightweight stats — total number of expenses logged and total amount spent — pulled from the `expenses` table. Unauthenticated visitors are redirected to `/login`. This step converts the current placeholder stub into a real, styled page that fits the Spendly design system.

---

## Depends on

- **Step 1 — Database Setup:** `users` and `expenses` tables and `get_db()` must exist.
- **Step 2 — Registration:** At least one user must exist in the DB.
- **Step 3 — Login and Logout:** Session management (`session['user_id']`, `session['user_name']`) and the `login_required` helper must be in place.

---

## Routes

| Method | Path | Description | Access |
|--------|------|-------------|--------|
| `GET` | `/profile` | Render the user's profile page | Logged-in only |

The existing `/profile` stub in `app.py` is replaced — no new route is added, only the handler body changes.

---

## Database changes

No schema changes. Two read-only queries against existing tables:

1. Fetch full user row: `SELECT id, name, email, created_at FROM users WHERE id = ?`
2. Fetch aggregate stats: `SELECT COUNT(*) AS expense_count, COALESCE(SUM(amount), 0) AS total_spent FROM expenses WHERE user_id = ?`

---

## Templates

**Modify:**
- `templates/profile.html` — replace the placeholder `<h1>` with the full profile layout (avatar initials, name, email, member-since date, stats row, logout link).

**Create:** None.

---

## Files to change

- `app.py` — replace the `/profile` stub body: call `login_required()`, query the DB for user row and expense stats, pass all values to `render_template`.
- `templates/profile.html` — full template implementation.
- `static/css/style.css` — add `.profile-*` CSS classes at the bottom of the file (before any `@media` overrides if needed, otherwise append).

---

## Files to create

None.

---

## New dependencies

No new pip packages.

---

## Rules for implementation

- No SQLAlchemy or ORMs — use raw `sqlite3` via `get_db()`.
- Parameterised queries only — never format user-supplied values into SQL strings.
- Use CSS variables — never hardcode hex values in new styles.
- All templates extend `base.html`.
- Guard the route with the existing `login_required()` helper — call it at the very top of the route function and `return` its result if it is not `None`.
- Avatar initials: derive from the user's `name` in the template using Jinja (`name | upper` on the first character). For a one-word name use the first letter only; for two or more words use first letters of the first two words.
- `created_at` is stored as an ISO datetime string (`YYYY-MM-DD HH:MM:SS`). Slice to `YYYY-MM-DD` in the template (`user.created_at[:10]`) — no custom Jinja filter needed.
- `total_spent` must be formatted to 2 decimal places. Use Jinja's `"%.2f" | format(total_spent)` or `"{:.2f}".format(total_spent)` — do not use a custom filter.
- New CSS classes must use the `.profile-` prefix to avoid collisions with existing classes.
- Do not add a profile link to the navbar — the navbar is already session-aware; this step does not change `base.html`.

---

## Layout spec

The profile page uses a single centred column (max-width ~640 px), consistent with the auth pages. Structure top to bottom:

1. **Page header** (`.profile-header`) — warm paper background strip with page title "Your Profile" using `.terms-title` font style.
2. **Profile card** (`.profile-card`) — white card, `var(--radius-md)` corners, `var(--border)` border, standard card shadow. Contains:
   - **Avatar** (`.profile-avatar`) — large circle, `var(--accent)` background, white initials in `var(--font-display)` at ~2rem.
   - **User name** (`.profile-name`) — `var(--font-display)`, ~1.5rem, `var(--ink)`.
   - **Email** (`.profile-email`) — `0.9rem`, `var(--ink-muted)`.
   - **Member since** (`.profile-meta`) — small label + date, `var(--ink-faint)`.
3. **Stats row** (`.profile-stats`) — two side-by-side stat tiles inside the same card, separated by a `var(--border-soft)` divider, each showing a label and a number.
4. **Actions row** — a single `btn-ghost` anchor pointing to `url_for('logout')` labelled "Sign out".

---

## Definition of done

- [ ] `GET /profile` redirects to `/login` when no session exists.
- [ ] `GET /profile` renders the profile page for a logged-in user.
- [ ] The page displays the user's full name as stored in the DB.
- [ ] The page displays the user's email address.
- [ ] The avatar circle shows the correct initials derived from the name.
- [ ] The "Member since" date shows the account `created_at` date (YYYY-MM-DD).
- [ ] The stats row shows the correct total number of expenses for that user.
- [ ] The stats row shows the correct total amount spent (2 decimal places) for that user.
- [ ] The "Sign out" button navigates to `/logout` and ends the session.
- [ ] The page is visually consistent with the rest of Spendly — correct fonts, colours from CSS variables, no inline hex values.
- [ ] App starts without errors (`venv/bin/python3 app.py`).
- [ ] No existing tests are broken (`venv/bin/pytest`).
