from models.database import get_db_connection


class Category:
    """Expense category model."""

    def __init__(self, id, name):
        self.id = id
        self.name = name

    @staticmethod
    def get_all():
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, name FROM categories ORDER BY name")
            rows = cursor.fetchall()
            return [Category(**row) for row in rows]
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_by_id(category_id):
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, name FROM categories WHERE id = %s", (category_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return Category(**row)
        finally:
            cursor.close()
            connection.close()
