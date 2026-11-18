"""models.py - functions that READ and WRITE the database (all the SQL lives here).

Rule we follow: other files never write SQL. They call these functions instead.
Every query uses `?` placeholders. The values are passed separately, which stops
"SQL injection" (a hacker typing SQL code into a form field).
"""
from database import open_db

# Whitelist for sorting. We NEVER paste user text into the SQL directly,
# so we only allow these exact choices.
SORT_COLUMNS = {"date": "expense_date", "amount": "amount"}
SORT_ORDERS = {"asc": "ASC", "desc": "DESC"}

# Sample expenses: (day of month, amount, category, description)
DEMO_EXPENSES = [
    (2, 120.0, "Food", "Canteen lunch"),
    (3, 200.0, "Travel", "Metro card recharge"),
    (5, 85.5, "Education", "Stationery and notebooks"),
    (8, 40.0, "Education", "Printing lab record"),
    (10, 450.0, "Education", "Engineering Mathematics book"),
    (12, 150.0, "Entertainment", "College fest entry"),
    (15, 299.0, "Bills", "Mobile recharge"),
    (18, 90.0, "Food", "Evening chai and samosa"),
]


def row_to_dict(row):
    """Turn a database row into a normal Python dict (easy to convert to JSON)."""
    return {
        "id": row["id"],
        "amount": row["amount"],
        "category": row["category"],
        "date": row["expense_date"],
        "description": row["description"],
        "notes": row["notes"],
        "is_demo": bool(row["is_demo"]),
    }


# ---------- Expenses ----------

def add_expense(db_path, data, is_demo=0):
    """INSERT a new expense and return its new id."""
    with open_db(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO expenses (amount, category, expense_date, description, notes, is_demo) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (data["amount"], data["category"], data["date"],
             data["description"], data["notes"], is_demo),
        )
        return cursor.lastrowid


def get_expense(db_path, expense_id):
    """SELECT one expense by id. Returns a dict, or None if it does not exist."""
    with open_db(db_path) as conn:
        row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    return row_to_dict(row) if row else None


def list_expenses(db_path, month=None, category=None, search=None,
                  sort="date", order="desc"):
    """SELECT many expenses. Each filter is added only if the user gave it."""
    sql = "SELECT * FROM expenses WHERE 1 = 1"
    params = []
    if month:
        sql += " AND substr(expense_date, 1, 7) = ?"   # first 7 characters = 'YYYY-MM'
        params.append(month)
    if category:
        sql += " AND category = ?"
        params.append(category)
    if search:
        sql += " AND description LIKE ?"               # LIKE with % = "contains"
        params.append(f"%{search}%")
    # Safe because the values come from our own whitelist dictionaries above.
    sql += f" ORDER BY {SORT_COLUMNS[sort]} {SORT_ORDERS[order]}, id DESC"
    with open_db(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [row_to_dict(row) for row in rows]


def update_expense(db_path, expense_id, data):
    """UPDATE an expense. Returns True if a row was changed, False if id not found."""
    with open_db(db_path) as conn:
        cursor = conn.execute(
            "UPDATE expenses SET amount = ?, category = ?, expense_date = ?, "
            "description = ?, notes = ? WHERE id = ?",
            (data["amount"], data["category"], data["date"],
             data["description"], data["notes"], expense_id),
        )
        return cursor.rowcount > 0


def delete_expense(db_path, expense_id):
    """DELETE an expense. Returns True if a row was removed."""
    with open_db(db_path) as conn:
        cursor = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        return cursor.rowcount > 0


def total_for_month(db_path, month):
    """Add up all expenses of one month. COALESCE gives 0 when there are no rows."""
    with open_db(db_path) as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count "
            "FROM expenses WHERE substr(expense_date, 1, 7) = ?",
            (month,),
        ).fetchone()
    return round(row["total"], 2), row["count"]


# ---------- Budgets ----------

def get_budget(db_path, month):
    """Return the budget amount for a month, or None if never set."""
    with open_db(db_path) as conn:
        row = conn.execute("SELECT amount FROM budgets WHERE month = ?", (month,)).fetchone()
    return row["amount"] if row else None


def set_budget(db_path, month, amount):
    """Insert the budget, or update it if that month already has one ("upsert")."""
    with open_db(db_path) as conn:
        conn.execute(
            "INSERT INTO budgets (month, amount) VALUES (?, ?) "
            "ON CONFLICT(month) DO UPDATE SET amount = excluded.amount",
            (month, amount),
        )


# ---------- Demo data ----------

def add_demo_expenses(db_path, month):
    """Insert the sample expenses into the given month, flagged is_demo = 1."""
    for day, amount, category, description in DEMO_EXPENSES:
        add_expense(db_path, {
            "amount": amount, "category": category,
            "date": f"{month}-{day:02d}",
            "description": description, "notes": "",
        }, is_demo=1)
    return len(DEMO_EXPENSES)


def delete_demo_expenses(db_path):
    """Remove only the sample rows; real expenses are untouched."""
    with open_db(db_path) as conn:
        return conn.execute("DELETE FROM expenses WHERE is_demo = 1").rowcount
