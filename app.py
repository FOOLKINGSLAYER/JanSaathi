import os
import secrets
from functools import wraps
from hmac import compare_digest

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from ai_service import analyze_challenge
from database import (add_challenge, add_collaboration, add_user, all_challenges, all_organizations,
                      all_users, challenge_project, challenges_for_user, dashboard_metrics, delete_user,
                      get_challenge, get_demo_user_by_email, get_project, update_challenge_status,
                      update_user, user_count)

COLLABORATIONS = []


def load_local_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


load_local_env()
app = Flask(__name__)
app.config.update(SECRET_KEY=os.getenv("SECRET_KEY", "change-this-development-secret"), MAX_CONTENT_LENGTH=16 * 1024 * 1024)
ROLE_DASHBOARDS = {"citizen": "citizen_dashboard", "university": "university_dashboard", "industry": "industry_dashboard", "government": "government_dashboard", "admin": "admin_dashboard"}


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "info")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped_view


def role_required(role):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped_view(*args, **kwargs):
            if session.get("user", {}).get("role") != role:
                flash("This workspace is not available for your account.", "error")
                return redirect(url_for(ROLE_DASHBOARDS[session["user"]["role"]]))
            return view(*args, **kwargs)
        return wrapped_view
    return decorator


def valid_csrf():
    return bool(session.get("csrf_token")) and compare_digest(request.form.get("csrf_token", ""), session["csrf_token"])


@app.context_processor
def inject_globals():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    def nav_active(prefix, exact=False):
        path = request.path.rstrip("/") or "/"
        return path == prefix if exact else path.startswith(prefix)

    return {"current_user": session.get("user"), "session_user_id": session.get("user_id"), "csrf_token": session["csrf_token"], "metrics": dashboard_metrics(), "nav_active": nav_active}


@app.get("/")
def index():
    return render_template("index.html", featured_challenges=all_challenges()[:3])


@app.get("/about")
def about():
    return render_template("about.html")


@app.get("/how-it-works")
def how_it_works():
    return render_template("how_it_works.html")


@app.get("/impact")
def impact():
    return render_template("impact.html")


@app.get("/contact")
def contact():
    return render_template("contact.html")


@app.get("/search")
def search():
    query = request.args.get("q", "").strip()
    challenges = all_challenges()
    if query:
        term = query.lower()
        challenges = [challenge for challenge in challenges if term in " ".join([challenge.get("title", ""), challenge.get("description", ""), challenge.get("category", ""), challenge.get("location", ""), " ".join(challenge.get("keywords", []))]).lower()]
    return render_template("search.html", challenges=challenges, query=query)


@app.get("/challenges")
def challenges_directory():
    return redirect(url_for("search"))


@app.get("/help")
def help_page():
    return render_template("help.html")


@app.get("/accessibility")
def accessibility():
    return render_template("accessibility.html")


@app.get("/sitemap")
def sitemap():
    return render_template("sitemap.html")


@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", message="Page not found", detail="The page may have moved or the address may be incorrect."), 404


