"""Server-side validation helpers."""

from datetime import date, datetime

MAX_EXPENSE_AMOUNT = 999_999.99
MAX_DESCRIPTION_LENGTH = 500


def validate_expense_submission(category_id, amount, description, expense_date, valid_category_ids):
    """Validate expense form fields. Returns (errors, cleaned values)."""
    errors = []
    category_id_int = None
    amount_value = None
    parsed_date = None
    clean_description = (description or "").strip()

    if not category_id:
        errors.append("Please select a category.")
    else:
        try:
            category_id_int = int(category_id)
            if category_id_int not in valid_category_ids:
                errors.append("Selected category is invalid.")
        except (TypeError, ValueError):
            errors.append("Selected category is invalid.")

    if amount is None or str(amount).strip() == "":
        errors.append("Amount is required.")
    else:
        try:
            amount_value = float(str(amount).strip())
            if amount_value <= 0:
                errors.append("Amount must be greater than zero.")
            elif amount_value > MAX_EXPENSE_AMOUNT:
                errors.append(f"Amount cannot exceed ${MAX_EXPENSE_AMOUNT:,.2f}.")
        except ValueError:
            errors.append("Amount must be a valid number.")

    if not clean_description:
        errors.append("Description is required.")
    elif len(clean_description) > MAX_DESCRIPTION_LENGTH:
        errors.append(f"Description cannot exceed {MAX_DESCRIPTION_LENGTH} characters.")

    if not expense_date or not str(expense_date).strip():
        errors.append("Date is required.")
    else:
        try:
            parsed_date = datetime.strptime(str(expense_date).strip(), "%Y-%m-%d").date()
            if parsed_date > date.today():
                errors.append("Expense date cannot be in the future.")
        except ValueError:
            errors.append("Date must be in YYYY-MM-DD format.")

    return errors, category_id_int, amount_value, clean_description, parsed_date
