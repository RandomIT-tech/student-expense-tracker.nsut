# Student Expense Tracker

Semester 1 mini project, Netaji Subhas University of Technology (NSUT), Delhi.

- Team members: **[NAMES AND ROLL NUMBERS]**
- Branch / section: **[IT]**
- Faculty: **[FACULTY NAME]**

A small web app to record student expenses (in ₹), set a budget per month and see how much is left.
Built with **Flask + SQLite + HTML/CSS + vanilla JavaScript (fetch)**.

## Project structure

```
student-expense-tracker/
├── app.py            # Flask app: the page route and all /api/... routes
├── database.py       # SQLite connection helper and table creation
├── models.py         # All SQL queries (add, read, update, delete, totals, budgets)
├── services.py       # Validation rules and budget calculations (no SQL, no Flask)
├── count_lines.py    # Counts source lines (see "Counting lines")
├── requirements.txt
├── templates/index.html        # The single HTML page (Dashboard + Monthly Budget views)
├── static/css/style.css
├── static/js/app.js            # Calls the API with fetch() and updates the page
├── tests/test_api.py           # 20 automated tests (unittest)
└── docs/                       # Learning guide and report outline
```

Why this layout: each file has one job. `app.py` handles web requests, `services.py` decides what is valid and
calculates numbers, `models.py` talks to the database. If something breaks, you know which file to open.

## Run it locally

```bash
# 1. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server
python app.py
```

Open <http://127.0.0.1:5000>. The file `expenses.db` is created automatically and keeps your data between restarts.

## Run the tests

```bash
python -m unittest -v
```

Tests use a temporary database file, so your real `expenses.db` is never touched.

## Counting lines

```bash
python count_lines.py
```

It prints total, non-blank and "code" (no blank/comment lines) counts per file. **Ask your instructor which one counts**
(and whether HTML/CSS/tests are included), then quote that number.

## API documentation

All requests and responses use JSON. Months look like `2026-10`, dates like `2026-10-05`.
Errors always look like `{"error": "message", "details": {"field": "problem"}}`.

| Method | URL | Purpose | Success code |
|---|---|---|---|
| GET | `/api/expenses` | List expenses. Optional query: `month`, `category`, `search`, `sort` (date/amount), `order` (asc/desc) | 200 |
| GET | `/api/expenses/<id>` | Get one expense | 200 (404 if missing) |
| POST | `/api/expenses` | Create an expense | 201 (400 if invalid) |
| PUT | `/api/expenses/<id>` | Replace an expense's fields | 200 (400 / 404) |
| DELETE | `/api/expenses/<id>` | Delete an expense | 200 (404 if missing) |
| GET | `/api/summary?month=` | Total, budget, remaining, percent, status | 200 |
| GET | `/api/budget?month=` | Budget saved for a month | 200 |
| PUT | `/api/budget` | Save or update a month's budget | 200 (400 if invalid) |
| POST / DELETE | `/api/demo-data` | Add / remove clearly flagged sample expenses | 201 / 200 |

**POST /api/expenses** (create)

```json
// request
{"amount": 120, "category": "Food", "date": "2026-10-05", "description": "Canteen lunch"}
// response, status 201
{"id": 1, "amount": 120.0, "category": "Food", "date": "2026-10-05",
 "description": "Canteen lunch", "notes": "", "is_demo": false}
```

**Validation error** (status 400)

```json
{"error": "Validation failed.", "details": {"amount": "Amount must be greater than zero."}}
```

**GET /api/summary?month=2026-10**

```json
{"month": "2026-10", "total_expenses": 400.5, "expense_count": 2, "budget": 1000.0,
 "budget_is_set": true, "remaining": 599.5, "percent_used": 40.1,
 "percent_remaining": 59.9, "status": "ok"}
```

`status` is one of `no_budget`, `ok`, `warning` (80% or more used), `exhausted` (exactly 100%), `over`.
`percent_used` is `null` when the budget is missing or zero, so there is never a divide-by-zero.

**PUT /api/budget**

```json
// request
{"month": "2026-10", "amount": 5000}
// response
{"month": "2026-10", "amount": 5000.0, "is_set": true}
```

Try it from a terminal:

```bash
curl -X POST http://127.0.0.1:5000/api/expenses -H "Content-Type: application/json" \
  -d '{"amount": 45, "category": "Food", "date": "2026-10-05", "description": "Chai"}'
```

## Database design

| Table | Columns |
|---|---|
| `expenses` | `id` (PK), `amount`, `category`, `expense_date` (YYYY-MM-DD), `description`, `notes`, `is_demo`, `created_at` |
| `budgets` | `month` (PK, YYYY-MM), `amount` |

## Deploying (Render example)

> Nothing here has been deployed or verified by the author of this guide. Follow the steps and record your own result.

1. **Git:** `git init`, `git add .`, `git commit -m "Student Expense Tracker"`.
2. **GitHub:** create an empty repository, then `git remote add origin <url>` and `git push -u origin main`.
3. **Render:** create a new *Web Service* from your GitHub repository.
4. **Settings:** build command `pip install -r requirements.txt`, start command `gunicorn app:app`.
5. **Deploy**, then open the URL Render gives you.
6. **Verify:** add an expense, refresh the page, open `/api/summary` in the browser, run through the checklist below.

**SQLite limitation:** on typical free hosting plans the server's disk is *temporary*. When the service restarts or
redeploys, `expenses.db` can be wiped. Persistent disks (often paid) or a hosted database (PostgreSQL) solve this; with a
disk you set the `DATABASE_PATH` environment variable to a path on that disk. Check Render's current documentation for
details, and mention this limitation honestly in your report.

## Manual test checklist (fill in your own results)

- [ ] Add an expense; it appears in the table and the Total Expenses card changes
- [ ] Add with empty amount / negative amount; error messages appear
- [ ] Edit an expense, then Cancel Edit
- [ ] Delete shows a confirmation dialog
- [ ] Search, category filter and sort work
- [ ] Set a budget for one month; another month stays unset
- [ ] Spend 80%+ of the budget (warning), then exceed it (red)
- [ ] Stop and restart the server; data is still there
- [ ] Resize the window to phone width; the table becomes stacked cards
