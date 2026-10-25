import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app import create_app


class WebAppTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "tasks.json"
        self.config = {"TESTING": True, "SECRET_KEY": "test-key", "TASKS_FILE": self.path}
        self.app = create_app(self.config)
        self.client = self.app.test_client()
        self.client.get("/")
        with self.client.session_transaction() as session:
            self.token = session["csrf_token"]

    def post(self, route, **data):
        return self.client.post(route, data={"csrf_token": self.token, **data})

    def test_add_sort_persist_and_remove(self):
        for name, priority in [("Last", "5"), ("First", "1"), ("Middle", "3")]:
            self.assertEqual(self.post("/tasks", name=name, priority=priority).status_code, 303)
        page = self.client.get("/").get_data(as_text=True)
        self.assertLess(page.index('>First<'), page.index('>Middle<'))
        self.assertLess(page.index('>Middle<'), page.index('>Last<'))
        descending = self.client.get("/?sort=desc").get_data(as_text=True)
        self.assertLess(descending.index('>Last<'), descending.index('>Middle<'))
        self.assertLess(descending.index('>Middle<'), descending.index('>First<'))
        self.assertIn('sort=asc', descending)
        self.post("/tasks", name="Another", priority="4")
        remembered = self.client.get("/").get_data(as_text=True)
        self.assertLess(remembered.index('>Last<'), remembered.index('>Another<'))
        self.assertLess(remembered.index('>Another<'), remembered.index('>First<'))
        self.client.get("/?sort=asc")
        ascending = self.client.get("/").get_data(as_text=True)
        self.assertLess(ascending.index('>First<'), ascending.index('>Last<'))
        restarted = create_app(self.config).test_client()
        self.assertIn(b">First<", restarted.get("/").data)
        tasks = json.loads(self.path.read_text(encoding="utf-8"))
        first_id = next(task["id"] for task in tasks if task["name"] == "First")
        self.assertEqual(self.post(f"/tasks/{first_id}/delete").status_code, 303)
        saved = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual({task["name"] for task in saved}, {"Middle", "Last", "Another"})
        self.assertEqual(self.post(f"/tasks/{first_id}/delete").status_code, 303)

    def test_invalid_inputs_preserve_name_without_writing(self):
        for priority in ["abc", "", "0", "6", "1.5"]:
            response = self.post("/tasks", name="Keep my task", priority=priority)
            self.assertEqual(response.status_code, 400)
            self.assertIn(b'value="Keep my task"', response.data)
        for name in ["", "   ", "x" * 201]:
            self.assertEqual(self.post("/tasks", name=name, priority="2").status_code, 400)
        self.assertFalse(self.path.exists())

    def test_name_sorting_and_selection_persistence(self):
        for name, priority in [("zebra", "1"), ("apple", "5"), ("Banana", "3")]:
            self.post("/tasks", name=name, priority=priority)
        before = self.path.read_bytes()
        for order, expected in [("asc", ["apple", "Banana", "zebra"]),
                                ("desc", ["zebra", "Banana", "apple"])]:
            page = self.client.get(f"/?sort_by=name&sort={order}").get_data(as_text=True)
            positions = [page.index(f'>{name}<') for name in expected]
            self.assertEqual(positions, sorted(positions))
        self.assertEqual(self.path.read_bytes(), before)
        self.post("/tasks", name="cherry", priority="2")
        page = self.client.get("/").get_data(as_text=True)
        self.assertLess(page.index('>zebra<'), page.index('>cherry<'))
        self.assertLess(page.index('>cherry<'), page.index('>apple<'))
        invalid = self.post("/tasks", name="Keep name", priority="abc").get_data(as_text=True)
        self.assertLess(invalid.index('>zebra<'), invalid.index('>apple<'))
        tasks = json.loads(self.path.read_text(encoding="utf-8"))
        cherry_id = next(task["id"] for task in tasks if task["name"] == "cherry")
        self.post(f"/tasks/{cherry_id}/delete")
        page = self.client.get("/").get_data(as_text=True)
        self.assertLess(page.index('>zebra<'), page.index('>apple<'))
        fallback = self.client.get("/?sort_by=invalid&sort=invalid").get_data(as_text=True)
        self.assertLess(fallback.index('>zebra<'), fallback.index('>apple<'))
        with self.client.session_transaction() as session:
            self.assertEqual(session['sort_by'], 'priority')
            self.assertEqual(session['sort_order'], 'asc')

    def test_form_protection_and_escaping(self):
        self.assertEqual(self.client.post("/tasks", data={"name": "test", "priority": "1"}).status_code, 400)
        self.assertEqual(self.client.post("/tasks", data={"csrf_token": "é"}).status_code, 400)
        self.post("/tasks", name="<script>alert(1)</script>", priority="1")
        page = self.client.get("/").data
        self.assertNotIn(b"<script>", page)
        self.assertIn(b"&lt;script&gt;", page)

    def test_corrupt_storage_is_preserved(self):
        self.path.write_text("broken json", encoding="utf-8")
        with self.assertLogs(self.app.logger, level="ERROR"):
            self.assertEqual(self.client.get("/").status_code, 503)
            self.assertEqual(self.post("/tasks", name="New", priority="2").status_code, 503)
        self.assertEqual(self.path.read_text(encoding="utf-8"), "broken json")

    def test_empty_list_and_static_assets(self):
        self.assertIn(b"A fresh start", self.client.get("/").data)
        with self.client.get("/static/style.css") as response:
            self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/tasks/missing/delete").status_code, 405)


if __name__ == "__main__":
    unittest.main()
