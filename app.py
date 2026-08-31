import os

from flask import Flask, flash, redirect, render_template, url_for
from flask_login import LoginManager, current_user
from werkzeug.exceptions import RequestEntityTooLarge

from config import Config
from models.user import User

from routes.admin import admin_bp
from routes.auth import auth_bp
from routes.employee import employee_bp
from routes.manager import manager_bp
from routes.finance import finance_bp
from routes.superadmin import superadmin_bp
from routes.approvals import approvals_bp
from routes.notifications import notifications_bp


login_manager = LoginManager()

login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id):
    try:
        return User.get_by_id(user_id)
    except RuntimeError:
        return None


def register_error_handlers(app):

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("errors/403.html"), 403


    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404


    @app.errorhandler(413)
    @app.errorhandler(RequestEntityTooLarge)
    def file_too_large(_error):

        flash(
            "Uploaded file exceeds the 5 MB limit.",
            "danger"
        )

        if not current_user.is_authenticated:
            return redirect(
                url_for("auth.login")
            )


        role = (
            current_user.role or ""
        ).strip().lower()


        if role == "employee":
            return redirect(
                url_for("employee.dashboard")
            )


        if role == "manager":
            return redirect(
                url_for("manager.dashboard")
            )


        if role == "finance_admin":
            return redirect(
                url_for("finance.dashboard")
            )


        if role in {"super_admin", "admin"}:
            return redirect(
                url_for("superadmin.dashboard")
            )


        return redirect(
            url_for("auth.login")
        )


    @app.errorhandler(500)
    def internal_error(_error):
        return render_template("errors/500.html"), 500


def create_app():
    """Application factory."""

    app = Flask(__name__)

    app.config.from_object(Config)


    os.makedirs(
        app.config["UPLOAD_FOLDER"],
        exist_ok=True
    )


    login_manager.init_app(app)

    register_error_handlers(app)


    # =========================================================
    # BLUEPRINTS
    # =========================================================

    app.register_blueprint(auth_bp)

    app.register_blueprint(admin_bp)

    app.register_blueprint(employee_bp)

    app.register_blueprint(manager_bp)

    app.register_blueprint(finance_bp)

    app.register_blueprint(superadmin_bp)

    app.register_blueprint(approvals_bp)

    app.register_blueprint(notifications_bp)


    # =========================================================
    # ROOT / HOME ROUTE
    # =========================================================

    @app.route("/")
    def index():

        # User is not logged in.
        if not current_user.is_authenticated:

            return redirect(
                url_for("auth.login")
            )


        # Normalize the role so accidental
        # whitespace/capitalization does not
        # break routing.
        role = (
            current_user.role or ""
        ).strip().lower()


        # Employee
        if role == "employee":

            return redirect(
                url_for("employee.dashboard")
            )


        # Manager
        if role == "manager":

            return redirect(
                url_for("manager.dashboard")
            )


        # Finance Admin
        if role == "finance_admin":

            return redirect(
                url_for("finance.dashboard")
            )


        # Super Admin / legacy Admin
        if role in {"super_admin", "admin"}:

            return redirect(
                url_for("superadmin.dashboard")
            )


        # Unknown role:
        # send the user back to login rather than
        # creating a redirect loop.
        return redirect(
            url_for("auth.login")
        )


    return app


if __name__ == "__main__":

    application = create_app()

    application.run(debug=True)