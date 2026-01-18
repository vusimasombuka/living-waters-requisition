from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)

# =========================
# CONFIGURATION
# =========================
app.secret_key = "lwbc_dev_secret"

MINOR_LIMIT = 1000  # R1000 approval threshold

USERS = {
    "treasurer": "treasurer123",
    "pastor": "pastor123"
}

DB_NAME = "requisitions.db"

# =========================
# DATABASE HELPER
# =========================
def get_db():
    return sqlite3.connect(DB_NAME, timeout=10)

# =========================
# ROUTES
# =========================
@app.route("/", methods=["GET", "POST"])
def submit():
    if request.method == "POST":
        data = request.form

        conn = get_db()
        c = conn.cursor()

        c.execute("""
            INSERT INTO requisitions
            (date, type, department, requestor, purpose, amount, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d"),
            data["type"],
            data["department"],
            data["requestor"],
            data["purpose"],
            float(data["amount"]),
            "Pending"
        ))

        conn.commit()
        conn.close()

        return "Requisition submitted successfully"

    return render_template("form.html", church="Living Waters Bible Church")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = request.form["role"]
        password = request.form["password"]

        if role in USERS and USERS[role] == password:
            session["role"] = role
            return redirect("/admin")

        return "Invalid credentials"

    return render_template("login.html", church="Living Waters Bible Church")


@app.route("/admin")
def admin():
    role = session.get("role")
    if role not in ["treasurer", "pastor"]:
        return redirect("/login")

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM requisitions ORDER BY date DESC")
    rows = c.fetchall()
    conn.close()

    return render_template(
        "admin.html",
        rows=rows,
        role=role,
        limit=MINOR_LIMIT,
        church="Living Waters Bible Church"
    )


@app.route("/approve/<int:req_id>")
def approve(req_id):
    role = session.get("role")
    if role not in ["treasurer", "pastor"]:
        return redirect("/login")

    conn = get_db()
    c = conn.cursor()

    # Get amount
    c.execute("SELECT amount FROM requisitions WHERE id=?", (req_id,))
    result = c.fetchone()

    if not result:
        conn.close()
        return "Requisition not found"

    amount = float(result[0])

    # Approval rules
    if amount <= MINOR_LIMIT and role == "treasurer":
        approver = "Treasurer"
    elif amount > MINOR_LIMIT and role == "pastor":
        approver = "Senior Pastor"
    else:
        conn.close()
        return "You are not authorised to approve this request"

    # Update requisition
    c.execute("""
        UPDATE requisitions
        SET status='Approved', approved_by=?
        WHERE id=?
    """, (approver, req_id))

    # Audit log (SAME CONNECTION)
    c.execute("""
        INSERT INTO audit_log
        (requisition_id, action, performed_by, role, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (
        req_id,
        "Approved",
        approver,
        role,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()

    return redirect("/admin")


@app.route("/reject/<int:req_id>")
def reject(req_id):
    role = session.get("role")
    if role not in ["treasurer", "pastor"]:
        return redirect("/login")

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        UPDATE requisitions
        SET status='Rejected'
        WHERE id=?
    """, (req_id,))

    c.execute("""
        INSERT INTO audit_log
        (requisition_id, action, performed_by, role, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (
        req_id,
        "Rejected",
        role.capitalize(),
        role,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()

    return redirect("/admin")

@app.route("/audit")
def audit():
    role = session.get("role")
    if role not in ["treasurer", "pastor"]:
        return redirect("/login")

    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT requisition_id, action, performed_by, role, timestamp
        FROM audit_log
        ORDER BY timestamp DESC
    """)
    rows = c.fetchall()
    conn.close()

    return render_template(
        "audit.html",
        rows=rows,
        church="Living Waters Bible Church"
    )
@app.route("/dashboard/<month>")
def dashboard(month):
    role = session.get("role")
    if role not in ["treasurer", "pastor"]:
        return redirect("/login")

    conn = get_db()
    c = conn.cursor()

    # Total count & total requested
    c.execute("""
        SELECT COUNT(*), SUM(amount)
        FROM requisitions
        WHERE date LIKE ?
    """, (f"{month}%",))
    total_count, total_requested = c.fetchone()

    # Total approved
    c.execute("""
        SELECT SUM(amount)
        FROM requisitions
        WHERE status='Approved' AND date LIKE ?
    """, (f"{month}%",))
    total_approved = c.fetchone()[0]

    # Per-department totals
    c.execute("""
        SELECT department, SUM(amount)
        FROM requisitions
        WHERE date LIKE ?
        GROUP BY department
    """, (f"{month}%",))
    by_department = c.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        month=month,
        total_count=total_count or 0,
        total_requested=total_requested or 0,
        total_approved=total_approved or 0,
        by_department=by_department,
        church="Living Waters Bible Church"
    )

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

