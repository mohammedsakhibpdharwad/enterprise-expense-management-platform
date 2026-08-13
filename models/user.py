from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from models.database import get_db_connection


class User(UserMixin):
    """User model backed by the MySQL users table."""

    def __init__(self, id, name, email, password_hash, role, department):
        self.id = id
        self.name = name
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.department = department

    @staticmethod
    def get_by_id(user_id):
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT id, name, email, password_hash, role, department "
                "FROM users WHERE id = %s",
                (user_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return User(**row)
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def get_by_email(email):
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT id, name, email, password_hash, role, department "
                "FROM users WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return User(**row)
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def create(name, email, password, role, department):
        password_hash = generate_password_hash(password)
        connection = get_db_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (name, email, password_hash, role, department) "
                "VALUES (%s, %s, %s, %s, %s)",
                (name, email, password_hash, role, department),
            )
            connection.commit()
            return User.get_by_id(cursor.lastrowid)
        finally:
            cursor.close()
            connection.close()

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
