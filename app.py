from flask import Flask, render_template, request, redirect, session, flash, g
from db_config import get_connection
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from functools import wraps
from datetime import timedelta, date
import os, datetime, secrets

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "complaintportalkey_2025_secure_xK9#mP")
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=4)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = False

app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME", "campusportal.noreply@gmail.com")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD", "pahi pqrk ssyc uxdf")

mail = Mail(app)

ADMIN_INVITE_CODE = os.environ.get("ADMIN_INVITE_CODE", "CAMPUS_ADMIN_2025")
PER_PAGE = 20


@app.template_filter("fmt_date")
def fmt_date(value, fmt="%d %b %Y"):
    if value is None:
        return "\u2014"
    if isinstance(value, str):
        try:
            return datetime.datetime.strptime(value, "%Y-%m-%d").strftime(fmt)
        except ValueError:
            return value
    try:
        return value.strftime(fmt)
    except Exception:
        return str(value)


@app.template_filter("fmt_datetime")
def fmt_datetime(value, fmt="%d %b %Y, %I:%M %p"):
    if value is None:
        return "\u2014"
    if isinstance(value, str):
        return value
    try:
        return value.strftime(fmt)
    except Exception:
        return str(value)


def generate_csrf_token():
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(16)
    return session["_csrf_token"]


app.jinja_env.globals["csrf_token"] = generate_csrf_token


def check_csrf():
    token = session.get("_csrf_token")
    form_token = request.form.get("_csrf_token")
    if not token or not form_token or token != form_token:
        flash("Security validation failed. Please try again.", "error")
        return False
    return True


def refresh_unread_count(user_id):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM notifications WHERE user_id=%s AND is_read=0",
            (user_id,)
        )
        result = cursor.fetchone()
        session["_unread_count"] = result["cnt"] if result else 0
        cursor.close()
        conn.close()
    except Exception:
        session["_unread_count"] = 0


def send_email(to_email, subject, body):
    try:
        msg = Message(
            subject,
            sender=("Campus Portal", app.config["MAIL_USERNAME"]),
            recipients=[to_email]
        )
        msg.body = body
        mail.send(msg)
    except Exception as e:
        print("Email failed:", e)


def log_action(user_id, action):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO audit_logs (user_id, action) VALUES (%s,%s)",
            (user_id, action)
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print("Audit log failed:", e)


def ensure_tables():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                log_id INT NOT NULL AUTO_INCREMENT,
                user_id INT DEFAULT NULL,
                action TEXT NOT NULL,
                created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (log_id),
                KEY idx_user_id (user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """)
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print("Table setup warning:", e)


@app.context_processor
def inject_globals():
    return dict(
        unread_count=session.get("_unread_count", 0),
        session=session,
        today=date.today()
    )


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(e):
    return render_template("404.html", error_code=500,
                           error_msg="Internal Server Error"), 500


@app.route("/")
def home():
    return redirect("/login")


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect("/dashboard")

    if request.method == "POST":
        if not check_csrf():
            return redirect("/register")

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "student")
        staff_type = request.form.get("staff_type", None)
        invite_code = request.form.get("invite_code", "").strip()

        if not name or not email or not password:
            flash("All fields are required!", "error")
            return redirect("/register")

        if len(password) < 6:
            flash("Password must be at least 6 characters!", "error")
            return redirect("/register")

        if role == "admin" and invite_code != ADMIN_INVITE_CODE:
            flash("Invalid admin invite code!", "error")
            return redirect("/register")

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT user_id FROM users WHERE email=%s", (email,))
        if cursor.fetchone():
            flash("Email already registered!", "error")
            cursor.close()
            conn.close()
            return redirect("/register")

        hashed_password = generate_password_hash(password)
        final_staff_type = staff_type if role == "staff" else None

        cursor.execute(
            "INSERT INTO users (name, email, password, role, staff_type) VALUES (%s,%s,%s,%s,%s)",
            (name, email, hashed_password, role, final_staff_type)
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash("Registration successful! Please login.", "success")
        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect("/dashboard")

    if request.method == "POST":
        if not check_csrf():
            return redirect("/login")

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Email and password are required!", "error")
            return redirect("/login")

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session.permanent = True
            session["user_id"] = user["user_id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            session["staff_type"] = user.get("staff_type")

            refresh_unread_count(user["user_id"])
            log_action(user["user_id"], f"User '{user['name']}' logged in")
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect("/dashboard")

        flash("Invalid email or password!", "error")
        return redirect("/login")

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    role = session["role"]
    user_id = session["user_id"]
    stats = {}

    if role in ["student", "faculty"]:
        cursor.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(status='New') AS new,
                SUM(status='Assigned') AS assigned,
                SUM(status='In Progress') AS in_progress,
                SUM(status='Resolved') AS resolved,
                SUM(status='Closed') AS closed,
                SUM(sla_deadline < NOW() AND status NOT IN ('Closed','Resolved')) AS overdue
            FROM complaints WHERE user_id=%s
        """, (user_id,))
        row = cursor.fetchone()
        stats = {k: (v or 0) for k, v in row.items()}

    elif role == "admin":
        cursor.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(status='New') AS new,
                SUM(status='Assigned') AS assigned,
                SUM(status='In Progress') AS in_progress,
                SUM(status='Resolved') AS resolved,
                SUM(status='Closed') AS closed,
                SUM(sla_deadline < NOW() AND status NOT IN ('Closed','Resolved')) AS overdue
            FROM complaints
        """)
        row = cursor.fetchone()
        stats = {k: (v or 0) for k, v in row.items()}

    elif role == "staff":
        cursor.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(c.status='Assigned') AS assigned,
                SUM(c.status='In Progress') AS in_progress,
                SUM(c.status='Resolved') AS resolved,
                SUM(c.status='Closed') AS closed,
                SUM(c.sla_deadline < NOW() AND c.status NOT IN ('Closed','Resolved')) AS overdue
            FROM complaints c
            JOIN assignments a ON c.complaint_id = a.complaint_id
            WHERE a.staff_id=%s
        """, (user_id,))
        row = cursor.fetchone()
        stats = {k: (v or 0) for k, v in row.items()}
        stats["new"] = stats.get("assigned", 0)

    cursor.close()
    conn.close()

    return render_template("dashboard.html", name=session["name"], role=role, stats=stats)


