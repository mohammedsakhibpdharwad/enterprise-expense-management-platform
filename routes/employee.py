from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from models.category import Category
from models.expense import Expense
from services import workflow
from utils.decorators import employee_required
from utils.file_upload import save_receipt
from utils.validators import validate_expense_submission

employee_bp = Blueprint("employee", __name__, url_prefix="/employee")


def _render_dashboard(categories, expenses, form=None):
    return render_template(
        "employee/dashboard.html",
        user=current_user,
        categories=categories,
        expenses=expenses,
        form=form if form is not None else {},
    )


@employee_bp.route("/dashboard", methods=["GET", "POST"])
@employee_required
def dashboard():
    try:
        categories = Category.get_all()
    except RuntimeError:
        flash("Unable to load categories. Please try again later.", "danger")
        categories = []

    if request.method == "POST":
        category_id = request.form.get("category_id")
        amount = request.form.get("amount", "").strip()
        description = request.form.get("description", "")
        expense_date = request.form.get("date", "").strip()
        receipt = request.files.get("receipt")

        valid_category_ids = {category.id for category in categories}

        errors, category_id_int, amount_value, clean_description, parsed_date = (
            validate_expense_submission(
                category_id,
                amount,
                description,
                expense_date,
                valid_category_ids,
            )
        )

        try:
            expenses = Expense.get_by_user(current_user.id)
        except RuntimeError:
            expenses = []

        if errors:
            for error in errors:
                flash(error, "danger")
            return _render_dashboard(categories, expenses, request.form)

        receipt_path = None
        receipt_hash = None

        if receipt and receipt.filename:
            try:
                saved = save_receipt(receipt)
                if isinstance(saved, tuple):
                    receipt_path = saved[0]
                    if len(saved) > 1:
                        receipt_hash = saved[1]
                else:
                    receipt_path = saved

            except ValueError as exc:
                flash(str(exc), "danger")
                return _render_dashboard(categories, expenses, request.form)

        category = next(
            (item for item in categories if item.id == category_id_int),
            None,
        )

        if category is None:
            flash("Invalid category.", "danger")
            return _render_dashboard(categories, expenses, request.form)

        try:
            expense, violations = workflow.submit_expense(
                current_user,
                category,
                amount_value,
                clean_description,
                parsed_date.strftime("%Y-%m-%d"),
                receipt_path,
                receipt_hash,
            )
        except RuntimeError:
            flash("Unable to save expense. Please try again later.", "danger")
            return _render_dashboard(categories, expenses, request.form)

        if violations:
            flash(
                "Expense submitted with policy warning(s). It requires additional review.",
                "warning",
            )
        else:
            flash(
                f"Expense #{expense.id} submitted successfully and is pending approval.",
                "success",
            )

        return redirect(url_for("employee.dashboard"))

    try:
        expenses = Expense.get_by_user(current_user.id)
    except RuntimeError:
        flash("Unable to load expense history. Please try again later.", "danger")
        expenses = []

    return _render_dashboard(categories, expenses)


@employee_bp.route("/expenses/<int:expense_id>/reopen", methods=["POST"])
@employee_required
def reopen_expense(expense_id):
    expense = Expense.get_by_id(expense_id)

    if not expense:
        flash("Expense not found.", "danger")
        return redirect(url_for("employee.dashboard"))

    if expense.user_id != current_user.id:
        flash("You are not authorized to modify this expense.", "danger")
        return redirect(url_for("employee.dashboard"))

    reason = request.form.get("reason", "").strip()

    ok, message = workflow.reopen(
        current_user,
        expense,
        reason,
    )

    flash(message, "success" if ok else "danger")

    return redirect(url_for("employee.dashboard"))


@employee_bp.route("/expenses/<int:expense_id>/resubmit", methods=["POST"])
@employee_required
def resubmit_expense(expense_id):
    expense = Expense.get_by_id(expense_id)

    if not expense:
        flash("Expense not found.", "danger")
        return redirect(url_for("employee.dashboard"))

    if expense.user_id != current_user.id:
        flash("You are not authorized to modify this expense.", "danger")
        return redirect(url_for("employee.dashboard"))

    reason = request.form.get("reason", "").strip()

    ok, message = workflow.resubmit(
        current_user,
        expense,
        reason,
    )

    flash(message, "success" if ok else "danger")

    return redirect(url_for("employee.dashboard"))