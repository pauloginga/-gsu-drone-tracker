import os
from datetime import datetime, date

from flask import Flask, render_template, redirect, url_for, flash, request, send_file, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm

# ---------------------------------------------------------------------------
# App & config
# ---------------------------------------------------------------------------
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'drone_tracker.db')}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["ADMIN_SETUP_CODE"] = os.environ.get("ADMIN_SETUP_CODE", "20262027")

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to continue."
login_manager.login_message_category = "error"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    service_number = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="pilot")  # 'pilot' or 'admin'
    is_approved = db.Column(db.Boolean, default=False)
    date_registered = db.Column(db.DateTime, default=datetime.utcnow)

    missions = db.relationship("Mission", backref="pilot", lazy=True,
                                cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Mission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pilot_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    mission_date = db.Column(db.Date, nullable=False, default=date.today)
    take_off_time = db.Column(db.String(10), nullable=False)   # stored as "HH:MM"
    landing_time = db.Column(db.String(10), nullable=False)    # stored as "HH:MM"
    duration_minutes = db.Column(db.Integer, nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    admin_remarks = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def duration_display(self):
        h, m = divmod(self.duration_minutes, 60)
        return f"{h}h {m}m"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def calc_duration_minutes(take_off, landing):
    """take_off / landing are 'HH:MM' strings. Handles missions crossing midnight."""
    t_off = datetime.strptime(take_off, "%H:%M")
    t_land = datetime.strptime(landing, "%H:%M")
    delta = (t_land - t_off).total_seconds() / 60
    if delta < 0:
        delta += 24 * 60  # landed after midnight
    return int(delta)


def admin_required(func):
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            abort(403)
        return func(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("pilot_dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        service_number = request.form.get("service_number", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not all([full_name, service_number, email, password]):
            flash("Please fill in all fields.", "error")
            return redirect(url_for("register"))

        if password != confirm:
            flash("Passwords do not match.", "error")
            return redirect(url_for("register"))

        if User.query.filter_by(service_number=service_number).first():
            flash("That service number is already registered.", "error")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("That email is already registered.", "error")
            return redirect(url_for("register"))

        user = User(
            full_name=full_name,
            service_number=service_number,
            email=email,
            role="pilot",
            is_approved=False,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("Registration submitted. An administrator must approve your account "
              "before you can log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/admin/register", methods=["GET", "POST"])
def admin_register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        service_number = request.form.get("service_number", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        setup_code = request.form.get("setup_code", "")

        if not all([full_name, service_number, email, password, setup_code]):
            flash("Please fill in all fields.", "error")
            return redirect(url_for("admin_register"))

        if setup_code != app.config["ADMIN_SETUP_CODE"]:
            flash("Incorrect admin setup code.", "error")
            return redirect(url_for("admin_register"))

        if password != confirm:
            flash("Passwords do not match.", "error")
            return redirect(url_for("admin_register"))

        if User.query.filter_by(service_number=service_number).first():
            flash("That service number is already registered.", "error")
            return redirect(url_for("admin_register"))

        if User.query.filter_by(email=email).first():
            flash("That email is already registered.", "error")
            return redirect(url_for("admin_register"))

        admin = User(
            full_name=full_name,
            service_number=service_number,
            email=email,
            role="admin",
            is_approved=True,
        )
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()

        flash("Admin account created. You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("admin_register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter(
            (User.email == identifier) | (User.service_number == identifier)
        ).first()

        if not user or not user.check_password(password):
            flash("Invalid credentials.", "error")
            return redirect(url_for("login"))

        if not user.is_approved:
            flash("Your account is awaiting admin approval.", "error")
            return redirect(url_for("login"))

        login_user(user)
        if user.role == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("pilot_dashboard"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Pilot routes
# ---------------------------------------------------------------------------
@app.route("/pilot/dashboard", methods=["GET", "POST"])
@login_required
def pilot_dashboard():
    if current_user.role != "pilot":
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        mission_date_str = request.form.get("mission_date")
        take_off = request.form.get("take_off_time")
        landing = request.form.get("landing_time")
        remarks = request.form.get("remarks", "").strip()

        if not all([mission_date_str, take_off, landing]):
            flash("Please fill in date, take-off time, and landing time.", "error")
            return redirect(url_for("pilot_dashboard"))

        try:
            mission_date = datetime.strptime(mission_date_str, "%Y-%m-%d").date()
            duration = calc_duration_minutes(take_off, landing)
        except ValueError:
            flash("Invalid date or time format.", "error")
            return redirect(url_for("pilot_dashboard"))

        mission = Mission(
            pilot_id=current_user.id,
            mission_date=mission_date,
            take_off_time=take_off,
            landing_time=landing,
            duration_minutes=duration,
            remarks=remarks,
        )
        db.session.add(mission)
        db.session.commit()
        flash("Mission attendance logged.", "success")
        return redirect(url_for("pilot_dashboard"))

    my_missions = (
        Mission.query.filter_by(pilot_id=current_user.id)
        .order_by(Mission.mission_date.desc(), Mission.id.desc())
        .all()
    )
    return render_template("pilot_dashboard.html", missions=my_missions, today=date.today().isoformat())


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------
@app.route("/admin/dashboard")
@login_required
@admin_required
def admin_dashboard():
    pending_users = User.query.filter_by(role="pilot", is_approved=False).all()
    all_users = User.query.order_by(User.role.desc(), User.full_name).all()
    all_missions = (
        Mission.query.order_by(Mission.mission_date.desc(), Mission.id.desc()).all()
    )
    return render_template(
        "admin_dashboard.html",
        pending_users=pending_users,
        all_users=all_users,
        missions=all_missions,
    )


@app.route("/admin/approve/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_approved = True
    db.session.commit()
    flash(f"{user.full_name} approved.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/reject/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def reject_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash("Registration rejected and removed.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/delete_user/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("You can't delete your own account while logged in as it.", "error")
        return redirect(url_for("admin_dashboard"))

    if user.role == "admin":
        remaining_admins = User.query.filter_by(role="admin").count()
        if remaining_admins <= 1:
            flash("You can't delete the last remaining admin account.", "error")
            return redirect(url_for("admin_dashboard"))

    db.session.delete(user)  # cascades to delete their missions too
    db.session.commit()
    flash(f"{user.full_name} has been deleted.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/mission_remarks/<int:mission_id>", methods=["POST"])
@login_required
@admin_required
def mission_remarks(mission_id):
    mission = Mission.query.get_or_404(mission_id)
    mission.admin_remarks = request.form.get("admin_remarks", "").strip()
    db.session.commit()
    flash("Remarks saved.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/clear_attendance", methods=["POST"])
@login_required
@admin_required
def clear_attendance():
    Mission.query.delete()
    db.session.commit()
    flash("Attendance sheet cleared.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/export_pdf")
@login_required
@admin_required
def export_pdf():
    missions = (
        Mission.query.order_by(Mission.mission_date.desc(), Mission.id.desc()).all()
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    elements = []

    title = Paragraph("GSU/CIS Drone Tracker — Attendance Report", styles["Title"])
    subtitle = Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]
    )
    elements += [title, subtitle, Spacer(1, 12)]

    data = [["Pilot", "Service No.", "Date", "Take-off", "Landing", "Duration", "Remarks", "Admin Remarks"]]
    for m in missions:
        data.append([
            m.pilot.full_name,
            m.pilot.service_number,
            m.mission_date.strftime("%Y-%m-%d"),
            m.take_off_time,
            m.landing_time,
            m.duration_display(),
            m.remarks or "",
            m.admin_remarks or "",
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8c1a1a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5e6e6")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"gsu_drone_attendance_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
        mimetype="application/pdf",
    )


# ---------------------------------------------------------------------------
# CLI command to bootstrap the first admin account
# ---------------------------------------------------------------------------
@app.cli.command("create-admin")
def create_admin():
    """Usage: flask create-admin"""
    full_name = input("Full name: ").strip()
    service_number = input("Service number: ").strip()
    email = input("Email: ").strip().lower()
    password = input("Password: ").strip()

    if User.query.filter_by(email=email).first():
        print("A user with that email already exists.")
        return

    admin = User(
        full_name=full_name,
        service_number=service_number,
        email=email,
        role="admin",
        is_approved=True,
    )
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    print(f"Admin account created for {full_name}.")


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