@app.errorhandler(500)
def server_error(error):
    return render_template("error.html", message="Something went wrong", detail="Please return to the JanSaathi home page and try again."), 500


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if not valid_csrf():
            flash("Your form session expired. Please try again.", "error")
            return render_template("login.html"), 400
        email, password = request.form.get("email", "").strip().lower(), request.form.get("password", "")
        user = get_demo_user_by_email(email)
        if not email or not password or user is None or not check_password_hash(user.password_hash, password):
            flash("We could not verify those details. Check your email and password.", "error")
            return render_template("login.html", email=email), 401
        session.clear()
        session["user_id"] = user.id
        session["user"] = {"name": user.name, "email": user.email, "role": user.role, "organization": user.organization}
        flash(f"Welcome back, {user.name}.", "success")
        return redirect(url_for(ROLE_DASHBOARDS[user.role]))
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if not valid_csrf():
            flash("Your form session expired. Please try again.", "error")
            return render_template("register.html"), 400
        password, confirmation = request.form.get("password", ""), request.form.get("confirm_password", "")
        if password != confirmation or len(password) < 8:
            flash("Use a matching password of at least 8 characters.", "error")
            return render_template("register.html", form=request.form), 400
        email = request.form.get("email", "").strip().lower()
        name = request.form.get("name", "").strip()
        role = request.form.get("role", "citizen")
        if not name or not email or role not in ROLE_DASHBOARDS or get_demo_user_by_email(email):
            flash("Enter a valid name and a new email address.", "error")
            return render_template("register.html", form=request.form), 400
        user = add_user(name, email, generate_password_hash(password), role, request.form.get("organization", "").strip())
        session.clear()
        session["user_id"] = user.id
        session["user"] = {"name": user.name, "email": user.email, "role": user.role, "organization": user.organization}
        flash("Your JanSaathi account is ready.", "success")
        return redirect(url_for(ROLE_DASHBOARDS[role]))
    return render_template("register.html")


