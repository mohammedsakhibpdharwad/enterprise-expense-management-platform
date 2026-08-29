from models.database import execute, fetch_all, fetch_one


class Department:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id")
        self.name = kwargs.get("name")
        self.manager_id = kwargs.get("manager_id")
        self.monthly_budget = kwargs.get("monthly_budget")
        self.manager_name = kwargs.get("manager_name")

    @staticmethod
    def all():
        rows = fetch_all(
            """
            SELECT d.*, u.name AS manager_name
            FROM departments d
            LEFT JOIN users u ON u.id = d.manager_id
            ORDER BY d.name
            """
        )
        return [Department(**row) for row in rows]

    @staticmethod
    def get(dept_id):
        row = fetch_one(
            """
            SELECT d.*, u.name AS manager_name
            FROM departments d
            LEFT JOIN users u ON u.id = d.manager_id
            WHERE d.id = %s
            """,
            (dept_id,),
        )
        return Department(**row) if row else None

    @staticmethod
    def create(name, manager_id=None, monthly_budget=0):
        dept_id, _ = execute(
            "INSERT INTO departments (name, manager_id, monthly_budget) VALUES (%s, %s, %s)",
            (name, manager_id or None, monthly_budget or 0),
        )
        return Department.get(dept_id)

    @staticmethod
    def update(dept_id, name, manager_id=None, monthly_budget=0):
        execute(
            "UPDATE departments SET name = %s, manager_id = %s, monthly_budget = %s WHERE id = %s",
            (name, manager_id or None, monthly_budget or 0, dept_id),
        )
        if manager_id:
            execute(
                "UPDATE users SET manager_id = %s WHERE department_id = %s AND role = 'employee'",
                (manager_id, dept_id),
            )
        execute("UPDATE users SET department = %s WHERE department_id = %s", (name, dept_id))
