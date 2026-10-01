from flask import Flask, render_template, request, redirect, jsonify, session
import sqlite3
import os
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.secret_key = "colonymind-ai-secret-key-change-later"

DATABASE = "database/colony.db"


# =========================
# DATABASE
# =========================

def get_db():
    os.makedirs("database", exist_ok=True)

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    return conn


def init_db():

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            location TEXT NOT NULL,
            status TEXT DEFAULT 'Pending'
        )
    """)

    # Priority migration
    columns = [
        row["name"]
        for row in conn.execute("PRAGMA table_info(issues)").fetchall()
    ]

    if "priority" not in columns:
        conn.execute("""
            ALTER TABLE issues
            ADD COLUMN priority TEXT DEFAULT 'Medium'
        """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'Resident'
        )
    """)

    conn.commit()
    conn.close()


# =========================
# LOGIN REQUIRED
# =========================

def login_required(route_function):

    @wraps(route_function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:
            return redirect("/login")

        return route_function(*args, **kwargs)

    return wrapper


# =========================
# HOME
# =========================

@app.route("/")
def home():
    return render_template("index.html")


# =========================
# SIGNUP
# =========================

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get(
            "confirm_password", ""
        )

        if not name or not email or not password:
            return render_template(
                "signup.html",
                error="Please fill in all fields."
            )

        if password != confirm_password:
            return render_template(
                "signup.html",
                error="Passwords do not match."
            )

        if len(password) < 6:
            return render_template(
                "signup.html",
                error="Password must contain at least 6 characters."
            )

        conn = get_db()

        existing_user = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if existing_user:

            conn.close()

            return render_template(
                "signup.html",
                error="An account with this email already exists."
            )

        hashed_password = generate_password_hash(password)

        conn.execute("""
            INSERT INTO users
            (name, email, password)
            VALUES (?, ?, ?)
        """, (
            name,
            email,
            hashed_password
        ))

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("signup.html")


# =========================
# LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if "user_id" in session:
        return redirect("/dashboard")

    if request.method == "POST":

        email = request.form.get(
            "email", ""
        ).strip().lower()

        password = request.form.get(
            "password", ""
        )

        conn = get_db()

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_role"] = user["role"]

            return redirect("/dashboard")

        return render_template(
            "login.html",
            error="Invalid email or password."
        )

    return render_template("login.html")


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
@login_required
def dashboard():

    conn = get_db()

    issues = conn.execute(
        "SELECT * FROM issues ORDER BY id DESC"
    ).fetchall()

    total = len(issues)

    pending = sum(
        1 for issue in issues
        if issue["status"] == "Pending"
    )

    progress = sum(
        1 for issue in issues
        if issue["status"] == "In Progress"
    )

    resolved = sum(
        1 for issue in issues
        if issue["status"] == "Resolved"
    )

    conn.close()

    return render_template(
        "dashboard.html",
        issues=issues,
        total=total,
        pending=pending,
        progress=progress,
        resolved=resolved
    )


# =========================
# REPORT ISSUE
# =========================


@app.route("/report", methods=["GET", "POST"])
@login_required
def report():

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()
        priority = request.form.get("priority", "Medium").strip()

        allowed_priorities = ["Low", "Medium", "High", "Critical"]

        if priority not in allowed_priorities:
            priority = "Medium"

        if title and description and location:

            conn = get_db()

            conn.execute("""
                INSERT INTO issues
                (title, description, location, priority)
                VALUES (?, ?, ?, ?)
            """, (
                title,
                description,
                location,
                priority
            ))

            conn.commit()
            conn.close()

        return redirect("/dashboard")

    return render_template("report.html")


# =========================
# UPDATE STATUS
# =========================

@app.route(
    "/update-status/<int:issue_id>",
    methods=["POST"]
)
@login_required
def update_status(issue_id):

    status = request.form.get("status")

    allowed_statuses = [
        "Pending",
        "In Progress",
        "Resolved"
    ]

    if status not in allowed_statuses:
        return redirect("/dashboard")

    conn = get_db()

    conn.execute(
        """
        UPDATE issues
        SET status = ?
        WHERE id = ?
        """,
        (status, issue_id)
    )

    conn.commit()
    conn.close()

    return redirect("/dashboard")


# =========================
# DELETE ISSUE
# =========================

@app.route(
    "/delete-issue/<int:issue_id>",
    methods=["POST"]
)
@login_required
def delete_issue(issue_id):

    conn = get_db()

    conn.execute(
        "DELETE FROM issues WHERE id = ?",
        (issue_id,)
    )

    conn.commit()
    conn.close()

    return redirect("/dashboard")


# =========================
# COMMUNITY
# =========================

@app.route("/community")
@login_required
def community():

    conn = get_db()

    issues = conn.execute(
        "SELECT * FROM issues ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return render_template(
        "community.html",
        issues=issues
    )


# =========================
# AI ASSISTANT PAGE
# =========================

@app.route("/ai-assistant")
@login_required
def ai_assistant():

    return render_template(
        "ai_assistant.html"
    )


# =========================
# AI ASSISTANT API
# =========================

@app.route(
    "/api/ai-assistant",
    methods=["POST"]
)
@login_required
def ai_assistant_api():

    data = request.get_json(
        silent=True
    ) or {}

    question = data.get(
        "question", ""
    ).strip().lower()

    if not question:

        return jsonify({
            "answer":
            "Please enter a question about your community."
        })

    conn = get_db()

    issues = conn.execute(
        "SELECT * FROM issues ORDER BY id DESC"
    ).fetchall()

    conn.close()

    total = len(issues)

    pending = sum(
        1 for issue in issues
        if issue["status"] == "Pending"
    )

    progress = sum(
        1 for issue in issues
        if issue["status"] == "In Progress"
    )

    resolved = sum(
        1 for issue in issues
        if issue["status"] == "Resolved"
    )

    if total == 0:

        return jsonify({
            "answer":
            "Your community currently has no reported issues yet."
        })

    if "pending" in question:

        pending_issues = [
            issue for issue in issues
            if issue["status"] == "Pending"
        ]

        if pending_issues:

            answer = (
                f"There are {pending} pending "
                "issues in your community.\n\n"
            )

            for issue in pending_issues[:5]:

                answer += (
                    f"• {issue['title']} "
                    f"— {issue['location']}\n"
                )

        else:

            answer = (
                "There are currently no pending issues."
            )

        return jsonify({"answer": answer})

    if (
        "in progress" in question
        or "ongoing" in question
        or "progress" in question
    ):

        answer = (
            f"There are {progress} issues currently "
            "in progress."
        )

        return jsonify({"answer": answer})

    if "resolved" in question:

        answer = (
            f"{resolved} issues have been resolved so far."
        )

        return jsonify({"answer": answer})

    if (
        "overview" in question
        or "summary" in question
        or "community status" in question
        or "how many issues" in question
    ):

        answer = (
            "Current community overview:\n\n"
            f"• Total issues: {total}\n"
            f"• Pending: {pending}\n"
            f"• In Progress: {progress}\n"
            f"• Resolved: {resolved}"
        )

        return jsonify({"answer": answer})

    if (
        "show" in question
        or "list" in question
        or "all issues" in question
    ):

        answer = (
            f"Your community has {total} "
            "reported issues:\n\n"
        )

        for issue in issues[:10]:

            answer += (
                f"• {issue['title']} "
                f"— {issue['location']} "
                f"— {issue['status']}\n"
            )

        return jsonify({"answer": answer})

    if (
        "location" in question
        or "area" in question
        or "block" in question
    ):

        location_counts = {}

        for issue in issues:

            location = issue["location"]

            location_counts[location] = (
                location_counts.get(location, 0) + 1
            )

        sorted_locations = sorted(
            location_counts.items(),
            key=lambda item: item[1],
            reverse=True
        )

        answer = "Issue distribution by location:\n\n"

        for location, count in sorted_locations[:5]:

            answer += (
                f"• {location}: "
                f"{count} issue(s)\n"
            )

        return jsonify({"answer": answer})

    return jsonify({
        "answer": (
            "I can analyze your community data.\n\n"
            "Try asking about pending issues, "
            "resolved issues, locations, or "
            "your community overview."
        )
    })


# =========================
# SMART INSIGHTS
# =========================

@app.route("/insights")
@login_required
def insights():

    conn = get_db()

    issues = conn.execute(
        "SELECT * FROM issues ORDER BY id DESC"
    ).fetchall()

    conn.close()

    total = len(issues)

    pending = sum(
        1 for issue in issues
        if issue["status"] == "Pending"
    )

    progress = sum(
        1 for issue in issues
        if issue["status"] == "In Progress"
    )

    resolved = sum(
        1 for issue in issues
        if issue["status"] == "Resolved"
    )

    if total:

        pending_percent = round(
            pending / total * 100
        )

        progress_percent = round(
            progress / total * 100
        )

        resolved_percent = round(
            resolved / total * 100
        )

        resolution_rate = round(
            resolved / total * 100
        )

    else:

        pending_percent = 0
        progress_percent = 0
        resolved_percent = 0
        resolution_rate = 0

    location_counts = {}

    for issue in issues:

        location = issue["location"].strip()

        if location:

            location_counts[location] = (
                location_counts.get(location, 0) + 1
            )

    locations = sorted(
        location_counts.items(),
        key=lambda item: item[1],
        reverse=True
    )[:5]

    if locations:

        max_count = locations[0][1]

        location_percentages = [
            round(count / max_count * 100)
            for location, count in locations
        ]

    else:

        location_percentages = []

    return render_template(
        "insights.html",
        total=total,
        pending=pending,
        progress=progress,
        resolved=resolved,
        pending_percent=pending_percent,
        progress_percent=progress_percent,
        resolved_percent=resolved_percent,
        resolution_rate=resolution_rate,
        locations=locations,
        location_percentages=location_percentages
    )



# =========================
# RUN
# =========================

if __name__ == "__main__":

    init_db()

    app.run(debug=True)