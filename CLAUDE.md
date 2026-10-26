# CLAUDE.md

DailyLog: a single-user journaling app. FastAPI backend, PostgreSQL, photos on disk in
`uploads/`, plain HTML/CSS/JS frontend. No login.

- `README.md`: setup, run, test, Docker, project structure.
- `specs.md`: the specification. It is the source of truth for validation rules, limits,
  status codes and the API contract. Read it before changing behavior.

## Commands

Run from `backend/` (imports are flat: `import database`, `from models import ...`). The venv
is at the repo root: `source .venv/Scripts/activate`. Postgres must be running first
(`pg_isready -h localhost -p 5432`); if it is not, the tests hang on connect instead of
failing.

```bash
# Tests (needs a database whose name ends in _test)
TEST_DATABASE_URL=postgresql://postgres@localhost:5432/dailylog_test python -m pytest -q tests

# App
DATABASE_URL=postgresql://postgres@localhost:5432/dailylog uvicorn main:app --reload

# Docker (API on http://localhost:8080, Postgres not published)
docker compose up --build
```

CI (`.github/workflows/tests.yml`) runs the same pytest command against a Postgres 17
service on every push, to any branch, and on pull requests.

## Rules

- **No new features.** Search and filtering are listed in `specs.md` as a later stage. Fix,
  refactor and test what exists; ask before adding behavior.
- **Never touch the user's real data.** The real database is `dailylog` and the real photos
  are in `uploads/`. Tests must use `TEST_DATABASE_URL` and the temporary uploads folder from
  `conftest.py`. Do not weaken the `_test` name guard or the uploads guard in `conftest.py`.
- **Port 8000 belongs to the user's dev server.** If you start a server for testing, use a
  free high port (e.g. 87xx), confirm it actually bound, and confirm requests reach it
  before sending anything that writes.
- **Do not commit, push, or create branches yourself.** Propose the branch name, commit
  message and file list, then wait. The user commits one checklist item at a time, so keep
  unrelated changes separate.
- **Work in the stages the user names.** "Structure first" means empty files and folders
  only, with no code until asked.
- Keep the existing patterns: plain SQL with psycopg in `database.py` (`%s` placeholders, the
  current transaction handling), the Pydantic `DescriptionIn` model for the description,
  hand-written photo checks in `routes.py`. Limits and paths live in `models.py`.
- **Edits lock the log row first.** `_update` calls `database.lock_log` (`SELECT ... FOR
  UPDATE`) before reading the photos. Any new edit path must take the lock first and do all
  its database changes in that same transaction.
- **Timestamps are `TIMESTAMPTZ`.** Write aware UTC datetimes; every timestamp leaving the
  database goes through `database._fmt` (UTC, `+00:00`, six fractional digits). Never rely on
  the session time zone.
- **`GET /api/logs` is paged.** `limit` (default `DEFAULT_LIST_LIMIT` = 5, clamped to
  `MAX_LIST_LIMIT` = 20) and `offset`, newest first; the response stays a bare list. The page
  shows 5 and requests 6 to know whether an older page exists.
- **Schema changes go in `init_db`**: one transaction, safe to run twice, no migration tool.
  They run automatically on the real database and the Docker `pgdata` volume at the next
  start, so the README must tell the user to back up (`pg_dump`) first.
- **Never run `docker compose down -v`.** It deletes the `pgdata` and `uploads` volumes, i.e.
  the user's Docker logs and photos.
- Keep `specs.md`, `README.md` and the tests in step with any behavior change.
- Pin dependency versions in `requirements.txt`. Python 3.12. PEP 8.
- No emojis.
