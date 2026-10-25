# DailyLog

A personal journaling web app. Record your day with a description and 1 to 5 photos, then
view, edit, or delete your entries later. Everything is stored locally and survives restarts.
No account is needed.

See [specs.md](specs.md) for the full specification, validation rules, and API.

## Requirements

- Python 3.12 (the version CI and the Docker image use)
- PostgreSQL (the app and the tests each use their own database)

Or only Docker: `docker compose up` runs the app with its own Postgres (see
[Run with Docker](#run-with-docker)).

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

## Database setup

1. Create two empty databases, `dailylog` (the app) and `dailylog_test` (the tests; wiped
   before every test):

   ```bash
   createdb -U postgres dailylog
   createdb -U postgres dailylog_test
   ```

2. Put the password in the libpq password file `%APPDATA%\postgresql\pgpass.conf`, one line:

   ```
   localhost:5432:*:postgres:<password>
   ```

   The connection URLs below then carry no password.

3. Set `DATABASE_URL` before starting the app. If it is not set, the app refuses to start.

   ```bash
   export DATABASE_URL=postgresql://postgres@localhost:5432/dailylog
   ```

4. Set `TEST_DATABASE_URL` before running the tests. Its database name must end in `_test`
   and it must differ from `DATABASE_URL`, otherwise the run is refused.

   ```bash
   export TEST_DATABASE_URL=postgresql://postgres@localhost:5432/dailylog_test
   ```

The tables are created automatically on first start.

## Run

```bash
cd backend
DATABASE_URL=postgresql://postgres@localhost:5432/dailylog uvicorn main:app --reload
```

Open http://127.0.0.1:8000 in your browser. Interactive API docs are at
http://127.0.0.1:8000/docs.

On first start the app creates the tables in the database and the `uploads/` folder in the project root
(not inside `backend/`), whichever folder you start it from.

## Test

```bash
cd backend
TEST_DATABASE_URL=postgresql://postgres@localhost:5432/dailylog_test python -m pytest -q tests
```

The tests use the `_test` database and a temporary uploads folder, so they never touch your real entries.
A guard in `conftest.py` fails the run if your real `uploads/` change.

GitHub Actions runs the same suite on pushes to `main` and on pull requests
(`.github/workflows/tests.yml`).

| File | Covers |
|---|---|
| `conftest.py` | Shared fixtures, test client, test database safety check and wipe, uploads setup |
| `test_api.py` | Complete workflows (create, list, edit, delete) and restart persistence |
| `test_http_responses.py` | The page, static files, status codes and response formats |
| `test_logs.py` | Creating, listing, updating and deleting entries |
| `test_photos.py` | Photo uploads, file paths, image serving, multiple photos |
| `test_validation.py` | Descriptions, formats, file sizes, invalid image data |
| `test_description_model.py` | The Pydantic description model: trimming, character counting, error messages |
| `test_database.py` | PostgreSQL persistence, ordering, rollback, missing `DATABASE_URL`, log and photo relationships |

## Project structure

```
backend/
  main.py           App setup: serves the page, static files, uploads, and the API
  routes.py         API endpoints and validation (/api/logs)
  database.py       PostgreSQL schema and queries
  models.py         Limits, paths, the description input model, and the response model
  tests/            pytest suite (see above)
frontend/
  index.html        Web page
  style.css         Styles, light and dark themes
  app.js            Loads, creates, edits, and deletes logs through the API
uploads/            Stored photos (created at runtime)
requirements.txt    Python dependencies
specs.md            Specification
Dockerfile          Builds the API image (Python 3.12 slim, uvicorn on port 8000)
compose.yaml        Runs the API and Postgres 17 with volumes for data and photos
.dockerignore       Keeps .venv, .git, uploads and secrets out of the image
.github/workflows/
  tests.yml         CI: runs pytest against a Postgres 17 service container
```

## Run with Docker

```bash
docker compose up --build
```

Open http://localhost:8080. Change the host port with `API_PORT` (for example
`API_PORT=9000 docker compose up`). Postgres is not published to the host, so it does not
clash with a local Postgres or dev server.

Entries and photos live in the named volumes `pgdata` and `uploads` and survive
`docker compose down` and restarts. `docker compose down -v` deletes them.

The database user, password, and name default to dev-only values; override them with
`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` in the shell or a git-ignored `.env`.
Set them before the first start, since Postgres keeps the original password in the volume.


