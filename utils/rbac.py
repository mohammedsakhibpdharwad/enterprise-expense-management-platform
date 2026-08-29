"""Server-side role helpers. Legacy role `admin` remains the original admin role."""

ROLE_EMPLOYEE = "employee"
ROLE_ADMIN = "admin"
ROLE_LEGACY_ADMIN = ROLE_ADMIN
ROLE_MANAGER = "manager"
ROLE_FINANCE = "finance_admin"
ROLE_SUPER = "super_admin"

VALID_ROLES = (ROLE_EMPLOYEE, ROLE_ADMIN, ROLE_MANAGER, ROLE_FINANCE, ROLE_SUPER)


def normalize_role(role):
    return role or ROLE_EMPLOYEE


def dashboard_endpoint(role):
    mapped = normalize_role(role)

    if mapped == ROLE_SUPER:
        return "superadmin.dashboard"

    if mapped == ROLE_FINANCE:
        return "finance.dashboard"

    if mapped == ROLE_MANAGER:
        return "manager.dashboard"

    if mapped == ROLE_ADMIN:
        return "admin.dashboard"

    return "employee.dashboard"