@app.route("/submit_complaint", methods=["GET", "POST"])
def submit_complaint():
    if "user_id" not in session:
        return redirect("/login")

    if session["role"] not in ["student", "faculty"]:
        flash("Only Students and Faculty can raise complaints.", "error")
        return redirect("/dashboard")

    if request.method == "POST":
        if not check_csrf():
            return redirect("/submit_complaint")

        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        priority = request.form.get("priority", "Medium")
        room_number = request.form.get("room_number", "").strip() or None
        block_letter = request.form.get("block_letter", "").strip() or None
        hostel_type = request.form.get("hostel_type", None) or None
        building_name = request.form.get("building_name", "").strip() or None
        academic_room = request.form.get("academic_room", "").strip() or None

        if not category or not description or not priority:
            flash("Category, description, and priority are required!", "error")
            return redirect("/submit_complaint")

        if len(description) < 10:
            flash("Description must be at least 10 characters.", "error")
            return redirect("/submit_complaint")

        final_room = room_number if category == "Hostel" else (academic_room if category == "Academic Infrastructure" else None)

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """INSERT INTO complaints
               (user_id, category, description, priority, status,
                room_number, block_letter, hostel_type, building_name)
               VALUES (%s,%s,%s,%s,'New',%s,%s,%s,%s)""",
            (session["user_id"], category, description, priority,
             final_room, block_letter, hostel_type, building_name)
        )

        complaint_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()

        log_action(session["user_id"], f"Submitted complaint #{complaint_id} [{category}]")
        flash("Complaint submitted successfully!", "success")
        return redirect("/my_complaints")

    return render_template("submit_complaint.html")


@app.route("/my_complaints")
def my_complaints():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT *,
        CASE WHEN sla_deadline < NOW() AND status NOT IN ('Closed','Resolved') THEN 1 ELSE 0 END AS overdue
        FROM complaints
        WHERE user_id=%s
        ORDER BY created_at DESC
    """, (session["user_id"],))

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
        SELECT c.*, u.name AS raised_by, u.role AS user_role,
        CASE WHEN c.sla_deadline < NOW() AND c.status NOT IN ('Closed','Resolved') THEN 1 ELSE 0 END AS overdue
        FROM complaints c
        JOIN users u ON c.user_id = u.user_id
        WHERE c.complaint_id=%s
    """, (complaint_id,))

    complaint = cursor.fetchone()
    cursor.close()
    conn.close()

    if not complaint:
        flash("Complaint not found!", "error")
        return redirect("/dashboard")

    role = session["role"]
    user_id = session["user_id"]

    if role in ["student", "faculty"] and complaint["user_id"] != user_id:
        flash("Access denied!", "error")
        return redirect("/dashboard")

    if role == "staff":
        conn2 = get_connection()
        cur2 = conn2.cursor(dictionary=True)
        cur2.execute(
            "SELECT assignment_id FROM assignments WHERE complaint_id=%s AND staff_id=%s",
            (complaint_id, user_id)
        )
        if not cur2.fetchone():
            flash("Access denied!", "error")
            cur2.close()
            conn2.close()
            return redirect("/staff_panel")
        cur2.close()
        conn2.close()

    return render_template("complaint_details.html", complaint=complaint)


