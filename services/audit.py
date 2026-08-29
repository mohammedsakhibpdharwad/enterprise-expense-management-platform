from models.database import execute, fetch_all, fetch_one


def log_action(expense_id, action, performed_by, previous_status=None, new_status=None,
               previous_stage=None, new_stage=None, comment=None):
    execute(
        """
        INSERT INTO approval_audit
        (expense_id, action, previous_status, new_status, previous_stage, new_stage, performed_by, comment)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            expense_id,
            action,
            previous_status,
            new_status,
            previous_stage,
            new_stage,
            performed_by,
            comment,
        ),
    )


def get_timeline(expense_id):
    return fetch_all(
        """
        SELECT a.*, u.name AS actor_name, u.role AS actor_role
        FROM approval_audit a
        LEFT JOIN users u ON u.id = a.performed_by
        WHERE a.expense_id = %s
        ORDER BY a.created_at ASC, a.id ASC
        """,
        (expense_id,),
    )


def recent_activity(limit=25):
    return fetch_all(
        """
        SELECT a.*, u.name AS actor_name, e.amount, emp.name AS employee_name
        FROM approval_audit a
        LEFT JOIN users u ON u.id = a.performed_by
        LEFT JOIN expenses e ON e.id = a.expense_id
        LEFT JOIN users emp ON emp.id = e.user_id
        ORDER BY a.created_at DESC
        LIMIT %s
        """,
        (limit,),
    )


def count_policy_overrides():
    row = fetch_one(
        "SELECT COUNT(*) AS c FROM approval_audit WHERE action = 'policy_override'"
    )
    return int(row["c"] if row else 0)
