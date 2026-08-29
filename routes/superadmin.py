from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from werkzeug.security import generate_password_hash

from models.database import execute, fetch_all, fetch_one
from models.department import Department
from models.expense import Expense
from models.user import User
from services import audit
from utils.decorators import super_required
from utils.http import page_number, pager
from utils.rbac import VALID_ROLES, ROLE_LEGACY_ADMIN

superadmin_bp = Blueprint("superadmin", __name__, url_prefix="/admin")


@superadmin_bp.route("/system")
@super_required
def dashboard():
    stats = Expense.overview_stats()
    users_total = fetch_one("SELECT COUNT(*) AS c FROM users")["c"]
    return render_template(
        "superadmin/dashboard.html",
        stats=stats,
        users_total=users_total,
        activity=audit.recent_activity(15),
        departments=Department.all(),
    )


@superadmin_bp.route("/employees")
@super_required
def employees():
    page = page_number()
    rows, total = User.search(
        q=request.args.get("q"),
        department_id=request.args.get("department_id") or None,
        role=request.args.get("role") or None,
        is_active=request.args.get("is_active"),
        page=page,
    )
    return render_template(
        "superadmin/employees.html",
        employees=rows,
        paging=pager(total, page),
        departments=Department.all(),
        filters=request.args,
    )


@superadmin_bp.route("/employees/<int:user_id>")
@super_required
def employee_detail(user_id):
    user = User.get_by_id(user_id)
    if not user:
        flash("Employee not found.", "danger")
        return redirect(url_for("superadmin.employees"))
    expenses, total = Expense.get_by_user(user_id, page=page_number())
    stats = Expense.overview_stats([user_id])
    return render_template(
        "superadmin/employee_detail.html",
        person=user,
        expenses=expenses,
        paging=pager(total, page_number()),
        stats=stats,
        departments=Department.all(),
        managers=fetch_all("SELECT id, name FROM users WHERE role IN ('manager', 'super_admin', 'admin') ORDER BY name"),
    )


@superadmin_bp.route("/employees/<int:user_id>/update", methods=["POST"])
@super_required
def employee_update(user_id):
    user = User.get_by_id(user_id)
    if not user:
        flash("Employee not found.", "danger")
        return redirect(url_for("superadmin.employees"))
    role = request.form.get("role")
    if role not in VALID_ROLES or role == ROLE_LEGACY_ADMIN:
        role = "employee"
    dept_id = request.form.get("department_id") or None
    dept = Department.get(int(dept_id)) if dept_id else None
    manager_id = request.form.get("manager_id") or None
    is_active = 1 if request.form.get("is_active") == "1" else 0
    execute(
        """
        UPDATE users SET name=%s, role=%s, department_id=%s, department=%s, manager_id=%s, is_active=%s
        WHERE id=%s
        """,
        (
            request.form.get("name", user.name).strip(),
            role,
            dept_id,
            dept.name if dept else user.department,
            manager_id or None,
            is_active,
            user_id,
        ),
    )
    flash("Employee updated.", "success")
    return redirect(url_for("superadmin.employee_detail", user_id=user_id))


@superadmin_bp.route("/employees/create", methods=["POST"])
@super_required
def employee_create():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password") or "Password123!"
    role = request.form.get("role") or "employee"
    if role not in VALID_ROLES or role == ROLE_LEGACY_ADMIN:
        role = "employee"
    dept_id = request.form.get("department_id") or None
    dept = Department.get(int(dept_id)) if dept_id else None
    if not name or not email:
        flash("Name and email are required.", "danger")
        return redirect(url_for("superadmin.employees"))
    if User.get_by_email(email):
        flash("Email already exists.", "danger")
        return redirect(url_for("superadmin.employees"))
    User.create(name, email, password, role, dept.name if dept else "General", dept_id)
    flash("Employee created.", "success")
    return redirect(url_for("superadmin.employees"))


@superadmin_bp.route("/departments", methods=["GET", "POST"])
@super_required
def departments():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Department name is required.", "danger")
        else:
            Department.create(
                name,
                request.form.get("manager_id") or None,
                request.form.get("monthly_budget") or 0,
            )
            flash("Department created.", "success")
        return redirect(url_for("superadmin.departments"))
    return render_template(
        "superadmin/departments.html",
        departments=Department.all(),
        managers=fetch_all("SELECT id, name FROM users WHERE role IN ('manager', 'super_admin', 'admin') ORDER BY name"),
    )


@superadmin_bp.route("/departments/<int:dept_id>/update", methods=["POST"])
@super_required
def department_update(dept_id):
    Department.update(
        dept_id,
        request.form.get("name", "").strip(),
        request.form.get("manager_id") or None,
        request.form.get("monthly_budget") or 0,
    )
    flash("Department updated.", "success")
    return redirect(url_for("superadmin.departments"))


@superadmin_bp.route("/rules", methods=["GET", "POST"])
@super_required
def rules():
    if request.method == "POST":
        execute(
            """
            INSERT INTO approval_rules
            (name, min_amount, max_amount, require_manager, require_finance, require_super, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, 1)
            """,
            (
                request.form.get("name"),
                request.form.get("min_amount") or 0,
                request.form.get("max_amount") or 0,
                1 if request.form.get("require_manager") else 0,
                1 if request.form.get("require_finance") else 0,
                1 if request.form.get("require_super") else 0,
            ),
        )
        flash("Approval rule added.", "success")
        return redirect(url_for("superadmin.rules"))
    return render_template(
        "superadmin/rules.html",
        rules=fetch_all("SELECT * FROM approval_rules ORDER BY min_amount"),
        policies=fetch_all("SELECT * FROM expense_policies ORDER BY id"),
    )


@superadmin_bp.route("/policies", methods=["POST"])
@super_required
def policy_create():
    execute(
        """
        INSERT INTO expense_policies (name, policy_type, threshold, extra_value, is_active)
        VALUES (%s, %s, %s, %s, 1)
        """,
        (
            request.form.get("name"),
            request.form.get("policy_type"),
            request.form.get("threshold") or None,
            request.form.get("extra_value") or None,
        ),
    )
    flash("Policy added.", "success")
    return redirect(url_for("superadmin.rules"))


@superadmin_bp.route("/audit")
@super_required
def audit_log():
    return render_template("superadmin/audit.html", activity=audit.recent_activity(100))
