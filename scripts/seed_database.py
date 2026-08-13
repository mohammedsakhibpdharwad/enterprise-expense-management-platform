"""
Seed the database with demo users and expenses for charts and dashboards.

Run from project root:
    python scripts/seed_database.py
"""

import os
import sys
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import get_db_connection

ADMIN_EMAIL = "admin@expensehub.com"
EMPLOYEE_EMAILS = [
    ("alice@expensehub.com", "Alice Johnson", "Engineering"),
    ("bob@expensehub.com", "Bob Smith", "Marketing"),
    ("carol@expensehub.com", "Carol Davis", "Sales"),
]
DEFAULT_PASSWORD = "Password123!"


def get_category_map(cursor):
    cursor.execute("SELECT id, name FROM categories")
    return {row[1]: row[0] for row in cursor.fetchall()}


def ensure_user(cursor, name, email, role, department, password):
    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    row = cursor.fetchone()
    if row:
        return row[0]

    password_hash = generate_password_hash(password)
    cursor.execute(
        """
        INSERT INTO users (name, email, password_hash, role, department)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (name, email, password_hash, role, department),
    )
    return cursor.lastrowid


def seed_expenses(cursor, user_id, category_map, entries):
    for category_name, amount, description, expense_date, status in entries:
        cursor.execute(
            """
            INSERT INTO expenses (user_id, category_id, amount, description, date, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (user_id, category_map[category_name], amount, description, expense_date, status),
        )


def seed_if_empty():
    """Seed demo data when the expenses table has no rows."""
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM expenses")
        if cursor.fetchone()[0] > 0:
            return False
    finally:
        cursor.close()
        connection.close()

    main()
    return True


def main():
    today = date.today()

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        category_map = get_category_map(cursor)
        if not category_map:
            print("No categories found. Run schema.sql first.")
            return

        ensure_user(
            cursor,
            "System Admin",
            ADMIN_EMAIL,
            "admin",
            "Finance",
            DEFAULT_PASSWORD,
        )

        employee_ids = []
        for email, name, department in EMPLOYEE_EMAILS:
            employee_ids.append(
                ensure_user(cursor, name, email, "employee", department, DEFAULT_PASSWORD)
            )

        cursor.execute("SELECT COUNT(*) FROM expenses")
        expense_count = cursor.fetchone()[0]
        if expense_count == 0:
            alice_id, bob_id, carol_id = employee_ids

            seed_expenses(
                cursor,
                alice_id,
                category_map,
                [
                    ("Software", 249.99, "JetBrains license", today.replace(day=5), "approved"),
                    ("Travel", 420.00, "Client site visit", today.replace(day=12), "approved"),
                    ("Meals", 38.50, "Team lunch", today.replace(day=18), "pending"),
                    ("Office Supplies", 67.25, "Keyboard and mouse", today - timedelta(days=32), "approved"),
                    ("Training", 199.00, "Python workshop", today - timedelta(days=65), "approved"),
                    ("Travel", 310.00, "Conference travel", today - timedelta(days=95), "approved"),
                    ("Software", 89.00, "Cloud storage plan", today - timedelta(days=125), "approved"),
                ],
            )

            seed_expenses(
                cursor,
                bob_id,
                category_map,
                [
                    ("Meals", 54.75, "Client dinner", today.replace(day=8), "approved"),
                    ("Travel", 180.00, "Campaign photoshoot trip", today.replace(day=15), "approved"),
                    ("Office Supplies", 42.10, "Banner printing", today.replace(day=20), "pending"),
                    ("Software", 129.00, "Design tool subscription", today - timedelta(days=28), "approved"),
                    ("Travel", 265.00, "Industry event", today - timedelta(days=58), "approved"),
                    ("Meals", 33.40, "Working session catering", today - timedelta(days=88), "approved"),
                ],
            )

            seed_expenses(
                cursor,
                carol_id,
                category_map,
                [
                    ("Travel", 512.00, "Sales roadshow", today.replace(day=3), "approved"),
                    ("Meals", 46.80, "Prospect lunch", today.replace(day=10), "approved"),
                    ("Other", 75.00, "Client gift baskets", today.replace(day=22), "rejected"),
                    ("Office Supplies", 29.99, "Presentation materials", today - timedelta(days=35), "approved"),
                    ("Training", 150.00, "Negotiation skills course", today - timedelta(days=70), "approved"),
                    ("Travel", 388.00, "Regional sales visit", today - timedelta(days=100), "approved"),
                ],
            )

            print(f"Inserted sample expenses for {len(employee_ids)} employees.")
        else:
            print(f"Expenses already exist ({expense_count}). Skipping expense seed.")

        connection.commit()
        print("Seed complete.")
        print(f"Admin login:    {ADMIN_EMAIL} / {DEFAULT_PASSWORD}")
        print(f"Employee login: {EMPLOYEE_EMAILS[0][0]} / {DEFAULT_PASSWORD}")
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
