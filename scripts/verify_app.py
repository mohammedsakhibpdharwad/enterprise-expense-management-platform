"""Quick verification of core app components without a running server."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_expense_row_mapping():
    from models.expense import Expense

    row = {
        "id": 1,
        "user_id": 2,
        "category_id": 3,
        "amount": 99.5,
        "description": "Test expense",
        "date": "2026-08-01",
        "receipt_path": None,
        "status": "pending",
        "created_at": "2026-08-01 12:00:00",
        "category_name": "Travel",
    }
    expense = Expense._row_to_expense(row)
    assert str(expense.date) == "2026-08-01"
    assert float(expense.amount) == 99.5
    print("PASS: Expense row mapping")


def test_expense_alias_mapping():
    from models.expense import Expense

    row = {
        "id": 2,
        "user_id": 2,
        "category_id": 3,
        "amount": 10,
        "description": "Alias test",
        "expense_date": "2026-08-02",
        "receipt_path": None,
        "status": "pending",
        "created_at": "2026-08-02 12:00:00",
    }
    expense = Expense._row_to_expense(row)
    assert str(expense.date) == "2026-08-02"
    print("PASS: expense_date alias mapping")


def test_validators():
    from utils.validators import validate_expense_submission

    errors, _, amount, desc, _ = validate_expense_submission("1", "25.50", "Lunch", "2026-08-01", {1})
    assert not errors
    assert amount == 25.5
    assert desc == "Lunch"

    errors, _, _, _, _ = validate_expense_submission("", "-5", "", "bad-date", set())
    assert errors
    print("PASS: expense validators")


def test_app_factory():
    from app import create_app

    app = create_app()
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    expected = {
        "/",
        "/login",
        "/signup",
        "/logout",
        "/admin/dashboard",
        "/admin/analytics",
        "/admin/analytics/download",
        "/admin/api/analytics/summary",
        "/employee/dashboard",
    }
    missing = expected - rules
    assert not missing, f"Missing routes: {missing}"
    print("PASS: Flask app factory and routes")


if __name__ == "__main__":
    test_expense_row_mapping()
    test_expense_alias_mapping()
    test_validators()
    test_app_factory()
    print("All verification checks passed.")
