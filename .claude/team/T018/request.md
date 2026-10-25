# T018 request

User: "start the Pydantic form validation" (checklist item 3: "Validate the form with Pydantic. Use a Pydantic model for the description, such as a FastAPI Form model with min_length and max_length. The photo checks can stay hand-written.")

Context found by orchestrator:
- backend/routes.py: `_validate_description(value)` hand-validates the description (strip, blank -> 422 "description is required and cannot be blank", > MAX_DESCRIPTION_CHARS -> 422 "description must be at most 200 characters"). Called from create_log (POST /api/logs) and update_log (PUT /api/logs/{id}), which parse the form manually via `async with request.form() as form`.
- backend/models.py holds constants (MAX_DESCRIPTION_CHARS = 200) and the LogOut Pydantic model.
- specs.md (Validation rules, Errors table, status precedence) is the contract. routes.py docstring documents status precedence: body over limit 413 > request-shape 422 (description, photo count, non-file part, missing filename, extension) > oversized photo 413 > content 422 > 500. PUT checks 404 before the form.
- backend/tests/test_validation.py asserts exact `detail` strings for description errors, length counted in characters after trimming, description sent as a file part -> 422, and precedence cases (e.g. oversized photo + blank description -> 422 for description).
- fastapi==0.162.0 pinned (pydantic v2 comes with it).

Goal:
- Description validation is done by a Pydantic model (in models.py) with min_length / max_length (trimming via strip_whitespace / a validator as appropriate). Photo checks stay hand-written.
- Keep the external contract exactly: status codes, `detail` strings (plain string, not FastAPI's default list-of-errors body), precedence order, trimming, character counting. All existing tests must pass unchanged; do not weaken or edit existing tests. Adding focused tests is fine.
- Prefer the smallest change. Whether to use FastAPI's Form-model parameter or validate the existing parsed form with the model is the planner's call; justify it against the precedence and exact-detail requirements (a FastAPI Form dependency parses the body before the handler, which may break the 413-before-422 ordering and the PUT 404-first ordering, and returns FastAPI's default 422 body).
- No new features (checklist item 1). No new dependencies.

Safety:
- Do not modify the user's .venv. If a venv is needed, create it in the scratchpad: C:\Users\Ivan\AppData\Local\Temp\claude\C--Users-Ivan-Desktop-A-Finals\06ed2e94-8e36-4da6-bfa7-5e6605d893ff\scratchpad
- Postgres is on localhost:5432. Tests use TEST_DATABASE_URL=postgresql://postgres@localhost:5432/dailylog_test with DATABASE_URL unset. Never connect to `dailylog`, never touch uploads/, never use port 8000 (user's own server), never create/drop databases. If you start a temporary server, verify it bound to its own free port before driving it.
- Never commit or push; the user commits themselves.
