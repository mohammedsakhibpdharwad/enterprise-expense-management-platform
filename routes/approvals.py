from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models.category import Category
from models.expense import Expense
from models.user import User
from services import audit, workflow
from services.anomalies import parse_reasons
from services.policies import parse_violations
from utils.decorators import reviewer_required
from utils.http import expense_filters_from_request, page_number, pager
from utils.rbac import ROLE_MANAGER, normalize_role

approvals_bp = Blueprint("approvals", __name__)


def _scope_ids():
    role = normalize_role(current_user.role)
    if role == ROLE_MANAGER:
        ids = User.team_member_ids(current_user.id)
        return [i for i in ids if i != current_user.id]
    return None


@approvals_bp.route("/approvals")
@reviewer_required
def inbox():
    filters = expense_filters_from_request()
    if not filters.get("status"):
        filters["status"] = "pending"
    page = page_number()
    expenses, total = Expense.search(filters, page=page, user_ids=_scope_ids())
    return render_template(
        "approvals/inbox.html",
        expenses=expenses,
        filters=filters,
        paging=pager(total, page),
        categories=Category.get_all(),
        pending_approver=workflow.pending_approver_label,
    )


@approvals_bp.route("/approvals/<int:expense_id>")
@reviewer_required
def detail(expense_id):
    expense = Expense.get_by_id(expense_id)
    if not expense or not workflow.can_view_expense(current_user, expense):
        flash("Expense not found or not authorized.", "danger")
        return redirect(url_for("approvals.inbox"))
    return render_template(
        "expenses/detail.html",
        expense=expense,
        timeline=audit.get_timeline(expense_id),
        violations=parse_violations(expense.policy_violations),
        risk_reasons=parse_reasons(expense.risk_reasons),
        pending_approver=workflow.pending_approver_label(expense),
        can_act=workflow.can_act_on(current_user, expense),
        reviewer_view=True,
    )


@approvals_bp.route("/approvals/<int:expense_id>/approve", methods=["POST"])
@reviewer_required
def approve(expense_id):
    expense = Expense.get_by_id(expense_id)
    if not expense:
        flash("Expense not found.", "danger")
        return redirect(url_for("approvals.inbox"))
    ok, msg = workflow.approve(
        current_user,
        expense,
        comment=request.form.get("comment"),
        override_reason=request.form.get("override_reason"),
    )
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("approvals.detail", expense_id=expense_id))


@approvals_bp.route("/approvals/<int:expense_id>/reject", methods=["POST"])
@reviewer_required
def reject(expense_id):
    expense = Expense.get_by_id(expense_id)
    if not expense:
        flash("Expense not found.", "danger")
        return redirect(url_for("approvals.inbox"))
    ok, msg = workflow.reject(current_user, expense, request.form.get("reason", ""))
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("approvals.detail", expense_id=expense_id))


@approvals_bp.route("/approvals/<int:expense_id>/reopen", methods=["POST"])
@reviewer_required
def reopen(expense_id):
    expense = Expense.get_by_id(expense_id)
    if not expense or not workflow.can_view_expense(current_user, expense):
        flash("Expense not found or not authorized.", "danger")
        return redirect(url_for("approvals.inbox"))
    ok, msg = workflow.reopen(current_user, expense, request.form.get("reason", ""))
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("approvals.detail", expense_id=expense_id))


@approvals_bp.route("/approvals/bulk", methods=["POST"])
@reviewer_required
def bulk():
    ids = request.form.getlist("expense_ids")
    action = request.form.get("action")
    reason = request.form.get("reason")
    if action == "reject" and not (reason or "").strip():
        flash("Bulk rejection requires a reason.", "danger")
        return redirect(url_for("approvals.inbox"))
    results = workflow.bulk_decide(
        current_user,
        ids,
        action,
        reason=reason,
        override_reason=request.form.get("override_reason"),
    )
    ok_count = sum(1 for _i, ok, _m in results if ok)
    flash(f"Bulk {action}: {ok_count} of {len(results)} succeeded.", "info")
    return redirect(url_for("approvals.inbox"))
