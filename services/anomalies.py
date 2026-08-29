"""Rule-based anomaly detection. Not machine learning."""

import json

from models.database import fetch_all, fetch_one


def detect(user_id, amount, description, expense_date, receipt_hash, category_id):
    reasons = []
    level = "none"

    if amount >= 2000:
        reasons.append(f"Unusually high amount (${amount:.2f}).")
        level = _raise(level, "high")
    elif amount >= 800:
        reasons.append(f"Amount is high relative to typical claims (${amount:.2f}).")
        level = _raise(level, "medium")

    if receipt_hash:
        reuse = fetch_one(
            "SELECT id FROM expenses WHERE receipt_hash = %s AND user_id = %s LIMIT 1",
            (receipt_hash, user_id),
        )
        if reuse:
            reasons.append(f"This receipt file was already used on expense #{reuse['id']}.")
            level = _raise(level, "high")

    similar = fetch_all(
        """
        SELECT id, amount, date FROM expenses
        WHERE user_id = %s AND category_id = %s AND ABS(amount - %s) < 0.01
          AND date BETWEEN DATE_SUB(%s, INTERVAL 3 DAY) AND DATE_ADD(%s, INTERVAL 3 DAY)
          AND status <> 'rejected'
        LIMIT 5
        """,
        (user_id, category_id, amount, expense_date, expense_date),
    )
    if similar:
        ids = ", ".join(f"#{row['id']}" for row in similar)
        reasons.append(f"Similar amount/category claims in a 3-day window: {ids}.")
        level = _raise(level, "medium")

    desc = (description or "").strip().lower()
    if desc:
        dup_desc = fetch_all(
            """
            SELECT id FROM expenses
            WHERE user_id = %s AND LOWER(description) = %s
              AND date BETWEEN DATE_SUB(%s, INTERVAL 7 DAY) AND %s
              AND status <> 'rejected'
            LIMIT 5
            """,
            (user_id, desc, expense_date, expense_date),
        )
        if len(dup_desc) >= 2:
            reasons.append("Multiple expenses with the same description in the last 7 days.")
            level = _raise(level, "medium")

    rapid = fetch_one(
        """
        SELECT COUNT(*) AS c FROM expenses
        WHERE user_id = %s AND created_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
        """
        ,
        (user_id,),
    )
    if rapid and rapid["c"] >= 4:
        reasons.append("Several submissions in the last hour.")
        level = _raise(level, "low")

    return level, json.dumps(reasons) if reasons else None


def _raise(current, incoming):
    order = {"none": 0, "low": 1, "medium": 2, "high": 3}
    return incoming if order[incoming] > order.get(current, 0) else current


def parse_reasons(raw):
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else [str(raw)]
    except (TypeError, ValueError):
        return [str(raw)]
