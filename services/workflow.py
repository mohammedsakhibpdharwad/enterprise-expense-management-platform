from models.database import fetch_all, fetch_one
from models.expense import Expense
from models.user import User
from services import audit, notifications
from services.anomalies import detect as detect_anomalies, parse_reasons
from services.policies import evaluate_policies, serialize_violations
from utils.rbac import ROLE_FINANCE, ROLE_MANAGER, ROLE_SUPER, normalize_role


STAGE_ORDER = ["manager", "finance", "super"]


def matching_rule(amount):
    return fetch_one(
        """
        SELECT * FROM approval_rules
        WHERE is_active = 1 AND %s BETWEEN min_amount AND max_amount
        ORDER BY min_amount DESC
        LIMIT 1
        """,
        (amount,),
    )


def required_stages_for_amount(amount):
    rule = matching_rule(amount)
    stages = []
    if not rule:
        return ["manager"]
    if rule["require_manager"]:
        stages.append("manager")
    if rule["require_finance"]:
        stages.append("finance")
    if rule["require_super"]:
        stages.append("super")
    return stages or ["manager"]


def pending_approver_label(expense):
    if expense.status != "pending":
        return "—"
    return {
        "manager": "Manager",
        "finance": "Finance Admin",
        "super": "Super Admin",
    }.get(expense.current_stage, expense.current_stage)


def submit_expense(user, category, amount, description, expense_date, receipt_path, receipt_hash):
    stages = required_stages_for_amount(amount)
    violations = evaluate_policies(
        user,
        category.name,
        amount,
        expense_date,
        bool(receipt_path),
    )
    risk_level, risk_reasons = detect_anomalies(
        user.id, amount, description, expense_date, receipt_hash, category.id
    )
    if violations:
        extra = parse_reasons(risk_reasons)
        extra.append("Policy violation(s) detected.")
        risk_reasons = __import__("json").dumps(extra)
        if risk_level in ("none", "low"):
            risk_level = "medium"

    expense = Expense.create(
        user_id=user.id,
        category_id=category.id,
        amount=amount,
        description=description,
        expense_date=expense_date,
        receipt_path=receipt_path,
        current_stage=stages[0],
        required_stages=",".join(stages),
        policy_violations=serialize_violations(violations),
        risk_level=risk_level,
        risk_reasons=risk_reasons,
        receipt_hash=receipt_hash,
    )
    audit.log_action(
        expense.id,
        "submitted",
        user.id,
        previous_status=None,
        new_status="pending",
        previous_stage=None,
        new_stage=stages[0],
        comment=None,
    )
    _notify_stage_reviewers(expense, user, "Expense submitted", f"{user.name} submitted expense #{expense.id}.")
    if violations:
        _notify_finance_policy(expense)
    return expense, violations


def can_act_on(actor, expense):
    role = normalize_role(actor.role)
    if expense.status != "pending":
        return False
    if role == ROLE_MANAGER:
        team = User.team_member_ids(actor.id)
        return expense.user_id in team and expense.user_id != actor.id and expense.current_stage == "manager"
    if role == ROLE_FINANCE:
        return expense.current_stage == "finance"
    if role == ROLE_SUPER:
        return expense.current_stage in ("super", "finance", "manager")
    return False


def approve(actor, expense, comment=None, override_reason=None):
    if not can_act_on(actor, expense):
        return False, "You are not authorized to approve this expense at the current stage."

    stages = [s for s in (expense.required_stages or "manager").split(",") if s]
    try:
        idx = stages.index(expense.current_stage)
    except ValueError:
        idx = 0

    prev_status = expense.status
    prev_stage = expense.current_stage
    if expense.policy_violations and not override_reason and normalize_role(actor.role) in (ROLE_FINANCE, ROLE_SUPER):
        return False, "This expense has policy violations. Provide an override reason to continue."

    if override_reason:
        audit.log_action(
            expense.id,
            "policy_override",
            actor.id,
            prev_status,
            prev_status,
            prev_stage,
            prev_stage,
            override_reason,
        )

    if idx + 1 < len(stages):
        next_stage = stages[idx + 1]
        Expense.update_workflow(expense.id, current_stage=next_stage, status="pending")
        audit.log_action(
            expense.id,
            "approved",
            actor.id,
            prev_status,
            "pending",
            prev_stage,
            next_stage,
            comment or f"Approved at {prev_stage} stage.",
        )
        notifications.notify(
            expense.user_id,
            "Expense advanced",
            f"Expense #{expense.id} was approved at the {prev_stage} stage and is now with {next_stage}.",
            f"/employee/expenses/{expense.id}",
        )
        refreshed = Expense.get_by_id(expense.id)
        _notify_stage_reviewers(refreshed, actor, "Approval required", f"Expense #{expense.id} needs {next_stage} review.")
        return True, f"Approved at {prev_stage}. Next stage: {next_stage}."

    Expense.update_workflow(expense.id, status="approved", current_stage="complete")
    audit.log_action(
        expense.id,
        "final_approved",
        actor.id,
        prev_status,
        "approved",
        prev_stage,
        "complete",
        comment or "Final approval.",
    )
    notifications.notify(
        expense.user_id,
        "Expense approved",
        f"Expense #{expense.id} was fully approved.",
        f"/employee/expenses/{expense.id}",
    )
    return True, "Expense fully approved."


