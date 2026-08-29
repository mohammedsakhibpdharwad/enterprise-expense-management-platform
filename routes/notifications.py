from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

from services import notifications

notifications_bp = Blueprint("notify", __name__)

@notifications_bp.route("/notifications")
@login_required
def list_notifications():
    items = notifications.list_for_user(current_user.id)
    return render_template("notifications/list.html", items=items)


@notifications_bp.route("/notifications/<int:item_id>/read", methods=["POST"])
@login_required
def mark_read(item_id):
    notifications.mark_read(item_id, current_user.id)
    return redirect(url_for("notify.list_notifications"))


@notifications_bp.route("/notifications/read-all", methods=["POST"])
@login_required
def mark_all():
    notifications.mark_all_read(current_user.id)
    return redirect(url_for("notify.list_notifications"))
