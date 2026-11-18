"""database.py - everything about connecting to SQLite and creating tables.

Concept: SQLite is a database stored in ONE file (here: expenses.db).
Python talks to it using the built-in `sqlite3` module, so nothing extra to install.
"""
import sqlite3
from contextlib import contextmanager

# SQL that creates our two tables. "IF NOT EXISTS" means it is safe to run every time.
SCHEMA = """
CREATE TABLE IF NOT EXISTS expenses (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    amount       REAL    NOT NULL CHECK (amount > 0),
    category     TEXT    NOT NULL,
    expense_date TEXT    NOT NULL,             -- stored as 'YYYY-MM-DD'
    description  TEXT    NOT NULL DEFAULT '',
    notes        TEXT    NOT NULL DEFAULT '',
    is_demo      INTEGER NOT NULL DEFAULT 0,   -- 1 = sample data, 0 = real data
    created_at   TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS budgets (
    month  TEXT PRIMARY KEY,                   -- 'YYYY-MM', one budget per month
    amount REAL NOT NULL CHECK (amount >= 0)
);
"""


@contextmanager
def open_db(db_path):
    """Open the database, hand it to the caller, then ALWAYS clean up.

    Use it like this:
        with open_db(path) as conn:
            conn.execute(...)

    - On success we `commit()` (save changes permanently).
    - On error we `rollback()` (undo half-finished changes).
    - In every case we `close()` the connection.
    `@contextmanager` is what lets us use the `with` keyword on our own function.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # lets us read columns by name: row["amount"]
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path):
    """Create the tables if they do not exist yet."""
    with open_db(db_path) as conn:
        conn.executescript(SCHEMA)