@app.route("/admin_panel")
def admin_panel():
    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "admin":
        flash("Access Denied! Admin only.", "error")
        return redirect("/dashboard")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    status_filter = request.args.get("status", "")
    search_q = request.args.get("q", "").strip()
    page = max(1, int(request.args.get("page", 1)))

    where_clauses = []
    params = []

    if status_filter:
        where_clauses.append("c.status=%s")
        params.append(status_filter)

    if search_q:
        where_clauses.append("(c.category LIKE %s OR u.name LIKE %s OR c.description LIKE %s)")
        like = f"%{search_q}%"
        params.extend([like, like, like])

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    count_query = f"""
        SELECT COUNT(*) AS cnt FROM complaints c
        JOIN users u ON c.user_id = u.user_id {where_sql}
    """
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()["cnt"]
    total_pages = max(1, (total_count + PER_PAGE - 1) // PER_PAGE)
    page = min(page, total_pages)
    offset = (page - 1) * PER_PAGE

    main_query = f"""
        SELECT c.*, u.name AS raised_by, u.role AS user_role,
        CASE WHEN sla_deadline < NOW() AND c.status NOT IN ('Closed','Resolved') THEN 1 ELSE 0 END AS overdue
        FROM complaints c
        JOIN users u ON c.user_id = u.user_id
        {where_sql}
        ORDER BY c.created_at DESC
        LIMIT %s OFFSET %s
    """
    cursor.execute(main_query, params + [PER_PAGE, offset])
    complaints = cursor.fetchall()

    cursor.execute("SELECT user_id, name, staff_type FROM users WHERE role='staff' ORDER BY name")
    staff_list = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "admin_panel.html",
        complaints=complaints,
        staff_list=staff_list,
        status_filter=status_filter,
        search_q=search_q,
        page=page,
        total_pages=total_pages,
        total_count=total_count,
        now=date.today()
    )


@app.route("/assign_complaint/<int:complaint_id>", methods=["POST"])
def assign_complaint(complaint_id):
    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "admin":
        flash("Only Admin can assign complaints!", "error")
        return redirect("/dashboard")

    if not check_csrf():
        return redirect("/admin_panel")

    staff_id = request.form.get("staff_id")
    deadline = request.form.get("deadline")

    if not staff_id or not deadline:
        flash("Staff and deadline are required!", "error")
        return redirect("/admin_panel")

    try:
        deadline_date = datetime.datetime.strptime(deadline, "%Y-%m-%d").date()
        if deadline_date < date.today():
            flash("SLA deadline cannot be in the past!", "error")
            return redirect("/admin_panel")
    except ValueError:
        flash("Invalid deadline date format!", "error")
        return redirect("/admin_panel")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT status FROM complaints WHERE complaint_id=%s", (complaint_id,))
    complaint = cursor.fetchone()

    if not complaint:
        flash("Complaint not found!", "error")
        cursor.close()
        conn.close()
        return redirect("/admin_panel")

    cur_status = complaint["status"]
    if cur_status not in ("New", "Assigned"):
        flash("Cannot assign a complaint at this stage!", "error")
        cursor.close()
        conn.close()
        return redirect("/admin_panel")

    cursor.execute("SELECT email, name FROM users WHERE user_id=%s AND role='staff'", (staff_id,))
    staff = cursor.fetchone()
    if not staff:
        flash("Invalid staff member selected!", "error")
        cursor.close()
        conn.close()
        return redirect("/admin_panel")

    if cur_status == "New":
        cursor.execute(
            "INSERT INTO assignments (complaint_id, staff_id) VALUES (%s,%s)",
            (complaint_id, staff_id)
        )
    else:
        cursor.execute(
            "UPDATE assignments SET staff_id=%s, assigned_at=NOW() WHERE complaint_id=%s",
            (staff_id, complaint_id)
        )

    cursor.execute(
        "UPDATE complaints SET status='Assigned', sla_deadline=%s WHERE complaint_id=%s",
        (deadline, complaint_id)
    )

    cursor.execute(
        "INSERT INTO notifications (user_id, message) VALUES (%s,%s)",
        (staff_id, f"You have been assigned Complaint #{complaint_id}. Deadline: {deadline}")
    )

    action_word = "Re-assigned" if cur_status == "Assigned" else "Assigned"
    log_action(session["user_id"], f"{action_word} complaint #{complaint_id} to '{staff['name']}'")

    conn.commit()
    cursor.close()
    conn.close()

    send_email(
        staff["email"],
        f"Complaint #{complaint_id} Assigned to You",
        f"You have been assigned Complaint #{complaint_id}.\nDeadline: {deadline}\n\nLog in to view details."
    )

    flash(f"Complaint #{complaint_id} {action_word.lower()} to {staff['name']}!", "success")
    return redirect("/admin_panel")


