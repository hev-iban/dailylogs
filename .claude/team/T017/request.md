# T017 request

User: "yes upgrade fastapi" (in reply to: CI shows 136 passed, 133 warnings; option 1 was upgrading fastapi so they go away).

Context found by orchestrator:
- requirements.txt pins: fastapi==0.110, uvicorn==0.29, python-multipart==0.0.9, pillow==10.0, httpx==0.27, pytest==8.0, psycopg[binary]==3.3.6. Exact-pin style, keep it.
- User's .venv currently: starlette 0.36.3 (from fastapi 0.110), anyio 4.15.1 (unpinned, transitive), httpx 0.27.0.
- Warnings in CI and locally: 132x httpx "The 'app' shortcut is now deprecated" (starlette TestClient passes app= to httpx), 1x "anyio.abc.BlockingPortal alias is deprecated" from starlette/testclient.py.
- Latest fastapi on PyPI is 0.162.0.
- CI: .github/workflows/tests.yml runs `pip install -r requirements.txt` then `python -m pytest -q tests` in backend, Python 3.12, Postgres 17.

Goal:
- Upgrade fastapi to a current exact-pinned version so those 133 deprecation warnings go away, with all 136 tests still passing.
- Bump other pins (httpx, uvicorn, python-multipart, ...) only if the new fastapi/starlette requires it or if needed to clear the warnings; justify each.
- App code and tests change only if the upgrade breaks something; keep changes minimal and do not weaken any test. Prefer zero code changes.
- Do not hide warnings with filterwarnings.
- Known pre-existing Windows-only failure: tests/test_photos.py::test_uploads_traversal_refused[/uploads/....//secret.txt] (Starlette StaticFiles commonpath raises "Paths don't have the same drive" on Windows). Out of scope, but note whether the upgrade changes it.

Safety:
- Do not modify the user's .venv. Use a fresh venv in the scratchpad: C:\Users\Ivan\AppData\Local\Temp\claude\C--Users-Ivan-Desktop-A-Finals\b768432a-9d47-4021-84b7-340b256539be\scratchpad
- Postgres is running on localhost:5432. Tests use TEST_DATABASE_URL=postgresql://postgres@localhost:5432/dailylog_test with DATABASE_URL unset. Never connect to `dailylog`, never touch logs.db or uploads/, never use port 8000, never create/drop databases.
- Never commit or push; user commits themselves.