@app.get("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.get("/citizen/dashboard")
@role_required("citizen")
def citizen_dashboard():
    submitted = challenges_for_user(session["user_id"])
    return render_template("citizen/dashboard.html", challenges=submitted, stats={"submitted": len(submitted) + 2, "review": 2, "accepted": 1, "progress": 1, "resolved": 1})


@app.route("/citizen/submit", methods=["GET", "POST"])
@role_required("citizen")
def submit_challenge():
    if request.method == "POST":
        if not valid_csrf():
            flash("Your form session expired. Please try again.", "error")
            return render_template("citizen/submit_challenge.html"), 400
        title, description, category, location = (request.form.get(field, "").strip() for field in ("title", "description", "category", "location"))
        if not title or not description or not category or not location:
            flash("Please complete the title, description, category, and location.", "error")
            return render_template("citizen/submit_challenge.html", form=request.form), 400
        analysis = analyze_challenge(title, description, category, location)
        challenge = add_challenge(title, description, category, location, session["user_id"], analysis)
        source = "Gemini" if analysis.get("source") == "gemini" else "local analysis" if analysis.get("source") == "local" else "saved analysis"
        flash(f"Challenge #{challenge['id']} submitted with {source}. A human review remains part of the process.", "success")
        return redirect(url_for("citizen_challenge_detail", challenge_id=challenge["id"]))
    return render_template("citizen/submit_challenge.html")


@app.get("/citizen/challenges")
@role_required("citizen")
def citizen_challenges():
    return render_template("citizen/challenges.html", challenges=challenges_for_user(session["user_id"]))


@app.get("/citizen/challenge/<int:challenge_id>")
@role_required("citizen")
def citizen_challenge_detail(challenge_id):
    challenge = get_challenge(challenge_id)
    if not challenge or challenge["submitted_by"] != session["user_id"]:
        return render_template("error.html", message="Challenge not found."), 404
    return render_template("citizen/challenge_detail.html", challenge=challenge, project=challenge_project(challenge_id))


@app.get("/university/dashboard")
@role_required("university")
def university_dashboard():
    return render_template("university/dashboard.html", challenges=all_challenges(), projects=[get_project(1)])


@app.get("/university/challenges")
@role_required("university")
def university_challenges():
    return render_template("university/challenges.html", challenges=all_challenges())


@app.get("/university/challenge/<int:challenge_id>")
@role_required("university")
def university_challenge_detail(challenge_id):
    challenge = get_challenge(challenge_id)
    if not challenge:
        return render_template("error.html", message="Challenge not found."), 404
    return render_template("university/challenge_detail.html", challenge=challenge)


@app.post("/university/challenge/<int:challenge_id>/accept")
@role_required("university")
def accept_challenge(challenge_id):
    if not valid_csrf():
        flash("Your form session expired. Please try again.", "error")
        return redirect(url_for("university_challenge_detail", challenge_id=challenge_id))
    challenge = get_challenge(challenge_id)
    if challenge:
        update_challenge_status(challenge_id, "ACCEPTED", "Project formation", "National Institute of Technology")
        flash("Challenge accepted. You can now create a project workspace.", "success")
    return redirect(url_for("university_challenge_detail", challenge_id=challenge_id))


@app.get("/university/project/<int:project_id>")
@role_required("university")
def university_project(project_id):
    project = get_project(project_id)
    if not project:
        return render_template("error.html", message="Project not found."), 404
    return render_template("university/project.html", project=project, challenge=get_challenge(project["challenge_id"]))


@app.get("/industry/dashboard")
@role_required("industry")
def industry_dashboard():
    return render_template("industry/dashboard.html", projects=[get_project(1)])


@app.get("/industry/opportunities")
@role_required("industry")
def industry_opportunities():
    return render_template("industry/opportunities.html", projects=[get_project(1)])


@app.get("/industry/opportunity/<int:project_id>")
@role_required("industry")
def industry_opportunity(project_id):
    project = get_project(project_id)
    if not project:
        return render_template("error.html", message="Opportunity not found."), 404
    return render_template("industry/opportunity_detail.html", project=project, challenge=get_challenge(project["challenge_id"]))


@app.post("/industry/opportunity/<int:project_id>/interest")
@role_required("industry")
def industry_interest(project_id):
    if not valid_csrf():
        flash("Your form session expired. Please try again.", "error")
        return redirect(url_for("industry_opportunity", project_id=project_id))
    add_collaboration(project_id, session["user"].get("organization", "Industry partner"), request.form.get("type", "Mentorship"))
    flash("Your collaboration interest has been sent to the university team.", "success")
    return redirect(url_for("industry_opportunity", project_id=project_id))


@app.get("/government/dashboard")
@role_required("government")
def government_dashboard():
    return render_template("government/dashboard.html", challenges=all_challenges(), projects=[get_project(1)])


@app.get("/government/challenges")
@role_required("government")
def government_challenges():
    return render_template("government/challenges.html", challenges=all_challenges())


@app.get("/government/analytics")
@role_required("government")
def government_analytics():
    return render_template("government/analytics.html", challenges=all_challenges(), projects=[get_project(1)])


@app.get("/admin/dashboard")
@role_required("admin")
def admin_dashboard():
    return render_template("admin/dashboard.html", challenges=all_challenges(), projects=[get_project(1)], users=all_users(), organizations=all_organizations())


@app.route("/admin/review", methods=["GET", "POST"])
@role_required("admin")
def admin_review():
    if request.method == "POST":
        if not valid_csrf():
            flash("Your form session expired. Please try again.", "error")
            return redirect(url_for("admin_review"))
        challenge_id = request.form.get("challenge_id", type=int)
        status = request.form.get("status", "UNDER_REVIEW")
        if challenge_id and status in {"UNDER_REVIEW", "ASSIGNED", "RESOLVED", "REJECTED"}:
            update_challenge_status(challenge_id, status, status.replace("_", " ").title())
            flash("Challenge status updated.", "success")
        return redirect(url_for("admin_review"))
    return render_template("admin/review.html", challenges=all_challenges())


@app.post("/admin/users/<int:user_id>/update")
@role_required("admin")
def admin_update_user(user_id):
    if not valid_csrf():
        flash("Your form session expired. Please try again.", "error")
        return redirect(url_for("admin_dashboard"))
    if user_id == session.get("user_id"):
        flash("The active admin account cannot be disabled or removed.", "error")
        return redirect(url_for("admin_dashboard"))
    action = request.form.get("action")
    if action == "delete":
        delete_user(user_id)
        flash("Account removed.", "success")
    else:
        update_user(user_id, role=request.form.get("role"), active=action != "disable")
        flash("Account permissions updated.", "success")
    return redirect(url_for("admin_dashboard"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG", "0") == "1")
