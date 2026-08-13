from functools import wraps

from flask import abort, redirect, url_for
from flask_login import current_user, login_required


def role_required(role):
    """Restrict a route to users with the given role."""

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped_view(*args, **kwargs):
            if current_user.role != role:
                if current_user.role == "admin":
                    return redirect(url_for("admin.dashboard"))
                if current_user.role == "employee":
                    return redirect(url_for("employee.dashboard"))
                abort(403)
            return view_func(*args, **kwargs)

        return wrapped_view

    return decorator


admin_required = role_required("admin")
employee_required = role_required("employee")
