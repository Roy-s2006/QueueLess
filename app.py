
import os
from functools import wraps
from datetime import datetime

from flask import (
    Flask, render_template, redirect, url_for,
    request, flash, abort, jsonify
)
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import select

from config import Config
from models import db, User, Service, Counter, QueueToken


# --------------------------------------------------
# APPLICATION CONFIGURATION
# --------------------------------------------------

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# --------------------------------------------------
# ADMIN ACCESS CONTROL
# --------------------------------------------------

def admin_required(function):
    @wraps(function)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash("Administrator access required.", "danger")
            return redirect(url_for("user_dashboard"))
        return function(*args, **kwargs)

    return decorated_function


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

@app.route("/")
def index():
    services = Service.query.filter_by(is_active=True).all()
    return render_template("index.html", services=services)


# --------------------------------------------------
# USER REGISTRATION
# --------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if current_user.is_authenticated:
        return redirect(url_for("admin_dashboard" if current_user.is_admin else "user_dashboard"))

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email or not password:
            flash("Please fill in all required fields.", "danger")

        elif len(password) < 8:
            flash("Password must contain at least 8 characters.", "danger")

        elif password != confirm_password:
            flash("Passwords do not match.", "danger")

        elif User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "danger")

        else:
            user = User(
                name=name,
                email=email,
                password=generate_password_hash(password),
                is_admin=False
            )

            db.session.add(user)
            db.session.commit()

            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))

    return render_template("register.html")


