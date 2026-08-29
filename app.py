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
        flash("Uploaded file exceeds the 5 MB limit.", "danger")
        if current_user.is_authenticated and current_user.role == "employee":
            return redirect(url_for("employee.dashboard"))
        if current_user.is_authenticated and current_user.role == "admin":
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("auth.login"))

    @app.errorhandler(500)
    def internal_error(_error):
        return render_template("errors/500.html"), 500


def create_app():
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    login_manager.init_app(app)
    register_error_handlers(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(manager_bp)
    app.register_blueprint(finance_bp)
    app.register_blueprint(superadmin_bp)
    app.register_blueprint(approvals_bp)
    app.register_blueprint(notifications_bp)

    @app.route("/")
    def index():
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if current_user.role == "admin":
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("employee.dashboard"))

    return app

if __name__ == "__main__":
    application = create_app()
    application.run(debug=True)