@app.route("/staff_panel")
def staff_panel():
    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "staff":
        flash("Access Denied! Staff only.", "error")
        return redirect("/dashboard")

    status_filter = request.args.get("status", "")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT c.complaint_id, c.category, c.priority, c.status, c.sla_deadline,
               c.description, c.remarks, c.room_number, c.building_name, a.assigned_at,
               CASE WHEN c.sla_deadline < NOW() AND c.status NOT IN ('Closed','Resolved') THEN 1 ELSE 0 END AS overdue
        FROM complaints c
        JOIN assignments a ON c.complaint_id = a.complaint_id
        WHERE a.staff_id=%s
    """
    params = [session["user_id"]]

    if status_filter:
        query += " AND c.status=%s"
        params.append(status_filter)

    query += " ORDER BY a.assigned_at DESC"

    cursor.execute(query, params)
    assigned_complaints = cursor.fetchall()
    cursor.close()
    conn.close()

    valid_transitions = {
        "Assigned": ["In Progress"],
        "In Progress": ["Resolved"],
        "Resolved": ["Closed"]
    }

    return render_template(
        "staff_panel.html",
        assigned_complaints=assigned_complaints,
        valid_transitions=valid_transitions,
        status_filter=status_filter
    )


@app.route("/update_status/<int:complaint_id>", methods=["POST"])
def update_status(complaint_id):
    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "staff":
        flash("Only Staff can update complaint status!", "error")
        return redirect("/dashboard")

    if not check_csrf():
        return redirect("/staff_panel")

    new_status = request.form.get("status", "").strip()
    remarks = request.form.get("remarks", "").strip()

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT c.status, c.user_id AS owner_id, a.staff_id
        FROM complaints c
        JOIN assignments a ON c.complaint_id = a.complaint_id
        WHERE c.complaint_id=%s AND a.staff_id=%s
    """, (complaint_id, session["user_id"]))

    record = cursor.fetchone()

    if not record:
        flash("Complaint not found or not assigned to you!", "error")
        cursor.close()
        conn.close()
        return redirect("/staff_panel")

    current_status = record["status"]
    owner_id = record["owner_id"]

    if current_status == "Closed":
        flash("Cannot modify a closed complaint!", "error")
        cursor.close()
        conn.close()
        return redirect("/staff_panel")

    valid = {
        "Assigned": ["In Progress"],
        "In Progress": ["Resolved"],
        "Resolved": ["Closed"]
    }

    if new_status not in valid.get(current_status, []):
        flash(f"Invalid status transition: {current_status} to {new_status}", "error")
        cursor.close()
        conn.close()
        return redirect("/staff_panel")

    cursor.execute(
        "UPDATE complaints SET status=%s, remarks=%s WHERE complaint_id=%s",
        (new_status, remarks, complaint_id)
    )

    cursor.execute(
        "INSERT INTO notifications (user_id, message) VALUES (%s, %s)",
        (owner_id, f"Your Complaint #{complaint_id} status updated to '{new_status}'")
    )

    cursor.execute("SELECT email FROM users WHERE user_id=%s", (owner_id,))
    owner = cursor.fetchone()
    owner_email = owner["email"] if owner else None

    log_action(session["user_id"], f"Updated complaint #{complaint_id}: {current_status} to {new_status}")

    conn.commit()
    cursor.close()
    conn.close()

    if owner_email:
        send_email(
            owner_email,
            "Complaint Status Updated",
            f"Your Complaint #{complaint_id} has been updated to '{new_status}'.\n\nRemarks: {remarks}"
        )

    flash(f"Complaint #{complaint_id} updated to '{new_status}'!", "success")
    return redirect("/staff_panel")


