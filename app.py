from flask import Flask, render_template, request, redirect, url_for, flash, session
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
        "SELECT amount, category, date, description FROM expenses "
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


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
