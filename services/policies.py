import json

from models.database import fetch_all, fetch_one


def active_policies():
    return fetch_all("SELECT * FROM expense_policies WHERE is_active = 1")


def evaluate_policies(user, category_name, amount, expense_date, has_receipt):
    """Return list of human-readable policy violation strings. Rule-based only."""
    violations = []
    policies = active_policies()
    for policy in policies:
        if policy["department_id"] and user.department_id != policy["department_id"]:
            continue
        ptype = policy["policy_type"]
        threshold = float(policy["threshold"] or 0)
        extra = policy["extra_value"]

        if ptype == "receipt_required" and amount >= threshold and not has_receipt:
            violations.append(f"Receipt is required for amounts of ${threshold:.2f} or more.")

        if ptype == "max_amount" and amount > threshold:
            violations.append(f"Amount exceeds company maximum of ${threshold:.2f}.")

        if ptype == "category_max" and extra and category_name == extra and amount > threshold:
            violations.append(f"{category_name} expenses cannot exceed ${threshold:.2f}.")

        if ptype == "daily_limit" and extra and category_name == extra:
            row = fetch_one(
                """
                SELECT COALESCE(SUM(amount), 0) AS total
                FROM expenses
                WHERE user_id = %s AND date = %s AND status <> 'rejected'
                  AND category_id = (SELECT id FROM categories WHERE name = %s LIMIT 1)
                """,
                (user.id, expense_date, extra),
            )
            running = float(row["total"] or 0) + amount
            if running > threshold:
                violations.append(
                    f"Daily {extra} spend would be ${running:.2f}, above the ${threshold:.2f} limit."
                )

    return violations


def serialize_violations(violations):
    return json.dumps(violations) if violations else None


def parse_violations(raw):
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else [str(raw)]
    except (TypeError, ValueError):
        return [str(raw)]
