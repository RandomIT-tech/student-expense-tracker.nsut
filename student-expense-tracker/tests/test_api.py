"""Tests for the API. Run from the project folder with:  python -m unittest -v

Each test gets a brand-new TEMPORARY database, so your real expenses.db is never touched.
`setUp` runs before every test; `tearDown` runs after every test.
"""
import os
import sys
import tempfile
import unittest

# Make "import app" work when tests are run from the project folder.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app          # noqa: E402
from database import init_db  # noqa: E402

VALID_EXPENSE = {"amount": 120, "category": "Food", "date": "2026-10-05",
                 "description": "Canteen lunch"}


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        handle, self.db_file = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        app.config["DB_PATH"] = self.db_file
        app.config["TESTING"] = True
        init_db(self.db_file)
        self.client = app.test_client()   # a fake browser

    def tearDown(self):
        os.remove(self.db_file)

    def create(self, **changes):
        """Helper: POST an expense (optionally changing some fields)."""
        return self.client.post("/api/expenses", json={**VALID_EXPENSE, **changes})


class ExpenseCrudTests(ApiTestCase):
    def test_create_expense(self):
        response = self.create()
        self.assertEqual(response.status_code, 201)
        body = response.get_json()
        self.assertEqual(body["amount"], 120)
        self.assertEqual(body["category"], "Food")
        self.assertIn("id", body)

    def test_read_expenses_and_single_expense(self):
        new_id = self.create().get_json()["id"]
        listing = self.client.get("/api/expenses?month=2026-10").get_json()
        self.assertEqual(listing["count"], 1)
        single = self.client.get(f"/api/expenses/{new_id}")
        self.assertEqual(single.status_code, 200)
        self.assertEqual(single.get_json()["description"], "Canteen lunch")

    def test_update_expense(self):
        new_id = self.create().get_json()["id"]
        changed = {**VALID_EXPENSE, "amount": 99.5, "category": "Travel"}
        response = self.client.put(f"/api/expenses/{new_id}", json=changed)
        self.assertEqual(response.status_code, 200)
        saved = self.client.get(f"/api/expenses/{new_id}").get_json()
        self.assertEqual(saved["amount"], 99.5)
        self.assertEqual(saved["category"], "Travel")

    def test_delete_expense(self):
        new_id = self.create().get_json()["id"]
        self.assertEqual(self.client.delete(f"/api/expenses/{new_id}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/expenses/{new_id}").status_code, 404)


class ValidationTests(ApiTestCase):
    def test_invalid_amounts_are_rejected(self):
        for bad_amount in ["abc", -5, 0, "", None, True, "nan"]:
            response = self.create(amount=bad_amount)
            self.assertEqual(response.status_code, 400, f"amount={bad_amount!r}")
            self.assertIn("amount", response.get_json()["details"])

    def test_missing_fields_are_rejected(self):
        response = self.client.post("/api/expenses", json={})
        self.assertEqual(response.status_code, 400)
        details = response.get_json()["details"]
        for field in ("amount", "category", "date"):
            self.assertIn(field, details)

    def test_invalid_date_and_category(self):
        self.assertEqual(self.create(date="2026-02-30").status_code, 400)
        self.assertEqual(self.create(date="05/10/2026").status_code, 400)
        self.assertEqual(self.create(category="Gaming").status_code, 400)

    def test_body_must_be_json_object(self):
        response = self.client.post("/api/expenses", data="not json")
        self.assertEqual(response.status_code, 400)

    def test_missing_expense_id_gives_404(self):
        self.assertEqual(self.client.get("/api/expenses/9999").status_code, 404)
        self.assertEqual(self.client.put("/api/expenses/9999", json=VALID_EXPENSE).status_code, 404)
        self.assertEqual(self.client.delete("/api/expenses/9999").status_code, 404)


class FilterTests(ApiTestCase):
    def test_filter_search_and_sort(self):
        self.create(amount=50, category="Food", date="2026-10-01", description="Chai")
        self.create(amount=300, category="Travel", date="2026-10-09", description="Metro recharge")
        self.create(amount=75, category="Food", date="2026-11-02", description="November snack")

        october = self.client.get("/api/expenses?month=2026-10").get_json()
        self.assertEqual(october["count"], 2)

        food = self.client.get("/api/expenses?month=2026-10&category=Food").get_json()
        self.assertEqual(food["count"], 1)

        found = self.client.get("/api/expenses?search=metro").get_json()
        self.assertEqual(found["count"], 1)

        by_amount = self.client.get("/api/expenses?month=2026-10&sort=amount&order=asc").get_json()
        self.assertEqual([e["amount"] for e in by_amount["expenses"]], [50, 300])

    def test_bad_filter_values_give_400(self):
        self.assertEqual(self.client.get("/api/expenses?month=oct").status_code, 400)
        self.assertEqual(self.client.get("/api/expenses?sort=colour").status_code, 400)


