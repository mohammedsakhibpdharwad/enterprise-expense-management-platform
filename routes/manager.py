from flask import Blueprint, render_template
from flask_login import current_user

from models.expense import Expense
from models.user import User
from utils.decorators import manager_required
from utils.http import expense_filters_from_request, page_number, pager

manager_bp = Blueprint("manager", __name__, url_prefix="/manager")


@manager_bp.route("/dashboard")
@manager_required
def dashboard():
    team_ids = [i for i in User.team_member_ids(current_user.id) if i != current_user.id]
    filters = expense_filters_from_request()
    filters["status"] = filters.get("status") or "pending"
    expenses, total = Expense.search(filters, page=page_number(), user_ids=team_ids)
    stats = Expense.overview_stats(team_ids)
    return render_template(
        "manager/dashboard.html",
        stats=stats,
        expenses=expenses,
        paging=pager(total, page_number()),
        team_size=len(team_ids),
    )
