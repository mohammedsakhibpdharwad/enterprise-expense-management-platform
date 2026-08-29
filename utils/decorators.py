from functools import wraps

from flask import redirect, url_for
from flask_login import current_user, login_required

from utils.rbac import (
    ROLE_ADMIN,
    ROLE_EMPLOYEE,
    ROLE_FINANCE,
    ROLE_MANAGER,
    ROLE_SUPER,
)


def _home_for_user():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))

    if current_user.role == ROLE_EMPLOYEE:
        return redirect(url_for("employee.dashboard"))

    return redirect(url_for("admin.dashboard"))


def role_required(role):
    """Restrict a route to users with the given role."""

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped_view(*args, **kwargs):
            if current_user.role != role:
                return _home_for_user()
            return view_func(*args, **kwargs)

        return wrapped_view

    return decorator


def roles_required(*roles):
    """Restrict a route to any of the supplied roles."""

    allowed = set(roles)

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped_view(*args, **kwargs):
            if current_user.role not in allowed:
                return _home_for_user()
            return view_func(*args, **kwargs)

        return wrapped_view

    return decorator


admin_required = role_required(ROLE_ADMIN)
employee_required = role_required(ROLE_EMPLOYEE)
manager_required = role_required(ROLE_MANAGER)
finance_required = role_required(ROLE_FINANCE)
super_required = role_required(ROLE_SUPER)

reviewer_required = roles_required(
    ROLE_MANAGER,
    ROLE_FINANCE,
    ROLE_SUPER,
)