class BudgetAndSummaryTests(ApiTestCase):
    def set_budget(self, amount, month="2026-10"):
        return self.client.put("/api/budget", json={"month": month, "amount": amount})

    def test_save_and_read_budget(self):
        self.assertEqual(self.set_budget(5000).status_code, 200)
        saved = self.client.get("/api/budget?month=2026-10").get_json()
        self.assertEqual(saved["amount"], 5000)
        self.assertTrue(saved["is_set"])
        self.set_budget(6000)   # update the same month
        self.assertEqual(self.client.get("/api/budget?month=2026-10").get_json()["amount"], 6000)

    def test_budgets_are_separate_per_month(self):
        self.set_budget(5000, "2026-10")
        other = self.client.get("/api/budget?month=2026-11").get_json()
        self.assertFalse(other["is_set"])

    def test_invalid_budget_is_rejected(self):
        self.assertEqual(self.set_budget(-1).status_code, 400)
        self.assertEqual(self.set_budget("abc").status_code, 400)
        self.assertEqual(self.set_budget(100, "bad").status_code, 400)

    def test_summary_calculation(self):
        self.set_budget(1000)
        self.create(amount=250)
        self.create(amount=150.5)
        summary = self.client.get("/api/summary?month=2026-10").get_json()
        self.assertEqual(summary["total_expenses"], 400.5)
        self.assertEqual(summary["remaining"], 599.5)
        self.assertEqual(summary["percent_used"], 40.1)
        self.assertEqual(summary["status"], "ok")

    def test_summary_statuses(self):
        self.set_budget(100)
        self.create(amount=85)
        self.assertEqual(self.client.get("/api/summary?month=2026-10").get_json()["status"], "warning")
        self.create(amount=15)
        self.assertEqual(self.client.get("/api/summary?month=2026-10").get_json()["status"], "exhausted")
        self.create(amount=10)
        over = self.client.get("/api/summary?month=2026-10").get_json()
        self.assertEqual(over["status"], "over")
        self.assertEqual(over["remaining"], -10)

    def test_zero_or_missing_budget_does_not_crash(self):
        self.create(amount=100)
        no_budget = self.client.get("/api/summary?month=2026-10").get_json()
        self.assertEqual(no_budget["status"], "no_budget")
        self.assertIsNone(no_budget["percent_used"])
        self.set_budget(0)
        zero = self.client.get("/api/summary?month=2026-10").get_json()
        self.assertIsNone(zero["percent_used"])
        self.assertEqual(zero["remaining"], -100)

    def test_empty_month_summary(self):
        summary = self.client.get("/api/summary?month=2026-01").get_json()
        self.assertEqual(summary["total_expenses"], 0)
        self.assertEqual(summary["expense_count"], 0)


class PersistenceAndDemoTests(ApiTestCase):
    def test_data_survives_a_new_connection(self):
        """Simulates a restart: a brand-new test client reads the same database file."""
        new_id = self.create().get_json()["id"]
        self.set_budget_for_persistence()
        fresh_client = app.test_client()
        self.assertEqual(fresh_client.get(f"/api/expenses/{new_id}").status_code, 200)
        self.assertEqual(fresh_client.get("/api/budget?month=2026-10").get_json()["amount"], 4000)

    def set_budget_for_persistence(self):
        self.client.put("/api/budget", json={"month": "2026-10", "amount": 4000})

    def test_demo_data_can_be_loaded_and_removed_without_touching_real_data(self):
        self.create(description="My real expense")
        self.assertEqual(self.client.post("/api/demo-data?month=2026-10").status_code, 201)
        everything = self.client.get("/api/expenses?month=2026-10").get_json()["expenses"]
        self.assertEqual(sum(1 for e in everything if e["is_demo"]), 8)
        self.client.delete("/api/demo-data")
        left = self.client.get("/api/expenses?month=2026-10").get_json()["expenses"]
        self.assertEqual([e["description"] for e in left], ["My real expense"])


if __name__ == "__main__":
    unittest.main()
