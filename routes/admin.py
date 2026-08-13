from datetime import datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, url_for
from flask_login import current_user

from models.expense import Expense
from utils.decorators import admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.before_request
@admin_required
def require_admin():
    """Ensure every admin blueprint route is admin-only."""


@admin_bp.route("/dashboard")
def dashboard():
    try:
        expenses = Expense.get_all()
    except RuntimeError:
        flash("Unable to load expenses. Please try again later.", "danger")
        expenses = []
    return render_template("admin/dashboard.html", user=current_user, expenses=expenses)


@admin_bp.route("/expenses/<int:expense_id>/approve", methods=["POST"])
def approve_expense(expense_id):
    if expense_id <= 0:
        flash("Invalid expense ID.", "danger")
        return redirect(url_for("admin.dashboard"))

    try:
        expense = Expense.get_by_id(expense_id)
    except RuntimeError:
        flash("Unable to process request. Please try again later.", "danger")
        return redirect(url_for("admin.dashboard"))

    if not expense:
        flash("Expense not found.", "danger")
        return redirect(url_for("admin.dashboard"))

    if expense.status != "pending":
        flash("Only pending expenses can be approved.", "warning")
        return redirect(url_for("admin.dashboard"))

    try:
        Expense.update_status(expense_id, "approved")
    except RuntimeError:
        flash("Unable to approve expense. Please try again later.", "danger")
        return redirect(url_for("admin.dashboard"))

    flash(f"Expense #{expense_id} approved.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/expenses/<int:expense_id>/reject", methods=["POST"])
def reject_expense(expense_id):
    if expense_id <= 0:
        flash("Invalid expense ID.", "danger")
        return redirect(url_for("admin.dashboard"))

    try:
        expense = Expense.get_by_id(expense_id)
    except RuntimeError:
        flash("Unable to process request. Please try again later.", "danger")
        return redirect(url_for("admin.dashboard"))

    if not expense:
        flash("Expense not found.", "danger")
        return redirect(url_for("admin.dashboard"))

    if expense.status != "pending":
        flash("Only pending expenses can be rejected.", "warning")
        return redirect(url_for("admin.dashboard"))

    try:
        Expense.update_status(expense_id, "rejected")
    except RuntimeError:
        flash("Unable to reject expense. Please try again later.", "danger")
        return redirect(url_for("admin.dashboard"))

    flash(f"Expense #{expense_id} rejected.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/analytics")
def analytics():
    try:
        totals = Expense.get_monthly_totals()
    except RuntimeError:
        flash("Unable to load analytics. Please try again later.", "danger")
        totals = {"current_month": 0.0, "previous_month": 0.0}
    return render_template("admin/analytics.html", user=current_user, totals=totals)


@admin_bp.route("/api/analytics/summary")
def analytics_summary():
    try:
        return jsonify(Expense.get_monthly_totals())
    except RuntimeError:
        return jsonify({"error": "Unable to load summary."}), 500


@admin_bp.route("/api/analytics/by-department")
def analytics_by_department():
    try:
        return jsonify(Expense.get_totals_by_department())
    except RuntimeError:
        return jsonify({"error": "Unable to load department analytics."}), 500


@admin_bp.route("/api/analytics/by-category")
def analytics_by_category():
    try:
        return jsonify(Expense.get_totals_by_category())
    except RuntimeError:
        return jsonify({"error": "Unable to load category analytics."}), 500


@admin_bp.route("/api/analytics/trend")
def analytics_trend():
    try:
        return jsonify(Expense.get_six_month_trend())
    except RuntimeError:
        return jsonify({"error": "Unable to load trend analytics."}), 500


@admin_bp.route("/analytics/download")
def download_report():
    import csv
    import io

    from flask import Response

    try:
        rows = Expense.get_all_for_csv()
    except RuntimeError:
        flash("Unable to generate report. Please try again later.", "danger")
        return redirect(url_for("admin.analytics"))

    output = io.StringIO()
    writer = csv.writer(output)
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
            "Submitted At",
        ]
    )
    for row in rows:
        expense_date = row["date"]
        created_at = row["created_at"]
        writer.writerow(
            [
                row["id"],
                row["employee_name"],
                row["email"],
                row["department"],
                row["category"],
                f"{row['amount']:.2f}",
                (row["description"] or "").replace("\n", " ").replace("\r", " "),
                expense_date.strftime("%Y-%m-%d") if hasattr(expense_date, "strftime") else expense_date,
                row["status"],
                created_at.strftime("%Y-%m-%d %H:%M:%S")
                if hasattr(created_at, "strftime")
                else created_at,
            ]
        )

    filename = f"expense_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
