from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from models.database import execute, fetch_all, fetch_one
from utils.rbac import VALID_ROLES


class User(UserMixin):
    """User model backed by the MySQL users table."""

    def __init__(
        self,
        id,
        name,
        email,
        password_hash,
        role,
        department,
        employee_code=None,
        department_id=None,
        manager_id=None,
        is_active=1,
        **_extra,
    ):
        self.id = id
        self.name = name
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.department = department
        self.employee_code = employee_code
        self.department_id = department_id
        self.manager_id = manager_id
        self.account_active = bool(is_active)

    @staticmethod
    def _from_row(row):
        if not row:
            return None
        return User(**row)

    @staticmethod
    def get_by_id(user_id):
        row = fetch_one(
            """
            SELECT id, name, email, password_hash, role, department,
                   employee_code, department_id, manager_id, is_active
            FROM users
            WHERE id = %s
            """,
            (user_id,),
        )
        return User._from_row(row)

    @staticmethod
    def get_by_email(email):
        row = fetch_one(
            """
            SELECT id, name, email, password_hash, role, department,
                   employee_code, department_id, manager_id, is_active
            FROM users
            WHERE email = %s
            """,
            (email,),
        )
        return User._from_row(row)

    @staticmethod
    def create(
        name,
        email,
        password,
        role="employee",
        department="General",
        department_id=None,
        manager_id=None,
        is_active=1,
        employee_code=None,
    ):
        """Create a user while supporting all enterprise user fields."""

        if role not in VALID_ROLES:
            role = "employee"

        password_hash = generate_password_hash(password)

        user_id, _ = execute(
            """
            INSERT INTO users
                (name, email, password_hash, role, department,
                 employee_code, department_id, manager_id, is_active)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                name,
                email,
                password_hash,
                role,
                department,
                employee_code,
                department_id,
                manager_id,
                is_active,
            ),
        )

        if not employee_code:
            employee_code = f"EMP{user_id:04d}"
            execute(
                "UPDATE users SET employee_code = %s WHERE id = %s",
                (employee_code, user_id),
            )

        return User.get_by_id(user_id)

    @staticmethod
    def search(q=None, department_id=None, role=None, is_active=None, page=1, per_page=25):
        """Search users for Super Admin employee management."""

        page = max(int(page or 1), 1)
        per_page = max(min(int(per_page or 25), 100), 1)
        offset = (page - 1) * per_page

        conditions = []
        params = []

        if q:
            like = f"%{q.strip()}%"
            conditions.append(
                "(name LIKE %s OR email LIKE %s OR employee_code LIKE %s)"
            )
            params.extend([like, like, like])

        if department_id:
            conditions.append("department_id = %s")
            params.append(int(department_id))

        if role:
            conditions.append("role = %s")
            params.append(role)

        if is_active not in (None, ""):
            conditions.append("is_active = %s")
            params.append(1 if str(is_active) == "1" else 0)

        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        total_row = fetch_one(
            f"SELECT COUNT(*) AS total FROM users {where_sql}",
            tuple(params),
        )
        total = int(total_row["total"]) if total_row else 0

        rows = fetch_all(
            f"""
            SELECT id, name, email, password_hash, role, department,
                     employee_code, department_id,
manager_id, is_active
            FROM users
            {where_sql}
            ORDER BY name, id
            LIMIT %s OFFSET %s
            """,
            tuple(params + [per_page, offset]),
        )

        return [User._from_row(row) for row in rows], total

    @staticmethod
    def team_member_ids(manager_id):
        """Return employee IDs directly assigned to a manager."""

        rows = fetch_all(
            """
            SELECT id
            FROM users
            WHERE manager_id = %s
              AND role = 'employee'
            ORDER BY id
            """,
            (manager_id,),
        )
        return [int(row["id"]) for row in rows]

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
