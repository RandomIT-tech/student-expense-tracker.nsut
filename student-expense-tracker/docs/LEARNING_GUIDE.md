# Learning Guide: understand your own project

Read this with the code open. Do the exercises **yourselves** before asking anyone (including an AI) for help.

## 0. The big picture (say this in your viva)

```
Browser (HTML + CSS + app.js)  --fetch() JSON-->  Flask (app.py)  -->  services.py (validate, calculate)
                               <--JSON response--                 -->  models.py   (SQL)  -->  expenses.db
```

1. You click **Add Expense**. `app.js` collects the form values and sends `POST /api/expenses` with `fetch()`.
2. Flask runs `create_expense_route()`. It calls `services.validate_expense()`. If something is wrong it returns status 400.
3. If valid, `models.add_expense()` runs an SQL `INSERT` and the row is saved in `expenses.db`.
4. Flask replies with JSON (status 201). `app.js` then asks `/api/summary` and `/api/expenses` again and redraws the page.

The page never keeps its own copy of the data; the database is the single source of truth.

## 1. File by file

### database.py: concept: *context managers, SQL tables*
- `SCHEMA` is plain SQL text that creates two tables. `CHECK (amount > 0)` makes the database itself refuse bad amounts.
- `open_db()` opens a connection, **commits** if all went well, **rolls back** if an error happened, and always **closes**.
  The `@contextmanager` decorator lets us write `with open_db(path) as conn:`.
- `init_db()` runs the schema. Safe to run repeatedly because of `IF NOT EXISTS`.

### models.py: concept: *SQL CRUD, parameterised queries, dictionaries*
- CRUD = Create (`INSERT`), Read (`SELECT`), Update (`UPDATE`), Delete (`DELETE`).
- `?` placeholders: values are sent separately from the SQL text, which prevents **SQL injection**.
- `list_expenses()` starts with `WHERE 1 = 1` and adds `AND ...` only for filters that were provided.
  Sorting uses a **whitelist dictionary** because column names cannot use `?`.
- `total_for_month()` uses `SUM()`; `COALESCE(..., 0)` turns "no rows" into 0.
- `set_budget()` is an "upsert": insert, or update if that month already exists.
- `row_to_dict()` converts a database row to a Python dict so Flask can turn it into JSON.

### services.py: concept: *validation, exceptions, functions that return tuples*
- `parse_amount()` uses `try/except` to catch `float("abc")` failing. `math.isfinite()` blocks `nan`/`inf`.
- `validate_expense()` collects **all** errors into a dict, so the form can show every problem at once.
- `build_summary()` holds the formulas: `remaining = budget - total` and `percent_used = total / budget * 100`
  (only when budget > 0, which avoids division by zero). It also decides the `status` word.

### app.py: concept: *Flask routes, HTTP methods, status codes, JSON*
- `@app.route("/api/expenses", methods=["POST"])` links a URL + method to a function.
- `request.get_json()` reads the JSON the browser sent; `jsonify()` builds the JSON reply.
- Status codes used: 200 OK, 201 Created, 400 Bad Request (user's mistake), 404 Not Found.
- `<int:expense_id>` in a URL captures a number and passes it to the function.
- `render_template("index.html", categories=...)` fills the HTML using **Jinja** (`{% for %}` loops).

### templates/index.html: concept: *HTML structure, semantic tags, Jinja*
- One page, two `<section>` views. Which one is visible depends on the URL hash (`#dashboard` / `#budget`).
- Every element JS needs has an `id`. If you rename an `id`, you must rename it in `app.js` too.

### static/css/style.css: concept: *CSS variables, flexbox, grid, media queries*
- Colours are variables in `:root`. Change `--blue` and the whole theme changes.
- `display: grid; grid-template-columns: repeat(3, 1fr)` makes the three equal cards.
- `@media (max-width: 900px)` stacks columns on small screens; under 640px, table rows become cards.

### static/js/app.js: concept: *async/await, fetch, DOM, events*
- `api(url, options)` is the **only** function that calls `fetch()`. It throws an error for 4xx/5xx responses.
- `async/await`: `await` pauses until the server answers, without freezing the page.
- `refreshAll()` loads summary, expenses and budget again after every change.
- `renderTable()` builds rows with `document.createElement` and `textContent` (safe against HTML injection).
- `handleFormSubmit()` uses `POST` when adding and `PUT` when `state.editingId` is set.
- `event.preventDefault()` stops the browser's default form reload.

### tests/test_api.py: concept: *unit testing with unittest*
- `setUp()` makes a fresh temporary database before **each** test; `tearDown()` deletes it.
- `self.client` is a fake browser. `assertEqual` compares the real result with the expected one.

## 2. Exercises (do them in this order)

1. **Rename a category.** Change `"Other"` to `"Miscellaneous"` in `services.py`. Run the tests. Does anything break? Why?
2. **Change the warning level** from 80% to 90% (`WARNING_PERCENT`). Which test fails? Update the test numbers to match. Then search `app.js` for the text "80%": what else is still hard-coded, and how would you fix it?
3. **Change the theme.** Edit `--blue` in `style.css` to another colour. What changes?
4. **Add a category** ("Health"). How many files must you touch? (Hint: only one for the dropdowns. Why?)
5. **Read the SQL.** Open `expenses.db` with *DB Browser for SQLite* (free) and look at your rows.
6. **Add a new test** that checks a 200-character description is rejected.
7. **Trace a request.** In browser DevTools → Network tab, add an expense. Find the `POST` request, its JSON body and the response.
8. **Break it on purpose.** Remove `.strip()` in `validate_expense`. Which behaviour changes?
9. **Stretch (only after 1–8):** add a "Total for this category" line under the table using existing API data.

## 3. Likely viva questions (practise answering aloud)

1. What is Flask? Why not just HTML and JavaScript?
2. What is a REST API? Which HTTP methods do you use and why?
3. What does status code 201 / 400 / 404 mean? Where does your code return each?
4. Why do you store data in SQLite instead of a Python list?
5. What is SQL injection and how does your code avoid it?
6. What does `with open_db(...)` do? What are commit and rollback?
7. How does the browser get data from the server? Explain `fetch` and `await`.
8. Where is validation done, frontend or backend? Why must the backend validate?
9. How is the remaining budget calculated? What if the budget is zero?
10. Why do you store dates as `YYYY-MM-DD` text? How do you filter by month?
11. What happens to your data when the server restarts? When deployed on free hosting?
12. How did you test the project? What does `setUp` do?
13. What is the difference between `PUT` and `POST`?
14. What would you add next, and what are the limitations (no login, one shared database, no charts)?
15. **Which parts did you write or change yourselves, and which were generated with AI help?** (see below)

## 4. Being honest about AI help

Rules differ between universities and even between teachers. **Ask your instructor in writing** what is allowed
and how to declare it. A simple declaration to include in your report (edit it to be true for you):

> This project was developed by [team names]. We used an AI assistant (Claude) for [e.g. an initial code skeleton,
> explanations of Flask and SQL concepts]. We reviewed, ran and tested the code, and we made the following changes
> ourselves: [list]. We can explain every file.

Keep a short log: date, what you asked, what you changed. Your own changes (exercises above) are the real proof of learning.
