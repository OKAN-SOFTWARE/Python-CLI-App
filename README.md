# Task Tracker

A local Flask web app with a responsive HTML/CSS front end. Add tasks, view them
in ascending priority order (1–5), and remove them. Task names and priorities are
validated in the browser and on the server. Invalid submissions preserve your input.

Click **Priority** or **Name** above the task list to sort by that field. Click
the active control again to toggle ascending (↑) and descending (↓) order.
Names sort alphabetically without regard to capitalization. The selection stays
active in your browser session when adding or removing tasks.

## Run on Windows (PowerShell)

Requires Python 3.9 or newer. From this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:5000. Stop the server with Ctrl+C.

## Files and storage

- `app.py`: Flask routes, form protection, and JSON storage.
- `templates/`: server-rendered HTML pages.
- `static/style.css`: responsive styling; no external assets or JavaScript needed.
- `task_tracker.py`: original CLI and shared task validation.
- `tasks.json`: created beside `app.py` on the first successful addition. Tasks
  survive server restarts. Back up this file to keep a copy of your tasks.

Each task has a stable ID, name, and integer priority. Writes replace the file
atomically; damaged files produce a storage error rather than being overwritten.
The file path is independent of the directory from which you launch the app.

This is a single-process, local-use app with no accounts. Run one server instance
per data file. The original CLI (`python task_tracker.py`) still uses its own
in-memory list and does not share the web app's saved tasks.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Copyright

Copyright © 2026 OKAN TIKTAS. All rights reserved.
