from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db, init_db, seed_db

app = Flask(__name__)
app.secret_key = "spendly-dev-secret"

with app.app_context():
    init_db()
    seed_db()


def login_required():
    if not session.get('user_id'):
        return redirect(url_for('login'))


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get('user_id'):
        return redirect(url_for('landing'))

    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        if not name:
            return render_template("register.html", error="Name is required.")
        if not email:
            return render_template("register.html", error="Email is required.")
        if len(password) < 8:
            return render_template("register.html", error="Password must be at least 8 characters.")
        if password != confirm:
            return render_template("register.html", error="Passwords do not match.")

        conn = get_db()
        existing = conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            conn.close()
            return render_template("register.html", error="An account with that email already exists.")

        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        conn.commit()
        conn.close()

        flash("Account created! Please sign in.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get('user_id'):
        return redirect(url_for('landing'))

    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute("SELECT id, name, password_hash FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if not user or not check_password_hash(user["password_hash"], password):
            return render_template("login.html", error="Invalid email or password.")

        session['user_id']   = user["id"]
        session['user_name'] = user["name"]
        return redirect(url_for('profile'))

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
    return redirect(url_for('landing'))


@app.route("/profile")
def profile():
    guard = login_required()
    if guard:
        return guard

    conn = get_db()
    user = conn.execute(
        "SELECT id, name, email, created_at FROM users WHERE id = ?",
        (session['user_id'],)
    ).fetchone()
    stats = conn.execute(
        "SELECT COUNT(*) AS expense_count, COALESCE(SUM(amount), 0) AS total_spent "
        "FROM expenses WHERE user_id = ?",
        (session['user_id'],)
    ).fetchone()
    categories = conn.execute(
        "SELECT category, COALESCE(SUM(amount), 0) AS total "
        "FROM expenses WHERE user_id = ? GROUP BY category ORDER BY total DESC",
        (session['user_id'],)
    ).fetchall()
    expenses_list = conn.execute(
        "SELECT id, amount, category, date, description FROM expenses "
        "WHERE user_id = ? ORDER BY date DESC",
        (session['user_id'],)
    ).fetchall()
    conn.close()

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        categories=[dict(r) for r in categories],
        expenses_list=[dict(r) for r in expenses_list],
    )


VALID_CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    guard = login_required()
    if guard:
        return guard

    if request.method == "POST":
        amount_str  = request.form.get("amount", "").strip()
        category    = request.form.get("category", "").strip()
        date_str    = request.form.get("date", "").strip()
        description = request.form.get("description", "").strip()

        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
        except ValueError:
            return render_template("add-expense.html", error="Amount must be a positive number.", categories=VALID_CATEGORIES)

        if category not in VALID_CATEGORIES:
            return render_template("add-expense.html", error="Please select a valid category.", categories=VALID_CATEGORIES)

        try:
            datetime.date.fromisoformat(date_str)
        except ValueError:
            return render_template("add-expense.html", error="Date must be a valid YYYY-MM-DD date.", categories=VALID_CATEGORIES)

        conn = get_db()
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (session['user_id'], amount, category, date_str, description or None),
        )
        conn.commit()
        conn.close()

        flash("Expense added successfully.")
        return redirect(url_for('profile'))

    return render_template("add-expense.html", categories=VALID_CATEGORIES)


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    guard = login_required()
    if guard:
        return guard

    conn = get_db()
    expense = conn.execute(
        "SELECT * FROM expenses WHERE id = ? AND user_id = ?",
        (id, session['user_id'])
    ).fetchone()
    if not expense:
        conn.close()
        abort(404)

    if request.method == "POST":
        amount_str  = request.form.get("amount", "").strip()
        category    = request.form.get("category", "").strip()
        date_str    = request.form.get("date", "").strip()
        description = request.form.get("description", "").strip()

        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
        except ValueError:
            conn.close()
            return render_template("edit-expense.html", expense=expense, error="Amount must be a positive number.", categories=VALID_CATEGORIES)

        if category not in VALID_CATEGORIES:
            conn.close()
            return render_template("edit-expense.html", expense=expense, error="Please select a valid category.", categories=VALID_CATEGORIES)

        try:
            datetime.date.fromisoformat(date_str)
        except ValueError:
            conn.close()
            return render_template("edit-expense.html", expense=expense, error="Date must be a valid YYYY-MM-DD date.", categories=VALID_CATEGORIES)

        conn.execute(
            "UPDATE expenses SET amount=?, category=?, date=?, description=? WHERE id=? AND user_id=?",
            (amount, category, date_str, description or None, id, session['user_id']),
        )
        conn.commit()
        conn.close()

        flash("Expense updated.")
        return redirect(url_for('profile'))

    conn.close()
    return render_template("edit-expense.html", expense=expense, categories=VALID_CATEGORIES)


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense(id):
    guard = login_required()
    if guard:
        return guard

    conn = get_db()
    result = conn.execute(
        "DELETE FROM expenses WHERE id = ? AND user_id = ?",
        (id, session['user_id'])
    )
    conn.commit()
    conn.close()

    if result.rowcount == 0:
        abort(404)

    flash("Expense deleted.")
    return redirect(url_for('profile'))


@app.route("/expenses/stats")
def expense_stats():
    guard = login_required()
    if guard:
        return guard

    conn = get_db()
    stats = conn.execute(
        """
        SELECT
            COUNT(*)                          AS expense_count,
            COALESCE(SUM(amount), 0)          AS total_spent,
            COALESCE(AVG(amount), 0)          AS avg_amount,
            COALESCE(MAX(amount), 0)          AS max_amount,
            COALESCE(MIN(amount), 0)          AS min_amount,
            COALESCE(SUM(CASE WHEN strftime('%Y-%m', date) = strftime('%Y-%m', 'now') THEN amount END), 0)
                                              AS this_month_total,
            COUNT(CASE WHEN strftime('%Y-%m', date) = strftime('%Y-%m', 'now') THEN 1 END)
                                              AS this_month_count
        FROM expenses
        WHERE user_id = ?
        """,
        (session['user_id'],)
    ).fetchone()
    conn.close()

    return render_template("expenses-stats.html", stats=dict(stats))


@app.route("/expenses/categories")
def expense_categories():
    guard = login_required()
    if guard:
        return guard

    conn = get_db()
    rows = conn.execute(
        """
        SELECT
            category,
            COUNT(*)                       AS count,
            COALESCE(SUM(amount), 0)       AS total,
            COALESCE(AVG(amount), 0)       AS avg_amount,
            COALESCE(MAX(amount), 0)       AS max_amount,
            MAX(date)                      AS last_date
        FROM expenses
        WHERE user_id = ?
        GROUP BY category
        ORDER BY total DESC
        """,
        (session['user_id'],)
    ).fetchall()

    grand_total = sum(r['total'] for r in rows)
    categories = []
    for r in rows:
        d = dict(r)
        d['pct'] = round((d['total'] / grand_total * 100), 1) if grand_total > 0 else 0
        categories.append(d)

    conn.close()
    return render_template("expenses-categories.html", categories=categories, grand_total=grand_total)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
