# T012 request: split the long test file into topic files

Project root: C:/Users/Ivan/Desktop/A-Finals. Windows host, Git Bash, Python at .venv/Scripts/python.exe.
The user builds in explicit stages. Implement ONLY this stage.

## Current state (user-verified, must keep working)
- backend/tests/test_logs.py: 912 lines, one file, 130 passing tests (baseline:
  `cd backend && PYTHONDONTWRITEBYTECODE=1 ../.venv/Scripts/python.exe -m pytest -p no:cacheprovider -q tests` -> 130 passed, 1 warning).
- It holds the sys.path setup, helpers (make_image, padded_png, rows, assert_nothing_stored, post, put, snapshot, make_log,
  file_bytes, post_old, constants MAX, SHAPE, TOO_LONG), the `env` fixture, and the session autouse `_real_paths_guard`
  plus `test_real_paths_untouched` (proves the user's real logs.db and uploads/ are never touched).
- Production code: backend/main.py, database.py, models.py, routes.py; frontend/. UNCHANGED in this task.

## What the user asked (binding)
"re organize the test so that it will not be a long test file", with this layout (verbatim, all in backend/tests/):
  conftest.py              Shared pytest fixtures, test client, and test database setup.
  test_api.py              API-level integration tests covering complete request workflows.
  test_http_responses.py   HTTP status codes, response headers, and response formats.
  test_logs.py             Creating, listing, retrieving, updating, and deleting journal entries.
  test_photos.py           Photo uploads, file paths, image serving, and multiple-photo behavior.
  test_validation.py       Empty descriptions, unsupported formats, oversized files, and invalid image data.
  test_database.py         SQLite persistence, relationships between logs and photos, and database constraints

## Orchestrator defaults
- This is a MOVE, not a rewrite: every one of the 130 existing tests keeps its name, body, parametrization and assertions.
  Each test lives in exactly one file, chosen by the descriptions above. Record the mapping (test -> file) in the impl record.
- conftest.py gets the sys.path setup, the shared fixtures (env, the real-paths guard) and the helpers used by more than one
  file. pytest only auto-loads fixtures from conftest, so helper FUNCTIONS (make_image, post, put, ...) need a home that the
  test files can import cleanly; choose the simplest correct approach (e.g. keep them in conftest.py and import from it, or
  expose them as fixtures) and record why. No extra helper module unless genuinely needed; if added, record why.
- The real-paths guard must still run for the whole session and test_real_paths_untouched must still exist and pass.
- test_api.py: there are no end-to-end workflow tests today. Add a small number (1 to 3) of short workflow tests that only use
  the public API through the existing helpers, e.g. create -> list -> edit -> list -> delete -> list, and data surviving a
  new create_app on the same db/uploads (restart). Keep them short; they are the only new tests allowed. Final count = 130 + those.
- test_database.py: tests about SQLite rows, ordering ties, rollback, cascade, client-sent created_at ignored, etc. If very few
  existing tests fit, that is fine; do not invent new ones for it.
- No file should be a dumping ground; aim for each file well under ~300 lines. Keep the existing code style (comment density,
  naming). PEP 8.
- Delete nothing except the moved content from test_logs.py (test_logs.py stays, holding the CRUD tests).
- The test command stays exactly the same.

## Constraints
- Edit/create only files in backend/tests/. Do not touch production code, the real logs.db or uploads/.
- Do not run any server on port 8000. Tests use tmp paths only.
- Remove any __pycache__ you create (use PYTHONDONTWRITEBYTECODE=1 and -p no:cacheprovider).
- OUT OF SCOPE: changing what a test asserts, docs, Docker.
