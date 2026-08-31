from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

from models.expense import Expense
from services import notifications


notifications_bp = Blueprint("notify", __name__)


@notifications_bp.route("/notifications")
@login_required
def list_notifications():
    items = notifications.list_for_user(current_user.id)

    return render_template(
        "notifications/list.html",
        items=items,
    )


@notifications_bp.route("/notifications/<int:item_id>")
@login_required
def notification_detail(item_id):
    item = notifications.get_for_user(
        item_id,
        current_user.id,
    )

    if not item:
        return redirect(
            url_for("notify.list_notifications")
        )

    notifications.mark_read(
        item_id,
        current_user.id,
    )

    expense = None

    link = item.get("link")

    if link:
        parts = link.rstrip("/").split("/")

        try:
            expense_id = int(parts[-1])
            expense = Expense.get_by_id(expense_id)
        except (ValueError, TypeError):
            expense = None

    return render_template(
        "notifications/detail.html",
        item=item,
        expense=expense,
    )


@notifications_bp.route(
    "/notifications/<int:item_id>/read",
    methods=["POST"],
)
@login_required
def mark_read(item_id):
    notifications.mark_read(
        item_id,
        current_user.id,
    )

    return redirect(
        url_for("notify.list_notifications")
    )


@notifications_bp.route(
    "/notifications/read-all",
    methods=["POST"],
)
@login_required
def mark_all():
    notifications.mark_all_read(
        current_user.id
    )

    return redirect(
        url_for("notify.list_notifications")
    )