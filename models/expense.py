from decimal import Decimal

from models.database import get_db_connection


class Expense:
    """Expense model backed by the MySQL expenses table."""

    def __init__(
        self,
        id,
        user_id,
        category_id,
        amount,
        description,
        expense_date,
        receipt_path,
        status,
        created_at,
        user_name=None,
        user_email=None,
        department=None,
        category_name=None,
    ):
        self.id = id
        self.user_id = user_id
        self.category_id = category_id
        self.amount = Decimal(str(amount))
        self.description = description
        self.date = expense_date
        self.receipt_path = receipt_path
        self.status = status
        self.created_at = created_at
        self.user_name = user_name
        self.user_email = user_email
        self.department = department
        self.category_name = category_name

    @staticmethod
    def _row_to_expense(row):
        data = dict(row)
        if "date" in data and "expense_date" not in data:
            data["expense_date"] = data.pop("date")
        return Expense(**data)

    @staticmethod
    def create(user_id, category_id, amount, description, expense_date, receipt_path=None):
        connection = get_db_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO expenses (user_id, category_id, amount, description, date, receipt_path, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'pending')
                """,
                (user_id, category_id, amount, description, expense_date, receipt_path),
            )
            connection.commit()
            return Expense.get_by_id(cursor.lastrowid)
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_by_id(expense_id):
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT e.id, e.user_id, e.category_id, e.amount, e.description, e.date,
                       e.receipt_path, e.status, e.created_at,
                       u.name AS user_name, u.email AS user_email, u.department,
                       c.name AS category_name
                FROM expenses e
                JOIN users u ON e.user_id = u.id
                JOIN categories c ON e.category_id = c.id
                WHERE e.id = %s
                """,
                (expense_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return Expense._row_to_expense(row)
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_by_user(user_id):
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT e.id, e.user_id, e.category_id, e.amount, e.description, e.date,
                       e.receipt_path, e.status, e.created_at,
                       c.name AS category_name
                FROM expenses e
                JOIN categories c ON e.category_id = c.id
                WHERE e.user_id = %s
                ORDER BY e.date DESC, e.created_at DESC
                """,
                (user_id,),
            )
            return [Expense._row_to_expense(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_all():
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT e.id, e.user_id, e.category_id, e.amount, e.description, e.date,
                       e.receipt_path, e.status, e.created_at,
                       u.name AS user_name, u.email AS user_email, u.department,
                       c.name AS category_name
                FROM expenses e
                JOIN users u ON e.user_id = u.id
                JOIN categories c ON e.category_id = c.id
                ORDER BY e.created_at DESC
                """
            )
            return [Expense._row_to_expense(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def update_status(expense_id, status):
        connection = get_db_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                "UPDATE expenses SET status = %s WHERE id = %s",
                (status, expense_id),
            )
            connection.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_monthly_totals():
        """Return total approved expenses for current and previous month."""
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT
                    COALESCE(SUM(CASE
                        WHEN YEAR(date) = YEAR(CURDATE()) AND MONTH(date) = MONTH(CURDATE())
                        THEN amount ELSE 0 END), 0) AS current_month,
                    COALESCE(SUM(CASE
                        WHEN YEAR(date) = YEAR(DATE_SUB(CURDATE(), INTERVAL 1 MONTH))
                         AND MONTH(date) = MONTH(DATE_SUB(CURDATE(), INTERVAL 1 MONTH))
                        THEN amount ELSE 0 END), 0) AS previous_month
                FROM expenses
                WHERE status = 'approved'
                """
            )
            row = cursor.fetchone()
            return {
                "current_month": float(row["current_month"]),
                "previous_month": float(row["previous_month"]),
            }
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_totals_by_department():
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT u.department, COALESCE(SUM(e.amount), 0) AS total
                FROM expenses e
                JOIN users u ON e.user_id = u.id
                WHERE e.status = 'approved'
                GROUP BY u.department
                ORDER BY total DESC
                """
            )
            return [
                {"department": row["department"], "total": float(row["total"])}
                for row in cursor.fetchall()
            ]
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_totals_by_category():
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT c.name AS category, COALESCE(SUM(e.amount), 0) AS total
                FROM expenses e
                JOIN categories c ON e.category_id = c.id
                WHERE e.status = 'approved'
                GROUP BY c.name
                ORDER BY total DESC
                """
            )
            return [
                {"category": row["category"], "total": float(row["total"])}
                for row in cursor.fetchall()
            ]
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_six_month_trend():
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT DATE_FORMAT(e.date, '%Y-%m') AS month_label,
                       COALESCE(SUM(e.amount), 0) AS total
                FROM expenses e
                WHERE e.status = 'approved'
                  AND e.date >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 5 MONTH), '%Y-%m-01')
                GROUP BY DATE_FORMAT(e.date, '%Y-%m')
                ORDER BY month_label ASC
                """
            )
            rows = cursor.fetchall()
            return [
                {"month": row["month_label"], "total": float(row["total"])}
                for row in rows
            ]
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_all_for_csv():
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT e.id, u.name AS employee_name, u.email, u.department,
                       c.name AS category, e.amount, e.description, e.date,
                       e.status, e.created_at
                FROM expenses e
                JOIN users u ON e.user_id = u.id
                JOIN categories c ON e.category_id = c.id
                ORDER BY e.date DESC, e.id DESC
                """
            )
            return cursor.fetchall()
        finally:
            cursor.close()
            connection.close()
