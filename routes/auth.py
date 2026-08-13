from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_user, logout_user, current_user

from models.user import User

auth_bp = Blueprint("auth", __name__)


def _dashboard_for_role(role):
    if role == "admin":
        return url_for("admin.dashboard")
    return url_for("employee.dashboard")


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(_dashboard_for_role(current_user.role))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        role = request.form.get("role", "employee")
        department = request.form.get("department", "").strip()

        errors = []
        if not name:
            errors.append("Name is required.")
        if not email:
            errors.append("Email is required.")
        if not password:
            errors.append("Password is required.")
        elif len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm_password:
            errors.append("Passwords do not match.")
        if role not in ("admin", "employee"):
            errors.append("Invalid role selected.")
        if not department:
            errors.append("Department is required.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("auth/signup.html", form=request.form)

        if User.get_by_email(email):
            flash("An account with that email already exists.", "danger")
            return render_template("auth/signup.html", form=request.form)

        user = User.create(name, email, password, role, department)
        login_user(user)
        flash("Account created successfully. Welcome!", "success")
        return redirect(_dashboard_for_role(user.role))

    return render_template("auth/signup.html", form={})


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(_dashboard_for_role(current_user.role))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        user = User.get_by_email(email)
        if not user or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html", email=email)

        login_user(user, remember=remember)
        flash(f"Welcome back, {user.name}!", "success")
        next_page = request.args.get("next")
        if next_page:
            return redirect(next_page)
        return redirect(_dashboard_for_role(user.role))

    return render_template("auth/login.html", email="")


@auth_bp.route("/logout")
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
