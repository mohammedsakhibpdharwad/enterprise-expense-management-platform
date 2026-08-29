from flask import Blueprint, abort, current_app, send_from_directory
from flask_login import current_user, login_required

from models.expense import Expense
from services.workflow import can_view_expense

receipts_bp = Blueprint("receipts", __name__)


@receipts_bp.route("/receipts/<int:expense_id>")
@login_required
def download(expense_id):
    expense = Expense.get_by_id(expense_id)
    if not expense or not expense.receipt_path:
        abort(404)
    if not can_view_expense(current_user, expense):
        abort(403)
    filename = expense.receipt_path.split("/")[-1]
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename, as_attachment=False)
