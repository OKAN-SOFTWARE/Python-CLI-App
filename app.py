"""Local Flask front end for the task tracker."""

import json
import os
from pathlib import Path
import secrets
from tempfile import NamedTemporaryFile
from threading import RLock
from uuid import uuid4

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for

from task_tracker import Task


class TaskStore:
    """JSON storage for one local application process."""

    def __init__(self, path):
        self.path = Path(path)
        self.lock = RLock()

    def read(self):
        if not self.path.exists():
            return []
        try:
            tasks = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(tasks, list):
                raise ValueError("Expected a list of tasks.")
            ids = set()
            for task in tasks:
                Task(task["name"], task["priority"])
                if not isinstance(task["id"], str) or task["id"] in ids:
                    raise ValueError("Invalid task ID.")
                ids.add(task["id"])
                if type(task["priority"]) is not int:
                    raise ValueError("Invalid stored priority.")
            return sorted(tasks, key=lambda task: task["priority"])
        except (ValueError, TypeError, KeyError, AttributeError) as error:
            raise OSError("Could not read tasks.json. Repair the file before making changes.") from error

    def write(self, tasks):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = None
        try:
            with NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                    delete=False) as temporary:
                temporary_path = Path(temporary.name)
                json.dump(tasks, temporary, indent=2, ensure_ascii=False)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, self.path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("TASK_TRACKER_SECRET") or secrets.token_hex(32),
        TASKS_FILE=Path(__file__).with_name("tasks.json"),
        MAX_CONTENT_LENGTH=16 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if test_config:
        app.config.update(test_config)
    store = TaskStore(app.config["TASKS_FILE"])

    @app.before_request
    def protect_forms():
        session.setdefault("csrf_token", secrets.token_hex(32))
        if request.method == "POST":
            token = request.form.get("csrf_token", "")
            if not secrets.compare_digest(token.encode("utf-8"), session["csrf_token"].encode("utf-8")):
                abort(400, description="Your form expired. Reload the page and try again.")

    def page(name="", priority="", error=None, status=200):
        with store.lock:
            tasks = store.read()
        sort_order = session.get("sort_order", "asc")
        sort_by = session.get("sort_by", "priority")
        tasks.sort(key=lambda task: task["name"].casefold() if sort_by == "name" else task["priority"],
                   reverse=sort_order == "desc")
        return render_template("index.html", tasks=tasks, name=name,
                               priority=priority, error=error, sort_order=sort_order,
                               sort_by=sort_by), status

    @app.get("/")
    def index():
        if "sort_by" in request.args:
            sort_by = request.args["sort_by"]
            session["sort_by"] = sort_by if sort_by in ("priority", "name") else "priority"
        if "sort" in request.args:
            sort_order = request.args["sort"]
            session["sort_order"] = sort_order if sort_order in ("asc", "desc") else "asc"
        return page()

    @app.post("/tasks")
    def add_task():
        name = request.form.get("name", "")
        priority = request.form.get("priority", "")
        try:
            task = Task(name, priority)
            if len(task.name) > 200:
                raise ValueError("Task name must be 200 characters or fewer.")
        except ValueError as error:
            return page(name, priority, str(error), 400)
        with store.lock:
            tasks = store.read()
            tasks.append({"id": uuid4().hex, "name": task.name, "priority": task.priority})
            store.write(tasks)
        flash("Task added.")
        return redirect(url_for("index"), code=303)

    @app.post("/tasks/<task_id>/delete")
    def delete_task(task_id):
        with store.lock:
            tasks = store.read()
            remaining = [task for task in tasks if task["id"] != task_id]
            if len(remaining) == len(tasks):
                flash("That task no longer exists. The list has been refreshed.")
            else:
                store.write(remaining)
                flash("Task removed.")
        return redirect(url_for("index"), code=303)

    @app.errorhandler(OSError)
    def storage_error(error):
        app.logger.exception("Task storage failed")
        return render_template("storage_error.html"), 503

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000)
