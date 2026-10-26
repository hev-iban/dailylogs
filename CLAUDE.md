# CLAUDE.md

DailyLog: a single-user journaling app. FastAPI backend, PostgreSQL, photos on disk in
`uploads/`, plain HTML/CSS/JS frontend. No login.

- `README.md`: setup, run, test, Docker, project structure.
- `specs.md`: the specification. It is the source of truth for validation rules, limits,
  status codes and the API contract. Read it before changing behavior.

## Commands

Run from `backend/` (imports are flat: `import database`, `from models import ...`).

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
- Keep `specs.md`, `README.md` and the tests in step with any behavior change.
- Pin dependency versions in `requirements.txt`. Python 3.12. PEP 8.
- No emojis.
