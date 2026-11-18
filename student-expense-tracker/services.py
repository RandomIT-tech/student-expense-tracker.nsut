"""services.py - the "thinking" part: validation rules and budget calculations.

No Flask and no SQL here. That keeps each function small and easy to test.
"""
import math
from datetime import date, datetime

import models

CATEGORIES = ["Food", "Travel", "Education", "Shopping", "Bills", "Entertainment", "Other"]
MAX_AMOUNT = 10_000_000          # sanity limit: 1 crore rupees
WARNING_PERCENT = 80             # show a warning once 80% of the budget is used


# ---------- Dates and months ----------

def current_month():
    """Today's month as 'YYYY-MM' (example: '2026-10')."""
    return date.today().strftime("%Y-%m")


def is_valid_month(text):
    """True only for real months like '2026-10'."""
    try:
        datetime.strptime(text, "%Y-%m")
        return True
    except (ValueError, TypeError):
        return False


def is_valid_date(text):
    """True only for real dates like '2026-10-25' (so '2026-02-30' fails)."""
    try:
        datetime.strptime(text, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


# ---------- Validation ----------

def parse_amount(value, allow_zero=False):
    """Convert user input to a number. Returns (number, error_message)."""
    # In Python, True/False count as numbers, so reject them explicitly.
    if value is None or value == "" or isinstance(value, bool):
        return None, "Amount is required."
    try:
        number = float(value)
    except (ValueError, TypeError):
        return None, "Amount must be a number."
    if not math.isfinite(number):          # blocks 'nan' and 'inf'
        return None, "Amount must be a real number."
    if number < 0:
        return None, "Amount cannot be negative."
    if number == 0 and not allow_zero:
        return None, "Amount must be greater than zero."
    if number > MAX_AMOUNT:
        return None, f"Amount cannot be more than {MAX_AMOUNT}."
    return round(number, 2), None


def validate_expense(data):
    """Check the JSON sent by the browser.

    Returns (clean_data, errors). If `errors` is empty, `clean_data` is safe to save.
    """
    errors = {}

    amount, amount_error = parse_amount(data.get("amount"))
    if amount_error:
        errors["amount"] = amount_error

    category = data.get("category")
    if category not in CATEGORIES:
        errors["category"] = "Choose one of: " + ", ".join(CATEGORIES) + "."

    expense_date = data.get("date")
    if not expense_date:
        errors["date"] = "Date is required."
    elif not is_valid_date(expense_date):
        errors["date"] = "Date must be a real date in YYYY-MM-DD format."

    description = str(data.get("description") or "").strip()
    notes = str(data.get("notes") or "").strip()
    if len(description) > 100:
        errors["description"] = "Description must be 100 characters or fewer."
    if len(notes) > 300:
        errors["notes"] = "Notes must be 300 characters or fewer."

    clean = {"amount": amount, "category": category, "date": expense_date,
             "description": description, "notes": notes}
    return clean, errors


# ---------- Budget calculations ----------

def build_summary(db_path, month):
    """Combine expenses and budget into the numbers shown on the dashboard.

    Total Expenses  = sum of the month's expenses
    Remaining       = Budget - Total Expenses
    Percent used    = Total / Budget * 100   (only when Budget > 0)
    """
    total, count = models.total_for_month(db_path, month)
    budget = models.get_budget(db_path, month)
    budget_is_set = budget is not None

    remaining = round((budget or 0) - total, 2)
    has_budget = budget_is_set and budget > 0
    percent_used = round(total / budget * 100, 1) if has_budget else None
    percent_remaining = round(remaining / budget * 100, 1) if has_budget else None

    if not has_budget:
        status = "no_budget"
    elif total > budget:
        status = "over"
    elif total == budget:
        status = "exhausted"
    elif percent_used >= WARNING_PERCENT:
        status = "warning"
    else:
        status = "ok"

    return {
        "month": month,
        "total_expenses": total,
        "expense_count": count,
        "budget": budget or 0,
        "budget_is_set": budget_is_set,
        "remaining": remaining,
        "percent_used": percent_used,
        "percent_remaining": percent_remaining,
        "status": status,
    }
