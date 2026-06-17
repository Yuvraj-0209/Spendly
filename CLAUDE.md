# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

Dependencies must be installed into the local venv — do not use the system Python:

```bash
venv/bin/python3 -m pip install -r requirements.txt   # first time setup
venv/bin/python3 app.py                                # runs on http://localhost:5001
```

## Running tests

```bash
venv/bin/pytest                        # all tests
venv/bin/pytest tests/test_foo.py      # single file
venv/bin/pytest -k "test_name"         # single test by name
```

## Architecture

**Single-file entry point.** `app.py` contains the Flask app object and every route. There is no blueprint or module split — all routes live here.

**Database layer (not yet implemented).** `database/db.py` is a stub. It should expose three functions: `get_db()` (returns a SQLite connection with `row_factory` and foreign keys enabled), `init_db()` (creates tables via `CREATE TABLE IF NOT EXISTS`), and `seed_db()` (inserts sample dev data). The database file is `expense_tracker.db` (gitignored). The `database/` directory is a Python package (`__init__.py` present).

**Template inheritance.** All pages extend `templates/base.html`, which provides the navbar, footer, and two extension points beyond `{% block content %}`:
- `{% block head %}` — for page-specific CSS links (used by `landing.html` to load `landing.css`)
- `{% block scripts %}` — for page-specific JS (used by `landing.html` for the YouTube modal)

**Two-stylesheet pattern.** `static/css/style.css` is the global stylesheet and defines all design tokens (CSS variables), the navbar, footer, auth pages, and the features/CTA sections on the landing page. `static/css/landing.css` is loaded only by `landing.html` and overrides the `.hero` class (resetting it from a two-column grid to a centered single-column layout). All classes introduced in `landing.css` use an `lp-` prefix to avoid conflicts with `style.css`.

**Placeholder routes.** `/logout`, `/profile`, `/expenses/add`, `/expenses/<id>/edit`, and `/expenses/<id>/delete` return plain strings — they are intentional stubs for students to implement.

## Design tokens

All colours, fonts, spacing radii, and max-widths are defined as CSS variables at the top of `style.css`. Use these variables (e.g. `var(--accent)`, `var(--ink-muted)`, `var(--radius-md)`) when adding new styles rather than hardcoding values.

## Legal pages

`/terms` and `/privacy` share CSS classes defined at the bottom of `style.css` (`.terms-header`, `.terms-page`, `.terms-body`, etc.). New legal-style content pages should reuse this same structure.
 