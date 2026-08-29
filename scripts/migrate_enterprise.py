"""Idempotent enterprise schema upgrade. Never drops tables or deletes expense/user data."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.security import generate_password_hash

from models.database import get_db_connection


def column_exists(cursor, table, column):
    cursor.execute(
        """
        SELECT COUNT(*) AS c FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
        """,
        (table, column),
    )
    return cursor.fetchone()["c"] > 0


def table_exists(cursor, table):
    cursor.execute(
        """
        SELECT COUNT(*) AS c FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
        """,
        (table,),
    )
    return cursor.fetchone()["c"] > 0


def index_exists(cursor, table, index_name):
    cursor.execute(
        """
        SELECT COUNT(*) AS c FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND INDEX_NAME = %s
        """,
        (table, index_name),
    )
    return cursor.fetchone()["c"] > 0


def add_column(cursor, table, column, ddl):
    if not column_exists(cursor, table, column):
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def add_index(cursor, table, index_name, ddl):
    if not index_exists(cursor, table, index_name):
        cursor.execute(ddl)


def migrate():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("ALTER TABLE users MODIFY COLUMN role VARCHAR(32) NOT NULL DEFAULT 'employee'")
        cursor.execute("UPDATE users SET role = 'super_admin' WHERE role IN ('admin')")

        add_column(cursor, "users", "employee_code", "employee_code VARCHAR(32) NULL")
        add_column(cursor, "users", "department_id", "department_id INT NULL")
        add_column(cursor, "users", "manager_id", "manager_id INT NULL")
        add_column(cursor, "users", "is_active", "is_active TINYINT(1) NOT NULL DEFAULT 1")

        if not table_exists(cursor, "departments"):
            cursor.execute(
                """
                CREATE TABLE departments (
                  id INT AUTO_INCREMENT PRIMARY KEY,
                  name VARCHAR(100) NOT NULL UNIQUE,
                  manager_id INT NULL,
                  monthly_budget DECIMAL(12, 2) NULL DEFAULT 0,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

        if not table_exists(cursor, "approval_rules"):
            cursor.execute(
                """
                CREATE TABLE approval_rules (
                  id INT AUTO_INCREMENT PRIMARY KEY,
                  name VARCHAR(100) NOT NULL,
                  min_amount DECIMAL(12, 2) NOT NULL DEFAULT 0,
                  max_amount DECIMAL(12, 2) NOT NULL,
                  require_manager TINYINT(1) NOT NULL DEFAULT 1,
                  require_finance TINYINT(1) NOT NULL DEFAULT 0,
                  require_super TINYINT(1) NOT NULL DEFAULT 0,
                  is_active TINYINT(1) NOT NULL DEFAULT 1
                )
                """
            )

        if not table_exists(cursor, "expense_policies"):
            cursor.execute(
                """
                CREATE TABLE expense_policies (
                  id INT AUTO_INCREMENT PRIMARY KEY,
                  name VARCHAR(120) NOT NULL,
                  policy_type VARCHAR(40) NOT NULL,
                  category_id INT NULL,
                  department_id INT NULL,
                  threshold DECIMAL(12, 2) NULL,
                  extra_value VARCHAR(120) NULL,
                  is_active TINYINT(1) NOT NULL DEFAULT 1
                )
                """
            )

        add_column(cursor, "expenses", "current_stage", "current_stage VARCHAR(32) NOT NULL DEFAULT 'manager'")
        add_column(cursor, "expenses", "required_stages", "required_stages VARCHAR(120) NOT NULL DEFAULT 'manager'")
        add_column(cursor, "expenses", "policy_violations", "policy_violations TEXT NULL")
        add_column(cursor, "expenses", "risk_level", "risk_level VARCHAR(16) NOT NULL DEFAULT 'none'")
        add_column(cursor, "expenses", "risk_reasons", "risk_reasons TEXT NULL")
        add_column(cursor, "expenses", "reopen_count", "reopen_count INT NOT NULL DEFAULT 0")
        add_column(cursor, "expenses", "receipt_hash", "receipt_hash VARCHAR(64) NULL")

        if not table_exists(cursor, "approval_audit"):
            cursor.execute(
                """
                CREATE TABLE approval_audit (
                  id INT AUTO_INCREMENT PRIMARY KEY,
                  expense_id INT NOT NULL,
                  action VARCHAR(40) NOT NULL,
                  previous_status VARCHAR(32) NULL,
                  new_status VARCHAR(32) NULL,
                  previous_stage VARCHAR(32) NULL,
                  new_stage VARCHAR(32) NULL,
                  performed_by INT NULL,
                  comment TEXT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  INDEX idx_audit_expense (expense_id, created_at),
                  CONSTRAINT fk_audit_expense FOREIGN KEY (expense_id) REFERENCES expenses(id) ON DELETE CASCADE
                )
                """
            )

        if not table_exists(cursor, "notifications"):
            cursor.execute(
                """
                CREATE TABLE notifications (
                  id INT AUTO_INCREMENT PRIMARY KEY,
                  user_id INT NOT NULL,
                  title VARCHAR(150) NOT NULL,
                  message VARCHAR(500) NOT NULL,
                  link VARCHAR(255) NULL,
                  is_read TINYINT(1) NOT NULL DEFAULT 0,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  INDEX idx_notifications_user (user_id, is_read, created_at),
                  CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
            )

        add_index(cursor, "users", "idx_users_department_id", "CREATE INDEX idx_users_department_id ON users (department_id)")
        add_index(cursor, "users", "idx_users_manager_id", "CREATE INDEX idx_users_manager_id ON users (manager_id)")
        add_index(cursor, "users", "idx_users_employee_code", "CREATE INDEX idx_users_employee_code ON users (employee_code)")
        add_index(cursor, "expenses", "idx_expenses_stage", "CREATE INDEX idx_expenses_stage ON expenses (current_stage, status)")
        add_index(cursor, "expenses", "idx_expenses_amount", "CREATE INDEX idx_expenses_amount ON expenses (amount)")
        add_index(cursor, "expenses", "idx_expenses_receipt_hash", "CREATE INDEX idx_expenses_receipt_hash ON expenses (receipt_hash)")

        _seed_reference_data(cursor)
        _backfill_departments(cursor)
        _assign_employee_codes(cursor)
        _ensure_demo_roles(cursor)

        connection.commit()
        print("Enterprise migration complete.")
    finally:
        cursor.close()
        connection.close()


def _seed_reference_data(cursor):
    cursor.execute("SELECT COUNT(*) AS c FROM approval_rules")
    if cursor.fetchone()["c"] == 0:
        cursor.executemany(
            """
            INSERT INTO approval_rules
            (name, min_amount, max_amount, require_manager, require_finance, require_super, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, 1)
            """,
            [
                ("Low amount — Manager only", 0, 200.00, 1, 0, 0),
                ("Medium amount — Manager + Finance", 200.01, 1000.00, 1, 1, 0),
                ("High amount — Manager + Finance + Super Admin", 1000.01, 999999.99, 1, 1, 1),
            ],
        )

    cursor.execute("SELECT COUNT(*) AS c FROM expense_policies")
    if cursor.fetchone()["c"] == 0:
        cursor.executemany(
            """
            INSERT INTO expense_policies
            (name, policy_type, category_id, department_id, threshold, extra_value, is_active)
            VALUES (%s, %s, NULL, NULL, %s, %s, 1)
            """,
            [
                ("Receipt required above $75", "receipt_required", 75.00, None),
                ("Meals daily limit $80", "daily_limit", 80.00, "Meals"),
                ("Max single expense $5000", "max_amount", 5000.00, None),
                ("Travel category cap $2500", "category_max", 2500.00, "Travel"),
            ],
        )


def _backfill_departments(cursor):
    cursor.execute("SELECT DISTINCT department FROM users WHERE department IS NOT NULL AND department <> ''")
    names = [row["department"] for row in cursor.fetchall()]
    for name in names:
        cursor.execute("INSERT IGNORE INTO departments (name, monthly_budget) VALUES (%s, %s)", (name, 5000))
    cursor.execute(
        """
        UPDATE users u
        JOIN departments d ON d.name = u.department
        SET u.department_id = d.id
        WHERE u.department_id IS NULL
        """
    )


def _assign_employee_codes(cursor):
    cursor.execute("SELECT id FROM users WHERE employee_code IS NULL OR employee_code = '' ORDER BY id")
    for row in cursor.fetchall():
        code = f"EMP{row['id']:04d}"
        cursor.execute("UPDATE users SET employee_code = %s WHERE id = %s", (code, row["id"]))


def _ensure_user(cursor, name, email, role, department, password="Password123!"):
    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    row = cursor.fetchone()
    if row:
        cursor.execute(
            "UPDATE users SET role = %s, is_active = 1 WHERE id = %s AND email = %s",
            (role, row["id"], email),
        )
        return row["id"]
    cursor.execute("SELECT id FROM departments WHERE name = %s", (department,))
    dept = cursor.fetchone()
    if not dept:
        cursor.execute("INSERT INTO departments (name, monthly_budget) VALUES (%s, 5000)", (department,))
        cursor.execute("SELECT LAST_INSERT_ID() AS id")
        dept_id = cursor.fetchone()["id"]
    else:
        dept_id = dept["id"]
    cursor.execute(
        """
        INSERT INTO users (name, email, password_hash, role, department, department_id, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, 1)
        """,
        (name, email, generate_password_hash(password), role, department, dept_id),
    )
    cursor.execute("SELECT LAST_INSERT_ID() AS id")
    user_id = cursor.fetchone()["id"]
    cursor.execute("UPDATE users SET employee_code = %s WHERE id = %s", (f"EMP{user_id:04d}", user_id))
    return user_id


def _ensure_demo_roles(cursor):
    """Add demo manager/finance accounts without changing existing test passwords."""
    manager_id = _ensure_user(cursor, "Priya Manager", "manager@example.com", "manager", "Engineering")
    finance_id = _ensure_user(cursor, "Finance Admin", "finance@example.com", "finance_admin", "Finance")
    super_id = None
    cursor.execute(
        "SELECT id FROM users WHERE email IN ('admin@example.com', 'admin@expensehub.com') LIMIT 1"
    )
    super_row = cursor.fetchone()
    if super_row:
        super_id = super_row["id"]
        cursor.execute("UPDATE users SET role = 'super_admin' WHERE id = %s", (super_id,))

    cursor.execute("UPDATE departments SET manager_id = %s WHERE name = 'Engineering'", (manager_id,))
    cursor.execute(
        """
        UPDATE users SET manager_id = %s
        WHERE role = 'employee' AND (department = 'Engineering' OR department_id IN (
            SELECT id FROM (SELECT id FROM departments WHERE name = 'Engineering') d
        )) AND id <> %s
        """,
        (manager_id, manager_id),
    )
    return finance_id, super_id


def needs_migration():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        return not table_exists(cursor, "approval_audit")
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    migrate()
