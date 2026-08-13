"""Flask route blueprints."""

from routes.admin import admin_bp
from routes.auth import auth_bp
from routes.employee import employee_bp

__all__ = ["auth_bp", "admin_bp", "employee_bp"]
