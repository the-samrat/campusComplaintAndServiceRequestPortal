from flask import Flask, render_template, request, redirect, session
from db_config import get_connection
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = "complaintportalkey"

app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "campusportal.noreply@gmail.com"
app.config["MAIL_PASSWORD"] = "pahi pqrk ssyc uxdf"

mail = Mail(app)

def send_email(to_email, subject, body):
    try:
        msg = Message(
            subject,
            sender=("Campus Portal - No Reply", app.config["MAIL_USERNAME"]),
            recipients=[to_email]
        )
        msg.body = body
        mail.send(msg)
        print("✅ Email sent successfully to:", to_email)

    except Exception as e:
        print("❌ Email sending failed:", e)


@app.route("/")
def home():
    return redirect("/login")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]

        hashed_password = generate_password_hash(password)

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO users (name, email, password, role) VALUES (%s,%s,%s,%s)",
            (name, email, hashed_password, role)
        )

        conn.commit()
        cursor.close()
        conn.close()

        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["user_id"]
            session["name"] = user["name"]
            session["role"] = user["role"]

            return redirect("/dashboard")

        return "❌ Invalid Credentials!"

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    return render_template("dashboard.html",
                           name=session["name"],
                           role=session["role"])

@app.route("/submit_complaint", methods=["GET", "POST"])
def submit_complaint():
    if "user_id" not in session:
        return redirect("/login")

    if session["role"] not in ["student", "faculty"]:
        return "❌ Only Students and Faculty can raise complaints."

    if request.method == "POST":
        category = request.form["category"]
        description = request.form["description"]
        priority = request.form["priority"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO complaints (user_id, category, description, priority) VALUES (%s,%s,%s,%s)",
            (session["user_id"], category, description, priority)
        )

        conn.commit()
        cursor.close()
        conn.close()

        return redirect("/my_complaints")

    return render_template("submit_complaint.html")

@app.route("/my_complaints")
def my_complaints():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM complaints WHERE user_id=%s ORDER BY created_at DESC",
        (session["user_id"],)
    )

    complaints = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("my_complaints.html", complaints=complaints)

@app.route("/complaint/<int:complaint_id>")
def complaint_details(complaint_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT c.*, u.name AS raised_by, u.role AS user_role
        FROM complaints c
        JOIN users u ON c.user_id = u.user_id
        WHERE c.complaint_id=%s
    """, (complaint_id,))

    complaint = cursor.fetchone()

    cursor.close()
    conn.close()

    if not complaint:
        return "❌ Complaint not found!"

    return render_template("complaint_details.html", complaint=complaint)

@app.route("/admin_panel")
def admin_panel():
    if "user_id" not in session or session["role"] != "admin":
        return "❌ Access Denied!"

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT c.*, u.name AS raised_by, u.role AS user_role
        FROM complaints c
        JOIN users u ON c.user_id = u.user_id
        ORDER BY c.created_at DESC
    """)
    complaints = cursor.fetchall()

    cursor.execute("SELECT * FROM users WHERE role='staff'")
    staff_list = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("admin_panel.html",
                           complaints=complaints,
                           staff_list=staff_list)

@app.route("/assign_complaint/<int:complaint_id>", methods=["POST"])
def assign_complaint(complaint_id):
    if "user_id" not in session or session["role"] != "admin":
        return "❌ Only Admin can assign!"

    staff_id = request.form["staff_id"]
    deadline = request.form["deadline"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT email FROM users WHERE user_id=%s", (staff_id,))
    staff_email = cursor.fetchone()["email"]

    cursor.execute(
        "INSERT INTO assignments (complaint_id, staff_id) VALUES (%s,%s)",
        (complaint_id, staff_id)
    )

    cursor.execute("""
        UPDATE complaints
        SET status='Assigned', sla_deadline=%s
        WHERE complaint_id=%s
    """, (deadline, complaint_id))

    cursor.execute("""
        INSERT INTO notifications (user_id, message)
        VALUES (%s, %s)
    """, (staff_id, f"You have been assigned Complaint ID {complaint_id}"))

    conn.commit()
    cursor.close()
    conn.close()

    send_email(
        staff_email,
        "New Complaint Assigned",
        f"Complaint ID {complaint_id} has been assigned to you.\nDeadline: {deadline}"
    )

    return redirect("/admin_panel")

@app.route("/staff_panel")
def staff_panel():
    if "user_id" not in session or session["role"] != "staff":
        return "❌ Access Denied!"

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT c.complaint_id, c.category, c.priority,
               c.status, a.assigned_at
        FROM complaints c
        JOIN assignments a ON c.complaint_id = a.complaint_id
        WHERE a.staff_id = %s
    """, (session["user_id"],))

    assigned_complaints = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("staff_panel.html",
                           assigned_complaints=assigned_complaints)

@app.route("/update_status/<int:complaint_id>", methods=["POST"])
def update_status(complaint_id):
    if "user_id" not in session or session["role"] != "staff":
        return "❌ Only Staff can update!"

    new_status = request.form["status"]
    remarks = request.form["remarks"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        UPDATE complaints
        SET status=%s, remarks=%s
        WHERE complaint_id=%s
    """, (new_status, remarks, complaint_id))

    cursor.execute("""
        SELECT u.email
        FROM complaints c
        JOIN users u ON c.user_id = u.user_id
        WHERE c.complaint_id=%s
    """, (complaint_id,))
    owner_email = cursor.fetchone()["email"]

    cursor.execute("""
        INSERT INTO notifications (user_id, message)
        SELECT user_id, %s FROM complaints WHERE complaint_id=%s
    """, (f"Your complaint {complaint_id} status updated to {new_status}", complaint_id))

    conn.commit()
    cursor.close()
    conn.close()

    send_email(
        owner_email,
        "Complaint Status Updated",
        f"Your complaint ID {complaint_id} is now: {new_status}\nRemarks: {remarks}"
    )

    return redirect("/staff_panel")

@app.route("/notifications")
def view_notifications():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM notifications
        WHERE user_id=%s
        ORDER BY created_at DESC
    """, (session["user_id"],))

    notes = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("notifications.html", notes=notes)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)
