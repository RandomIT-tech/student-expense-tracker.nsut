"""app.py - the Flask web application: page route + REST API routes.

Concept: a Flask "route" connects a URL to a Python function.
    @app.route("/api/expenses", methods=["GET"])  ->  runs list_expenses_route()
`jsonify(...)` turns a Python dict into JSON text for the browser.
Run locally with:  python app.py
"""
import os

from flask import Flask, jsonify, render_template, request

import models
import services
from database import init_db

app = Flask(__name__)
# Where the SQLite file lives. Tests change this to a separate test database.
app.config["DB_PATH"] = os.environ.get("DATABASE_PATH", "expenses.db")
init_db(app.config["DB_PATH"])


# ---------- Small helper functions ----------

def db_path():
    return app.config["DB_PATH"]


def error_response(message, status, details=None):
    """Every error uses the same JSON shape so the frontend can handle it easily."""
    body = {"error": message}
    if details:
        body["details"] = details
    return jsonify(body), status


def read_json_body():
    """Return the JSON dictionary sent by the browser, or None if it is invalid."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def month_from_query():
    """Read ?month=YYYY-MM from the URL. Returns (month, error_response)."""
    month = request.args.get("month") or services.current_month()
    if not services.is_valid_month(month):
        return None, error_response("month must look like YYYY-MM, e.g. 2026-10.", 400)
    return month, None


# ---------- Page ----------

@app.route("/")
def home():
    """Send the single HTML page. Jinja puts the category list into it."""
    return render_template("index.html", categories=services.CATEGORIES)


# ---------- Expenses API ----------

@app.route("/api/expenses", methods=["GET"])
def list_expenses_route():
    """List expenses. Optional filters: month, category, search, sort, order."""
    month = request.args.get("month")
    if month and not services.is_valid_month(month):
        return error_response("month must look like YYYY-MM.", 400)

    category = request.args.get("category") or None
    if category and category not in services.CATEGORIES:
        return error_response("Unknown category.", 400)

    sort = request.args.get("sort", "date")
    order = request.args.get("order", "desc")
    if sort not in models.SORT_COLUMNS or order not in models.SORT_ORDERS:
        return error_response("sort must be date or amount; order must be asc or desc.", 400)

    expenses = models.list_expenses(db_path(), month, category,
                                    request.args.get("search", "").strip(), sort, order)
    return jsonify({"expenses": expenses, "count": len(expenses)})


@app.route("/api/expenses/<int:expense_id>", methods=["GET"])
def get_expense_route(expense_id):
    expense = models.get_expense(db_path(), expense_id)
    if expense is None:
        return error_response("Expense not found.", 404)
    return jsonify(expense)


@app.route("/api/expenses", methods=["POST"])
def create_expense_route():
    data = read_json_body()
    if data is None:
        return error_response("Request body must be a JSON object.", 400)
    clean, errors = services.validate_expense(data)
    if errors:
        return error_response("Validation failed.", 400, errors)
    new_id = models.add_expense(db_path(), clean)
    return jsonify(models.get_expense(db_path(), new_id)), 201   # 201 = Created


@app.route("/api/expenses/<int:expense_id>", methods=["PUT"])
def update_expense_route(expense_id):
    data = read_json_body()
    if data is None:
        return error_response("Request body must be a JSON object.", 400)
    clean, errors = services.validate_expense(data)
    if errors:
        return error_response("Validation failed.", 400, errors)
    if not models.update_expense(db_path(), expense_id, clean):
        return error_response("Expense not found.", 404)
    return jsonify(models.get_expense(db_path(), expense_id))


@app.route("/api/expenses/<int:expense_id>", methods=["DELETE"])
def delete_expense_route(expense_id):
    if not models.delete_expense(db_path(), expense_id):
        return error_response("Expense not found.", 404)
    return jsonify({"message": "Expense deleted."})


# ---------- Summary and budget API ----------

@app.route("/api/summary", methods=["GET"])
def summary_route():
    month, error = month_from_query()
    if error:
        return error
    return jsonify(services.build_summary(db_path(), month))


@app.route("/api/budget", methods=["GET"])
def get_budget_route():
    month, error = month_from_query()
    if error:
        return error
    amount = models.get_budget(db_path(), month)
    return jsonify({"month": month, "amount": amount or 0, "is_set": amount is not None})


@app.route("/api/budget", methods=["PUT"])
def set_budget_route():
    data = read_json_body()
    if data is None:
        return error_response("Request body must be a JSON object.", 400)
    month = data.get("month")
    if not services.is_valid_month(month):
        return error_response("month must look like YYYY-MM.", 400)
    amount, amount_error = services.parse_amount(data.get("amount"), allow_zero=True)
    if amount_error:
        return error_response("Validation failed.", 400, {"amount": amount_error})
    models.set_budget(db_path(), month, amount)
    return jsonify({"month": month, "amount": amount, "is_set": True})


# ---------- Optional demo data ----------

@app.route("/api/demo-data", methods=["POST"])
def load_demo_data_route():
    month, error = month_from_query()
    if error:
        return error
    added = models.add_demo_expenses(db_path(), month)
    return jsonify({"message": f"Added {added} demo expenses to {month}."}), 201


@app.route("/api/demo-data", methods=["DELETE"])
def clear_demo_data_route():
    removed = models.delete_demo_expenses(db_path())
    return jsonify({"message": f"Removed {removed} demo expenses."})


if __name__ == "__main__":
    app.run(debug=True)   # debug=True auto-reloads on code changes (never use on a live server)
