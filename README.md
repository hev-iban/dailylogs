# DailyLog

A personal journaling web app. Record your day with a description and 1 to 5 photos, then
view, edit, or delete your entries later. Everything is stored locally and survives restarts.
No account is needed.

See [specs.md](specs.md) for the full specification, validation rules, and API.

## Requirements

- Python 3.10 or newer

## Setup

From the project root:

```bash
python -m venv .venv
```

Activate the virtual environment:

```bash
# Windows (Git Bash)
source .venv/Scripts/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

## Run

```bash
cd backend
uvicorn main:app --reload
```

Open http://127.0.0.1:8000 in your browser. Interactive API docs are at
http://127.0.0.1:8000/docs.

On first start the app creates `logs.db` and the `uploads/` folder in the project root
(not inside `backend/`), whichever folder you start it from.

## Test

```bash
cd backend
python -m pytest -q tests
```

The tests use a temporary database and uploads folder, so they never touch your real entries.
A guard in `conftest.py` fails the run if your real `logs.db` or `uploads/` change.

| File | Covers |
|---|---|
| `conftest.py` | Shared fixtures, test client, temporary database and uploads setup |
| `test_api.py` | Complete workflows (create, list, edit, delete) and restart persistence |
| `test_http_responses.py` | The page, static files, status codes and response formats |
| `test_logs.py` | Creating, listing, updating and deleting entries |
| `test_photos.py` | Photo uploads, file paths, image serving, multiple photos |
| `test_validation.py` | Descriptions, formats, file sizes, invalid image data |
| `test_database.py` | SQLite persistence, ordering, rollback, log and photo relationships |

## Project structure

```
backend/
  main.py           App setup: serves the page, static files, uploads, and the API
  routes.py         API endpoints and validation (/api/logs)
  database.py       SQLite schema and queries
  models.py         Limits, paths, and the response model
  tests/            pytest suite (see above)
frontend/
  index.html        Web page
  style.css         Styles, light and dark themes
  app.js            Loads, creates, edits, and deletes logs through the API
uploads/            Stored photos (created at runtime)
logs.db             SQLite database (created at runtime)
requirements.txt    Python dependencies
specs.md            Specification
Dockerfile          Not set up yet
compose.yaml        Not set up yet
```