@app.route("/reports")
def reports():
    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "admin":
        flash("Access Denied! Admin only.", "error")
        return redirect("/dashboard")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(status='New') AS new_count,
            SUM(status='Assigned') AS assigned_count,
            SUM(status='In Progress') AS in_progress_count,
            SUM(status='Resolved') AS resolved_count,
            SUM(status='Closed') AS closed_count,
            SUM(sla_deadline < NOW() AND status NOT IN ('Closed','Resolved')) AS overdue_count
        FROM complaints
    """)
    summary = cursor.fetchone()
    summary = {k: (v or 0) for k, v in summary.items()}

    cursor.execute("SELECT status, COUNT(*) AS count FROM complaints GROUP BY status")
    status_data = cursor.fetchall()

    cursor.execute("SELECT category, COUNT(*) AS count FROM complaints GROUP BY category ORDER BY count DESC")
    category_data = cursor.fetchall()

    cursor.execute("SELECT priority, COUNT(*) AS count FROM complaints GROUP BY priority")
    priority_data = cursor.fetchall()

    cursor.execute("""
        SELECT DATE_FORMAT(created_at, '%Y-%m') AS month,
               DATE_FORMAT(created_at, '%b %Y') AS label,
               COUNT(*) AS count
        FROM complaints
        WHERE created_at >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
        GROUP BY DATE_FORMAT(created_at, '%Y-%m'), DATE_FORMAT(created_at, '%b %Y')
        ORDER BY month ASC
    """)
    monthly_data = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "reports.html",
        summary=summary,
        status_data=status_data,
        category_data=category_data,
        priority_data=priority_data,
        monthly_data=monthly_data
    )


@app.route("/audit_logs")
def audit_logs():
    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "admin":
        flash("Access Denied! Admin only.", "error")
        return redirect("/dashboard")

    page = max(1, int(request.args.get("page", 1)))
    per_page = 50

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS cnt FROM audit_logs")
    total_count = cursor.fetchone()["cnt"]
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    page = min(page, total_pages)
    offset = (page - 1) * per_page

    cursor.execute("""
        SELECT al.log_id, al.action, al.created_at,
               u.name AS user_name, u.role AS user_role
        FROM audit_logs al
        LEFT JOIN users u ON al.user_id = u.user_id
        ORDER BY al.created_at DESC
        LIMIT %s OFFSET %s
    """, (per_page, offset))
    logs = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "audit_logs.html",
        logs=logs,
        page=page,
        total_pages=total_pages,
        total_count=total_count
    )


@app.route("/notifications")
def view_notifications():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM notifications WHERE user_id=%s ORDER BY created_at DESC",
        (session["user_id"],)
    )
    notes = cursor.fetchall()

    cursor.execute(
        "UPDATE notifications SET is_read=1 WHERE user_id=%s",
        (session["user_id"],)
    )
    conn.commit()
    cursor.close()
    conn.close()

    session["_unread_count"] = 0

    return render_template("notifications.html", notes=notes)


@app.route("/backup")
def backup():
    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "admin":
        flash("Access Denied! Admin only.", "error")
        return redirect("/dashboard")

    backup_dir = os.path.join(os.path.dirname(__file__), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    filename = f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    filepath = os.path.join(backup_dir, filename)

    db_pass = os.environ.get("DB_PASSWORD", "system")
    cmd = f'mysqldump -u root -p{db_pass} complaint_portal > "{filepath}"'
    exit_code = os.system(cmd)

    if exit_code == 0:
        log_action(session["user_id"], f"Database backup created: {filename}")
        flash("Database backup created successfully!", "success")
    else:
        flash("Backup failed. Ensure mysqldump is available in your PATH.", "error")

    return redirect("/dashboard")


@app.route("/logout")
def logout():
    if "user_id" in session:
        log_action(session["user_id"], f"User '{session.get('name')}' logged out")
    session.clear()
    flash("You have been logged out successfully.", "success")
    return redirect("/login")


ensure_tables()

if __name__ == "__main__":
    app.run(debug=True)