# --------------------------------------------------
# USER LOGIN
# --------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("admin_dashboard" if current_user.is_admin else "user_dashboard"))

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):

            login_user(user)

            flash("Welcome back!", "success")

            if user.is_admin:
                return redirect(url_for("admin_dashboard"))

            return redirect(url_for("user_dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


# --------------------------------------------------
# USER DASHBOARD
# --------------------------------------------------

@app.route("/dashboard")
@login_required
def user_dashboard():

    if current_user.is_admin:
        return redirect(url_for("admin_dashboard"))

    services = Service.query.filter_by(is_active=True).all()

    tokens = QueueToken.query.filter_by(
        user_id=current_user.id
    ).order_by(QueueToken.created_at.desc()).all()

    return render_template(
        "user_dashboard.html",
        services=services,
        tokens=tokens
    )


# --------------------------------------------------
# GENERATE QUEUE TOKEN
# --------------------------------------------------

@app.route("/generate-token/<int:service_id>", methods=["POST"])
@login_required
def generate_token(service_id):

    if current_user.is_admin:
        abort(403)

    service = db.session.get(Service, service_id)

    if not service or not service.is_active:
        flash("This service is currently unavailable.", "danger")
        return redirect(url_for("user_dashboard"))

    existing_token = QueueToken.query.filter(
        QueueToken.user_id == current_user.id,
        QueueToken.service_id == service.id,
        QueueToken.status.in_(["Waiting", "Serving"])
    ).first()

    if existing_token:
        flash("You already have an active token for this service.", "warning")
        return redirect(url_for("token_details", token_id=existing_token.id))

    try:
        # Lock the service row and re-read its latest values, so two
        # people can never receive the same token number.
        locked_service = db.session.execute(
            select(Service)
            .where(Service.id == service.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).scalar_one()

        token_number = locked_service.next_token_number

        token = QueueToken(
            token_number=token_number,
            user_id=current_user.id,
            service_id=locked_service.id,
            status="Waiting"
        )

        locked_service.next_token_number += 1

        db.session.add(token)
        db.session.commit()

        flash("Your queue token has been generated!", "success")
        return redirect(url_for("token_details", token_id=token.id))

    except Exception:
        db.session.rollback()
        app.logger.exception("Token generation failed")
        flash("Unable to generate your token. Please try again.", "danger")
        return redirect(url_for("user_dashboard"))

# --------------------------------------------------
# TOKEN DETAILS
# --------------------------------------------------

@app.route("/token/<int:token_id>")
@login_required
def token_details(token_id):

    token = db.session.get(QueueToken, token_id)

    if not token:
        abort(404)

    if not current_user.is_admin and token.user_id != current_user.id:
        abort(403)

    waiting_ahead = QueueToken.query.filter(
        QueueToken.service_id == token.service_id,
        QueueToken.status == "Waiting",
        QueueToken.token_number < token.token_number
    ).count()

    current_serving = QueueToken.query.filter_by(
        service_id=token.service_id,
        status="Serving"
    ).order_by(QueueToken.token_number.asc()).first()

    average_time = token.service.average_service_time or 5

    estimated_wait = (
        waiting_ahead * average_time
        if token.status == "Waiting"
        else 0
    )

    return render_template(
        "token.html",
        token=token,
        waiting_ahead=waiting_ahead,
        current_serving=current_serving,
        estimated_wait=estimated_wait
    )


# --------------------------------------------------
# CANCEL USER TOKEN
# --------------------------------------------------

@app.route("/cancel-token/<int:token_id>", methods=["POST"])
@login_required
def cancel_token(token_id):

    token = db.session.get(QueueToken, token_id)

    if not token:
        abort(404)

    if not current_user.is_admin and token.user_id != current_user.id:
        abort(403)

    if token.status != "Waiting":
        flash("Only waiting tokens can be cancelled.", "warning")
    else:
        token.status = "Cancelled"
        db.session.commit()
        flash("Your token has been cancelled.", "success")

    return redirect(
        url_for("token_details", token_id=token.id)
        if not current_user.is_admin
        else url_for("admin_dashboard")
    )


# --------------------------------------------------
# ADMIN DASHBOARD
# --------------------------------------------------

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():

    total_tokens = QueueToken.query.count()

    waiting_tokens = QueueToken.query.filter_by(
        status="Waiting"
    ).count()

    serving_tokens = QueueToken.query.filter_by(
        status="Serving"
    ).count()

    completed_tokens = QueueToken.query.filter_by(
        status="Completed"
    ).count()

    counters = Counter.query.filter_by(is_active=True).all()

    tokens = QueueToken.query.order_by(
        QueueToken.created_at.desc()
    ).limit(100).all()

    return render_template(
        "admin_dashboard.html",
        total_tokens=total_tokens,
        waiting_tokens=waiting_tokens,
        serving_tokens=serving_tokens,
        completed_tokens=completed_tokens,
        counters=counters,
        tokens=tokens
    )


# --------------------------------------------------
# ADMIN DASHBOARD API (FOR LIVE UPDATES)
# --------------------------------------------------

@app.route("/api/admin/dashboard")
@admin_required
def admin_dashboard_api():
    """Return live statistics, counters, waiting queue and recent activity."""

    total_tokens = QueueToken.query.count()

    waiting_tokens = QueueToken.query.filter_by(
        status="Waiting"
    ).count()

    serving_tokens = QueueToken.query.filter_by(
        status="Serving"
    ).count()

    completed_tokens = QueueToken.query.filter_by(
        status="Completed"
    ).count()

    # Active counters and their currently serving tokens
    counters = Counter.query.filter_by(is_active=True).all()

    counter_data = []

    for counter in counters:
        serving_token = QueueToken.query.filter_by(
            counter_id=counter.id,
            status="Serving"
        ).first()

        counter_data.append({
            "id": counter.id,
            "name": counter.name,
            "service_name": counter.service.name,
            "serving_token_id": (
                serving_token.id if serving_token else None
            ),
            "serving_token_number": (
                serving_token.token_number if serving_token else None
            ),
            "customer_name": (
                serving_token.user.name if serving_token else None
            )
        })

    # Waiting queue
    waiting = QueueToken.query.filter_by(
        status="Waiting"
    ).order_by(
        QueueToken.created_at.asc()
    ).limit(50).all()

    waiting_data = [
        {
            "id": token.id,
            "token_number": token.token_number,
            "customer_name": token.user.name,
            "service_name": token.service.name,
            "created_at": token.created_at.strftime("%d %b %Y, %I:%M %p")
        }
        for token in waiting
    ]

    # Recent queue activity
    recent_tokens = QueueToken.query.order_by(
        QueueToken.created_at.desc()
    ).limit(100).all()

    recent_data = [
        {
            "id": token.id,
            "token_number": token.token_number,
            "customer_name": token.user.name,
            "service_name": token.service.name,
            "counter_name": (
                token.counter.name if token.counter else "—"
            ),
            "created_at": token.created_at.strftime("%d %b %Y, %I:%M %p"),
            "status": token.status
        }
        for token in recent_tokens
    ]

    return jsonify({
        "stats": {
            "total": total_tokens,
            "waiting": waiting_tokens,
            "serving": serving_tokens,
            "completed": completed_tokens
        },
        "counters": counter_data,
        "waiting_queue": waiting_data,
        "recent_activity": recent_data
    })



# --------------------------------------------------
# MANAGE SERVICES AND COUNTERS
# --------------------------------------------------

@app.route("/admin/services", methods=["GET", "POST"])
@admin_required
def manage_services():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        average_time = request.form.get("average_service_time", "5")

        try:
            average_time = int(average_time)
        except ValueError:
            average_time = 0

        if not name or average_time < 1:
            flash("Enter a valid service name and service duration.", "danger")
        elif Service.query.filter_by(name=name).first():
            flash("This service already exists.", "warning")
        else:
            service = Service(
                name=name,
                description=description,
                average_service_time=average_time
            )

            db.session.add(service)
            db.session.commit()

            flash("Service added successfully!", "success")

        return redirect(url_for("manage_services"))

    services = Service.query.order_by(Service.id.desc()).all()

    return render_template(
        "manage_services.html",
        services=services
    )


@app.route("/admin/add-counter/<int:service_id>", methods=["POST"])
@admin_required
def add_counter(service_id):

    service = db.session.get(Service, service_id)

    if not service or not service.is_active:
        flash("Service not found or inactive.", "danger")
        return redirect(url_for("manage_services"))

    name = request.form.get("name", "").strip()

    if not name:
        flash("Counter name is required.", "danger")
    else:
        counter = Counter(
            name=name,
            service_id=service.id
        )
        db.session.add(counter)
        db.session.commit()
        flash("Counter created successfully!", "success")

    return redirect(url_for("manage_services"))


# --------------------------------------------------
# ADMIN: CALL NEXT TOKEN
# --------------------------------------------------

@app.route("/admin/call-next/<int:counter_id>", methods=["POST"])
@admin_required
def call_next(counter_id):

    counter = db.session.get(Counter, counter_id)

    if not counter or not counter.is_active:
        flash("Counter is unavailable.", "danger")
        return redirect(url_for("admin_dashboard"))

    current_token = QueueToken.query.filter_by(
        counter_id=counter.id,
        status="Serving"
    ).first()

    if current_token:
        flash("Complete the current token before calling the next one.", "warning")
        return redirect(url_for("admin_dashboard"))

    next_token = QueueToken.query.filter_by(
        service_id=counter.service_id,
        status="Waiting"
    ).order_by(
        QueueToken.token_number.asc()
    ).first()

    if not next_token:
        flash("No waiting tokens for this service.", "info")
    else:
        next_token.status = "Serving"
        next_token.counter_id = counter.id
        next_token.called_at = datetime.utcnow()

        db.session.commit()
        flash(f"Token #{next_token.token_number} is now serving.", "success")

    return redirect(url_for("admin_dashboard"))


# --------------------------------------------------
# ADMIN: COMPLETE CURRENT TOKEN
# --------------------------------------------------

@app.route("/admin/complete/<int:token_id>", methods=["POST"])
@admin_required
def complete_token(token_id):

    token = db.session.get(QueueToken, token_id)

    if not token:
        abort(404)

    if token.status != "Serving":
        flash("Only a serving token can be completed.", "warning")
    else:
        token.status = "Completed"
        token.completed_at = datetime.utcnow()
        db.session.commit()
        flash("Token completed successfully!", "success")

    return redirect(url_for("admin_dashboard"))


# --------------------------------------------------
# ADMIN: SKIP OR CANCEL TOKEN
# --------------------------------------------------

@app.route("/admin/skip/<int:token_id>", methods=["POST"])
@admin_required
def skip_token(token_id):

    token = db.session.get(QueueToken, token_id)

    if not token:
        abort(404)

    if token.status not in ["Waiting", "Serving"]:
        flash("This token cannot be skipped.", "warning")
    else:
        token.status = "Cancelled"
        db.session.commit()
        flash(f"Token #{token.token_number} has been skipped.", "success")

    return redirect(url_for("admin_dashboard"))


# --------------------------------------------------
# QUEUE STATUS API (FOR LIVE UPDATES)
# --------------------------------------------------

@app.route("/api/token/<int:token_id>")
@login_required
def token_status_api(token_id):
    """Return the latest queue information for a token (used by live updates)."""

    token = db.session.get(QueueToken, token_id)

    if not token:
        abort(404)

    # Users may only view live information for their own tokens.
    if not current_user.is_admin and token.user_id != current_user.id:
        abort(403)

    waiting_ahead = QueueToken.query.filter(
        QueueToken.service_id == token.service_id,
        QueueToken.status == "Waiting",
        QueueToken.token_number < token.token_number
    ).count()

    current_serving = QueueToken.query.filter_by(
        service_id=token.service_id,
        status="Serving"
    ).order_by(QueueToken.token_number.asc()).first()

    average_time = token.service.average_service_time or 5
    estimated_wait = (
        waiting_ahead * average_time
        if token.status == "Waiting"
        else 0
    )

    return jsonify({
        "token_id": token.id,
        "token_number": token.token_number,
        "status": token.status,
        "waiting_ahead": waiting_ahead,
        "current_serving": (
            current_serving.token_number if current_serving else None
        ),
        "estimated_wait": estimated_wait,
        "counter_name": token.counter.name if token.counter else None
    })


# --------------------------------------------------
# DATABASE INITIALIZATION
# --------------------------------------------------

def initialize_database():

    os.makedirs(
        os.path.join(app.root_path, "instance"),
        exist_ok=True
    )

    with app.app_context():

        db.create_all()

        admin_email = os.environ.get(
            "QUEUELESS_ADMIN_EMAIL",
            "admin@queueless.com"
        ).strip().lower()

        admin_password = os.environ.get(
            "QUEUELESS_ADMIN_PASSWORD",
            "Admin@123"
        )

        admin = User.query.filter_by(email=admin_email).first()

        if not admin:
            admin = User(
                name="QueueLess Admin",
                email=admin_email,
                password=generate_password_hash(admin_password),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()


# --------------------------------------------------
# RUN APPLICATION
# --------------------------------------------------


if __name__ == "__main__":
    initialize_database()

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )

