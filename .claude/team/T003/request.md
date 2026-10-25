# T003 request: list logs, newest to oldest by created_at

Project root: C:/Users/Ivan/Desktop/A-Finals. Windows host, Git Bash. Python 3.12, venv at .venv/.
The user builds in explicit stages. Implement ONLY this stage.

## Current state (T002, verified by the user, must keep working unchanged)
backend/main.py (app wiring, body-limit middleware, create_app(db_path, uploads_dir)),
backend/database.py (schema: logs(id, description, created_at, updated_at), photos(id, log_id, path, position); insert_log),
backend/models.py (constants, LogOut model: id, description, photos: list[str], created_at, updated_at),
backend/routes.py (POST /logs), backend/tests/test_logs.py (44 tests).
created_at/updated_at are already set automatically on create (UTC ISO 8601, e.g. 2026-10-24T05:51:26.415363+00:00).
Prior spec for reference: C:/Users/Ivan/Desktop/A-Finals/.claude/team/T002/spec.xml

## What the user asked
"implement created_at and it should be posted by the newest to oldest"
Interpretation (binding unless contradictory): created_at is the automatic creation timestamp
(already implemented; confirm it is set server-side and cannot be supplied or overridden by the client).
Add GET /logs returning all logs ordered newest to oldest by created_at, each with id, description,
photos (in upload order), created_at, updated_at, same shape as the POST response. Empty store returns [].
Ties on created_at broken deterministically (newest id first).

## Constraints
- Only edit existing files in backend/ (routes.py, database.py, models.py, main.py if needed, tests/test_logs.py).
  No new files. Do not touch frontend/, Docker files, README.md, specs.md, requirements.txt.
- OUT OF SCOPE: GET /logs/{id}, edit, delete, pagination, search/date filter, frontend.
- Existing 44 tests must still pass; add tests for ordering, empty list, response shape,
  and that a client-supplied created_at is ignored.
- Tests use an isolated temp DB/uploads. Leave no DB, uploads, or __pycache__/.pytest_cache in the project.
