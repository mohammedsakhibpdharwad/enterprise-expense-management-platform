from datetime import datetime
import csv
import io

from flask import (
    Blueprint,
    Response,
    jsonify,
    render_template,
)
from flask_login import current_user

from models.category import Category
from models.database import fetch_all
from models.expense import Expense
from services import audit
from utils.decorators import finance_required
from utils.http import expense_filters_from_request, page_number, pager


finance_bp = Blueprint(
    "finance",
    __name__,
    url_prefix="/finance",
)


@finance_bp.route("/dashboard")
@finance_required
def dashboard():
    stats = Expense.overview_stats()

    pending, _pending_total = Expense.search(
        {"status": "pending"},
        page=1,
        per_page=8,
    )

    flagged, _flagged_total = Expense.search(
        {"risk": "high"},
        page=1,
        per_page=8,
    )

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

    expenses, total = Expense.search(
        filters,
        page=page_number(),
        per_page=20,
    )

    current_page = page_number()

    return render_template(
        "finance/reports.html",
        expenses=expenses,
        filters=filters,
        paging=pager(total, current_page),
        categories=Category.get_all(),
    )


@finance_bp.route("/reports/csv")
@finance_required
def reports_csv():
    """
    Export the finance report as CSV.

    Uses the same filters as the Reports page and retrieves records
    in batches so the export is not limited to the first 100 records.
    """

    filters = expense_filters_from_request()

    all_expenses = []

    export_page = 1
    per_page = 100

    while True:
        expenses, total = Expense.search(
            filters,
            page=export_page,
            per_page=per_page,
        )

        if not expenses:
            break

        all_expenses.extend(expenses)

        if len(all_expenses) >= total:
            break

        export_page += 1

    output = io.StringIO(newline="")

    writer = csv.writer(
        output,
        lineterminator="\n",
    )

    writer.writerow(
        [
            "ID",
            "Employee",
            "Email",
            "Department",
            "Category",
            "Amount",
            "Description",
            "Date",
            "Status",
            "Approval Stage",
            "Risk Level",
            "Submitted At",
        ]
    )

    for expense in all_expenses:
        writer.writerow(
            [
                expense.id,
                expense.user_name or "",
                expense.user_email or "",
                expense.department or "",
                expense.category_name or "",
                f"{expense.amount:.2f}",
                (expense.description or "")
                .replace("\n", " ")
                .replace("\r", " ")
                .strip(),
                (
                    expense.date.strftime("%Y-%m-%d")
                    if hasattr(expense.date, "strftime")
                    else expense.date or ""
                ),
                expense.status or "",
                expense.current_stage or "",
                expense.risk_level or "none",
                (
                    expense.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    if hasattr(expense.created_at, "strftime")
                    else expense.created_at or ""
                ),
            ]
        )

    filename = (
        f"expense_report_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": (
                f"attachment; filename={filename}"
            )
        },
    )


@finance_bp.route("/policies")
@finance_required
def policies():
    from models.database import fetch_all as fa

    return render_template(
        "finance/policies.html",
        policies=fa(
            "SELECT * FROM expense_policies ORDER BY id"
        ),
        rules=fa(
            "SELECT * FROM approval_rules ORDER BY min_amount"
        ),
    )


@finance_bp.route("/api/analytics/extended")
@finance_required
def extended_analytics():
    stats = Expense.overview_stats()

    employees = fetch_all(
        """
        SELECT
            u.name,
            COALESCE(
                SUM(
                    CASE
                        WHEN e.status = 'approved'
                        THEN e.amount
                    END
                ),
                0
            ) AS total
        FROM users u
        LEFT JOIN expenses e
            ON e.user_id = u.id
        GROUP BY u.id
        ORDER BY total DESC
        LIMIT 8
        """
    )

    return jsonify(
        {
            "stats": stats,
            "employees": [
                {
                    "name": row["name"],
                    "total": float(row["total"]),
                }
                for row in employees
            ],
            "departments": Expense.get_totals_by_department(),
            "categories": Expense.get_totals_by_category(),
            "trend": Expense.get_six_month_trend(),
        }
    )