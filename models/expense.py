from decimal import Decimal

from models.database import execute, fetch_all, fetch_one


EXPENSE_SELECT = """
    SELECT e.id, e.user_id, e.category_id, e.amount, e.description,
           e.date AS expense_date,
           e.receipt_path,
           e.status,
           e.created_at,
           e.current_stage,
           e.required_stages,
           e.policy_violations,
           e.risk_level,
           e.risk_reasons,
           e.reopen_count,
           e.receipt_hash,
           u.name AS user_name,
           u.email AS user_email,
           u.department,
           c.name AS category_name
    FROM expenses e
    JOIN users u ON e.user_id = u.id
    JOIN categories c ON e.category_id = c.id
"""


class Expense:
    """Expense model backed by the MySQL expenses table."""

    def __init__(self, **kwargs):
        if "date" in kwargs and "expense_date" not in kwargs:
            kwargs["expense_date"] = kwargs.pop("date")

        self.id = kwargs.get("id")
        self.user_id = kwargs.get("user_id")
        self.category_id = kwargs.get("category_id")

        amount = kwargs.get("amount")
        self.amount = Decimal(str(amount)) if amount is not None else Decimal("0")

        self.description = kwargs.get("description")
        self.date = kwargs.get("expense_date")
        self.receipt_path = kwargs.get("receipt_path")
        self.status = kwargs.get("status")
        self.created_at = kwargs.get("created_at")

        self.current_stage = kwargs.get("current_stage")
        self.required_stages = kwargs.get("required_stages")
        self.policy_violations = kwargs.get("policy_violations")
        self.risk_level = kwargs.get("risk_level")
        self.risk_reasons = kwargs.get("risk_reasons")
        self.reopen_count = kwargs.get("reopen_count", 0)
        self.receipt_hash = kwargs.get("receipt_hash")

        self.user_name = kwargs.get("user_name")
        self.user_email = kwargs.get("user_email")
        self.department = kwargs.get("department")
        self.category_name = kwargs.get("category_name")

    @staticmethod
    def _row_to_expense(row):
        data = dict(row)

        if "date" in data and "expense_date" not in data:
            data["expense_date"] = data.pop("date")

        return Expense(**data)

    @staticmethod
    def search(filters=None, page=1, per_page=25, user_ids=None):
        """Search expenses with filters and pagination."""
        filters = filters or {}

        page = max(int(page or 1), 1)
        per_page = max(min(int(per_page or 25), 100), 1)
        offset = (page - 1) * per_page

        conditions = []
        params = []

        if user_ids is not None:
            if not user_ids:
                return [], 0

            placeholders = ", ".join(["%s"] * len(user_ids))
            conditions.append(f"e.user_id IN ({placeholders})")
            params.extend(user_ids)

        if filters.get("q"):
            like = f"%{filters['q'].strip()}%"
            conditions.append(
                "(u.name LIKE %s OR u.email LIKE %s OR e.description LIKE %s)"
            )
            params.extend([like, like, like])

        if filters.get("employee_id"):
            conditions.append("e.user_id = %s")
            params.append(int(filters["employee_id"]))

        if filters.get("department"):
            conditions.append("u.department = %s")
            params.append(filters["department"])

        if filters.get("department_id"):
            conditions.append("u.department_id = %s")
            params.append(int(filters["department_id"]))

        if filters.get("category_id"):
            conditions.append("e.category_id = %s")
            params.append(int(filters["category_id"]))

        if filters.get("status"):
            conditions.append("e.status = %s")
            params.append(filters["status"])

        if filters.get("min_amount") not in (None, ""):
            conditions.append("e.amount >= %s")
            params.append(filters["min_amount"])

        if filters.get("max_amount") not in (None, ""):
            conditions.append("e.amount <= %s")
            params.append(filters["max_amount"])

        if filters.get("date_from"):
            conditions.append("e.date >= %s")
            params.append(filters["date_from"])

        if filters.get("date_to"):
            conditions.append("e.date <= %s")
            params.append(filters["date_to"])

        if filters.get("approval_stage"):
            conditions.append("e.current_stage = %s")
            params.append(filters["approval_stage"])

        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        count_row = fetch_one(
            f"""
            SELECT COUNT(*) AS total
            FROM expenses e
            JOIN users u ON e.user_id = u.id
            JOIN categories c ON e.category_id = c.id
            {where_sql}
            """,
            tuple(params),
        )

        total = int(count_row["total"]) if count_row else 0

        rows = fetch_all(
            EXPENSE_SELECT
            + f"""
            {where_sql}
            ORDER BY e.created_at DESC, e.id DESC
            LIMIT %s OFFSET %s
            """,
            tuple(params + [per_page, offset]),
        )

        return [Expense._row_to_expense(row) for row in rows], total

    @staticmethod
    def create(
        user_id,
        category_id,
        amount,
        description,
        expense_date,
        receipt_path=None,
        current_stage="manager",
        required_stages="manager",
        policy_violations=None,
        risk_level="none",
        risk_reasons=None,
        receipt_hash=None,
    ):
        """Create an expense with enterprise workflow metadata."""

        expense_id, _ = execute(
            """
            INSERT INTO expenses
                (
                    user_id,
                    category_id,
                    amount,
                    description,
                    date,
                    receipt_path,
                    status,
                    current_stage,
                    required_stages,
                    policy_violations,
                    risk_level,
                    risk_reasons,
                    receipt_hash
                )
            VALUES
                (
                    %s, %s, %s, %s, %s, %s, 'pending',
                    %s, %s, %s, %s, %s, %s
                )
            """,
            (
                user_id,
                category_id,
                amount,
                description,
                expense_date,
                receipt_path,
                current_stage,
                required_stages,
                policy_violations,
                risk_level,
                risk_reasons,
                receipt_hash,
            ),
        )

        return Expense.get_by_id(expense_id)

    @staticmethod
    def get_by_id(expense_id):
        row = fetch_one(
            EXPENSE_SELECT + " WHERE e.id = %s",
            (expense_id,),
        )

        return Expense._row_to_expense(row) if row else None

    @staticmethod
    def get_by_user(user_id, page=None, per_page=25):
        """Return user expenses, optionally paginated."""

        if page is None:
            rows = fetch_all(
                EXPENSE_SELECT
                + """
                WHERE e.user_id = %s
                ORDER BY e.date DESC, e.created_at DESC
                """,
                (user_id,),
            )

            return [Expense._row_to_expense(row) for row in rows]

        page = max(int(page or 1), 1)
        per_page = max(min(int(per_page or 25), 100), 1)
        offset = (page - 1) * per_page

        count_row = fetch_one(
            "SELECT COUNT(*) AS total FROM expenses WHERE user_id = %s",
            (user_id,),
        )

        total = int(count_row["total"]) if count_row else 0

        rows = fetch_all(
            EXPENSE_SELECT
            + """
              WHERE e.user_id = %s
              ORDER BY e.date DESC, e.created_at DESC
              LIMIT %s OFFSET %s
              """,
            (user_id, per_page, offset),
        )

        return [Expense._row_to_expense(row) for row in rows], total

    @staticmethod
    def get_all():
        rows = fetch_all(
            EXPENSE_SELECT + " ORDER BY e.created_at DESC"
        )

        return [Expense._row_to_expense(row) for row in rows]

    @staticmethod
    def overview_stats(user_ids=None):
        """Return expense summary statistics."""

        conditions = []
        params = []

        if user_ids is not None:
            if not user_ids:
                return {
                    "total_count": 0,
                    "pending_count": 0,
                    "approved_count": 0,
                    "rejected_count": 0,
                    "total_amount": 0.0,
                    "pending_amount": 0.0,
                    "approved_amount": 0.0,
                    "rejected_amount": 0.0,
                }

            placeholders = ", ".join(["%s"] * len(user_ids))
            conditions.append(f"user_id IN ({placeholders})")
            params.extend(user_ids)

        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        row = fetch_one(
            f"""
            SELECT
                COUNT(*) AS total_count,
                COALESCE(
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END),
                    0
                ) AS pending_count,
                COALESCE(
                    SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END),
                    0
                ) AS approved_count,
                COALESCE(
                    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END),
                    0
                ) AS rejected_count,
                COALESCE(SUM(amount), 0) AS total_amount,
                COALESCE(
                    SUM(CASE WHEN status = 'pending' THEN amount ELSE 0 END),
                    0
                ) AS pending_amount,
                COALESCE(
                    SUM(CASE WHEN status = 'approved' THEN amount ELSE 0 END),
                    0
                ) AS approved_amount,
                COALESCE(
                    SUM(CASE WHEN status = 'rejected' THEN amount ELSE 0 END),
                    0
                ) AS rejected_amount
            FROM expenses
            {where_sql}
            """,
            tuple(params),
        )

        return {
            "total_count": int(row["total_count"] or 0),
            "pending_count": int(row["pending_count"] or 0),
            "approved_count": int(row["approved_count"] or 0),
            "rejected_count": int(row["rejected_count"] or 0),
            "total_amount": float(row["total_amount"] or 0),
            "pending_amount": float(row["pending_amount"] or 0),
            "approved_amount": float(row["approved_amount"] or 0),
            "rejected_amount": float(row["rejected_amount"] or 0),
        }

    @staticmethod
    def update_workflow(
        expense_id,
        status=None,
        current_stage=None,
        required_stages=None,
        policy_violations=None,
        risk_level=None,
        risk_reasons=None,
        reopen_count=None,
        receipt_hash=None,
    ):
        """Update enterprise workflow fields."""

        updates = {
            "status": status,
            "current_stage": current_stage,
            "required_stages": required_stages,
            "policy_violations": policy_violations,
            "risk_level": risk_level,
            "risk_reasons": risk_reasons,
            "reopen_count": reopen_count,
            "receipt_hash": receipt_hash,
        }

        fields = []
        params = []

        for column, value in updates.items():
            if value is not None:
                fields.append(f"{column} = %s")
                params.append(value)

        if not fields:
            return False

        params.append(expense_id)

        _, count = execute(
            f"""
            UPDATE expenses
            SET {', '.join(fields)}
            WHERE id = %s
            """,
            tuple(params),
        )

        return count > 0

    @staticmethod
    def update_status(expense_id, status):
        _, count = execute(
            "UPDATE expenses SET status = %s WHERE id = %s",
            (status, expense_id),
        )

        return count > 0

    @staticmethod
    def get_monthly_totals():
        row = fetch_one(
            """
            SELECT
                COALESCE(
                    SUM(
                        CASE
                            WHEN YEAR(date) = YEAR(CURDATE())
                             AND MONTH(date) = MONTH(CURDATE())
                            THEN amount
                            ELSE 0
                        END
                    ),
                    0
                ) AS current_month,

                COALESCE(
                    SUM(
                        CASE
                            WHEN YEAR(date) = YEAR(
                                DATE_SUB(CURDATE(), INTERVAL 1 MONTH)
                            )
                            AND MONTH(date) = MONTH(
                                DATE_SUB(CURDATE(), INTERVAL 1 MONTH)
                            )
                            THEN amount
                            ELSE 0
                        END
                    ),
                    0
                ) AS previous_month
            FROM expenses
            WHERE status = 'approved'
            """
        )

        return {
            "current_month": float(row["current_month"] or 0),
            "previous_month": float(row["previous_month"] or 0),
        }

    @staticmethod
    def get_totals_by_department():
        rows = fetch_all(
            """
            SELECT
                u.department,
                COALESCE(SUM(e.amount), 0) AS total
            FROM expenses e
            JOIN users u ON e.user_id = u.id
            WHERE e.status = 'approved'
            GROUP BY u.department
            ORDER BY total DESC
            """
        )

        return [
            {
                "department": row["department"],
                "total": float(row["total"]),
            }
            for row in rows
        ]

    @staticmethod
    def get_totals_by_category():
        rows = fetch_all(
            """
            SELECT
                c.name AS category,
                COALESCE(SUM(e.amount), 0) AS total
            FROM expenses e
            JOIN categories c ON e.category_id = c.id
            WHERE e.status = 'approved'
            GROUP BY c.name
            ORDER BY total DESC
            """
        )

        return [
            {
                "category": row["category"],
                "total": float(row["total"]),
            }
            for row in rows
        ]

    @staticmethod
    def get_six_month_trend():
        rows = fetch_all(
            """
            SELECT
                DATE_FORMAT(e.date, '%Y-%m') AS month_label,
                COALESCE(SUM(e.amount), 0) AS total
            FROM expenses e
            WHERE e.status = 'approved'
              AND e.date >= DATE_FORMAT(
                    DATE_SUB(CURDATE(), INTERVAL 5 MONTH),
                    '%Y-%m-01'
                  )
            GROUP BY DATE_FORMAT(e.date, '%Y-%m')
            ORDER BY month_label ASC
            """
        )

        return [
            {
                "month": row["month_label"],
                "total": float(row["total"]),
            }
            for row in rows
        ]

    @staticmethod
    def get_all_for_csv():
        rows = fetch_all(
            """
            SELECT
                e.id,
                u.name AS employee_name,
                u.email,
                u.department,
                c.name AS category,
                e.amount,
                e.description,
                e.date,
                e.status,
                e.created_at
            FROM expenses e
            JOIN users u ON e.user_id = u.id
            JOIN categories c ON e.category_id = c.id
            ORDER BY e.date DESC, e.id DESC
            """
        )

        return rows