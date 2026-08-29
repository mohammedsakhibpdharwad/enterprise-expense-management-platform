"""Quick verification of Phase 5 core components."""

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
    from datetime import date, timedelta

    from utils.validators import validate_expense_submission

    errors, _, amount, desc, parsed = validate_expense_submission(
        "1", "25.50", "Lunch", date.today().isoformat(), {1}
    )
    assert not errors, errors
    assert amount == 25.5
    assert desc == "Lunch"
    assert parsed == date.today()

    future = (date.today() + timedelta(days=1)).isoformat()
    errors, _, _, _, _ = validate_expense_submission("", "-5", "", future, set())
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


def test_role_protection():
    from app import create_app

    app = create_app()
    client = app.test_client()
    response = client.get("/admin/dashboard", follow_redirects=False)
    assert response.status_code in (302, 401)
    response = client.get("/employee/dashboard", follow_redirects=False)
    assert response.status_code in (302, 401)
    print("PASS: unauthenticated users redirected from protected routes")


if __name__ == "__main__":
    test_expense_row_mapping()
    test_expense_alias_mapping()
    test_validators()
    test_app_factory()
    test_role_protection()
    print("All verification checks passed.")
