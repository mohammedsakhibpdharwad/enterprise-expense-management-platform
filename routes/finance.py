from datetime import datetime

from flask import Blueprint, Response, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from models.category import Category
from models.database import fetch_all
from models.expense import Expense
from services import audit
from utils.decorators import finance_required
from utils.http import expense_filters_from_request, page_number, pager

finance_bp = Blueprint("finance", __name__, url_prefix="/finance")


@finance_bp.route("/dashboard")
@finance_required
def dashboard():
    stats = Expense.overview_stats()
    pending, pending_total = Expense.search({"status": "pending"}, page=1, per_page=8)
    flagged, _t = Expense.search({"risk": "high"}, page=1, per_page=8)
    violations = audit.count_policy_overrides()
    return render_template(
        "finance/dashboard.html",
        stats=stats,
        pending=pending,
        flagged=flagged,
        override_count=violations,
        department_totals=Expense.get_totals_by_department(),
        category_totals=Expense.get_totals_by_category(),
    )


@finance_bp.route("/reports")
@finance_required
def reports():
    filters = expense_filters_from_request()
    expenses, total = Expense.search(filters, page=page_number(), per_page=20)
    return render_template(
        "finance/reports.html",
        expenses=expenses,
        filters=filters,
        paging=pager(total, page_number()),
        categories=Category.get_all(),
    )


@finance_bp.route("/reports/csv")
@finance_required
def reports_csv():
    import csv
    import io

    filters = expense_filters_from_request()
    rows = Expense.get_all_for_csv(filters)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "ID", "Employee", "Email", "Employee Code", "Department", "Category",
            "Amount", "Description", "Date", "Status", "Stage", "Risk", "Submitted At",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row["id"],
                row["employee_name"],
                row["email"],
                row["employee_code"],
                row["department"],
                row["category"],
                f"{row['amount']:.2f}",
                (row["description"] or "").replace("\n", " ").replace("\r", " "),
                row["date"].strftime("%Y-%m-%d") if hasattr(row["date"], "strftime") else row["date"],
                row["status"],
                row["stage"],
                row["risk_level"],
                row["created_at"].strftime("%Y-%m-%d %H:%M:%S") if hasattr(row["created_at"], "strftime") else row["created_at"],
            ]
        )
    filename = f"expense_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@finance_bp.route("/policies")
@finance_required
def policies():
    from models.database import fetch_all as fa

    return render_template(
        "finance/policies.html",
        policies=fa("SELECT * FROM expense_policies ORDER BY id"),
        rules=fa("SELECT * FROM approval_rules ORDER BY min_amount"),
    )


@finance_bp.route("/api/analytics/extended")
@finance_required
def extended_analytics():
    stats = Expense.overview_stats()
    employees = fetch_all(
        """
        SELECT u.name, COALESCE(SUM(CASE WHEN e.status='approved' THEN e.amount END),0) AS total
        FROM users u LEFT JOIN expenses e ON e.user_id = u.id
        GROUP BY u.id ORDER BY total DESC LIMIT 8
        """
    )
    return jsonify(
        {
            "stats": stats,
            "employees": [{"name": r["name"], "total": float(r["total"])} for r in employees],
            "departments": Expense.get_totals_by_department(),
            "categories": Expense.get_totals_by_category(),
            "trend": Expense.get_six_month_trend(),
        }
    )
