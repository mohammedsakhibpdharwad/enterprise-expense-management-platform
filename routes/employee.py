from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from models.category import Category
from models.expense import Expense
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
        errors, category_id_int, amount_value, clean_description, parsed_date = validate_expense_submission(
            category_id,
            amount,
            description,
            expense_date,
            valid_category_ids,
        )

        if errors:
            for error in errors:
                flash(error, "danger")
            try:
                expenses = Expense.get_by_user(current_user.id)
            except RuntimeError:
                expenses = []
            return _render_dashboard(categories, expenses, request.form)

        receipt_path = None
        if receipt and receipt.filename:
            try:
                receipt_path = save_receipt(receipt)
            except ValueError as exc:
                flash(str(exc), "danger")
                try:
                    expenses = Expense.get_by_user(current_user.id)
                except RuntimeError:
                    expenses = []
                return _render_dashboard(categories, expenses, request.form)

        try:
            Expense.create(
                user_id=current_user.id,
                category_id=category_id_int,
                amount=amount_value,
                description=clean_description,
                expense_date=parsed_date.strftime("%Y-%m-%d"),
                receipt_path=receipt_path,
            )
        except RuntimeError:
            flash("Unable to save expense. Please try again later.", "danger")
            try:
                expenses = Expense.get_by_user(current_user.id)
            except RuntimeError:
                expenses = []
            return _render_dashboard(categories, expenses, request.form)

        flash("Expense submitted successfully and is pending approval.", "success")
        return redirect(url_for("employee.dashboard"))

    try:
        expenses = Expense.get_by_user(current_user.id)
    except RuntimeError:
        flash("Unable to load expense history. Please try again later.", "danger")
        expenses = []

    return _render_dashboard(categories, expenses)