def reject(actor, expense, reason):
    if not reason or not reason.strip():
        return False, "A rejection reason is required."
    if not can_act_on(actor, expense):
        return False, "You are not authorized to reject this expense at the current stage."
    prev_status = expense.status
    prev_stage = expense.current_stage
    Expense.update_workflow(expense.id, status="rejected")
    audit.log_action(
        expense.id,
        "rejected",
        actor.id,
        prev_status,
        "rejected",
        prev_stage,
        prev_stage,
        reason.strip(),
    )
    notifications.notify(
        expense.user_id,
        "Expense rejected",
        f"Expense #{expense.id} was rejected: {reason.strip()[:200]}",
        f"/employee/expenses/{expense.id}",
    )
    return True, "Expense rejected."


def reopen(actor, expense, reason):
    """Employees may reopen their own rejected expenses; reviewers may reopen per policy."""
    if not reason or not reason.strip():
        return False, "A reopen reason is required."
    role = normalize_role(actor.role)
    allowed = False
    if expense.status != "rejected":
        return False, "Only rejected expenses can be reopened."
    if expense.user_id == actor.id and expense.reopen_count < 3:
        allowed = True
    if role in (ROLE_FINANCE, ROLE_SUPER):
        allowed = True
    if not allowed:
        return False, "This expense cannot be reopened."

    stages = required_stages_for_amount(float(expense.amount))
    Expense.update_workflow(
        expense.id,
        status="pending",
        current_stage=stages[0],
        required_stages=",".join(stages),
        reopen_count=int(expense.reopen_count or 0) + 1,
    )
    audit.log_action(
        expense.id,
        "reopened",
        actor.id,
        "rejected",
        "pending",
        expense.current_stage,
        stages[0],
        reason.strip(),
    )
    notifications.notify(
        expense.user_id,
        "Expense reopened",
        f"Expense #{expense.id} was reopened for correction/review.",
        f"/employee/expenses/{expense.id}",
    )
    return True, "Expense reopened and returned to the first approval stage."


def resubmit(actor, expense, reason):
    if expense.user_id != actor.id:
        return False, "Only the owner can resubmit this expense."
    if expense.status != "pending" or int(expense.reopen_count or 0) == 0:
        return False, "Resubmit is only available after a reopen."
    audit.log_action(
        expense.id,
        "resubmitted",
        actor.id,
        expense.status,
        "pending",
        expense.current_stage,
        expense.current_stage,
        reason or "Employee resubmitted after correction.",
    )
    notifications.notify(
        expense.user_id,
        "Expense resubmitted",
        f"Expense #{expense.id} was resubmitted for review.",
        f"/employee/expenses/{expense.id}",
    )
    _notify_stage_reviewers(expense, actor, "Expense resubmitted", f"{actor.name} resubmitted expense #{expense.id}.")
    return True, "Expense resubmitted to reviewers."


def bulk_decide(actor, expense_ids, action, reason=None, override_reason=None):
    results = []
    for expense_id in expense_ids:
        expense = Expense.get_by_id(int(expense_id))
        if not expense:
            results.append((expense_id, False, "Not found"))
            continue
        if action == "approve":
            ok, msg = approve(actor, expense, comment="Bulk approve", override_reason=override_reason)
        else:
            ok, msg = reject(actor, expense, reason or "")
        results.append((expense_id, ok, msg))
    return results


def _notify_stage_reviewers(expense, actor, title, message):
    stage = expense.current_stage
    recipients = []
    if stage == "manager":
        owner = User.get_by_id(expense.user_id)
        if owner and owner.manager_id:
            recipients.append(owner.manager_id)
        dept = fetch_one("SELECT manager_id FROM departments WHERE id = %s", (owner.department_id,)) if owner else None
        if dept and dept["manager_id"]:
            recipients.append(dept["manager_id"])
    elif stage == "finance":
        rows = fetch_all("SELECT id FROM users WHERE role IN ('finance_admin', 'super_admin', 'admin') AND is_active = 1")
        recipients.extend(r["id"] for r in rows)
    elif stage == "super":
        rows = fetch_all("SELECT id FROM users WHERE role IN ('super_admin', 'admin') AND is_active = 1")
        recipients.extend(r["id"] for r in rows)
    for user_id in set(recipients):
        if user_id != getattr(actor, "id", None):
            notifications.notify(user_id, title, message, f"/approvals/{expense.id}")


def _notify_finance_policy(expense):
    rows = fetch_all("SELECT id FROM users WHERE role IN ('finance_admin', 'super_admin', 'admin') AND is_active = 1")
    for row in rows:
        notifications.notify(
            row["id"],
            "Policy violation",
            f"Expense #{expense.id} was flagged for policy review.",
            f"/approvals/{expense.id}",
        )


def can_view_expense(actor, expense):
    if expense.user_id == actor.id:
        return True
    role = normalize_role(actor.role)
    if role in (ROLE_FINANCE, ROLE_SUPER):
        return True
    if role == ROLE_MANAGER:
        return expense.user_id in User.team_member_ids(actor.id)
    return False
