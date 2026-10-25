# T004 request: serve the frontend from FastAPI and move the API under /api

Project root: C:/Users/Ivan/Desktop/A-Finals. Windows host, Git Bash, Python at .venv/Scripts/python.exe.
The user builds in explicit stages. Implement ONLY this stage.

## Current state (verified by the user, must keep working)
- backend/main.py: create_app(db_path, uploads_dir, max_request_bytes), BodyLimitMiddleware, includes routes.router. Run from backend/: uvicorn main:app
- backend/routes.py: POST /logs (create, all upload rules) and GET /logs (list newest first)
- backend/database.py, backend/models.py
- backend/tests/test_logs.py: 50 passing tests calling /logs
- frontend/index.html (structure only), frontend/style.css and frontend/app.js (both EMPTY, leave them empty)
- index.html currently links href="style.css" and src="app.js"
Previous specs for reference: .claude/team/T002/spec.xml, .claude/team/T003/spec.xml (same root).

## What the user asked (binding)
"mount the app.js and style.css on static/ and route the frontend to fastapi
('/' serve the index.html), ('api/logs' the existing journal api)"
1. Serve the frontend/ folder's static files at /static/ (so /static/style.css and /static/app.js work).
2. GET / returns frontend/index.html.
3. The existing journal API moves from /logs to /api/logs (POST and GET). All behavior, validation,
   status codes and ordering stay exactly the same. The old /logs path no longer exists.
4. Update index.html's two references to /static/style.css and /static/app.js. No other HTML changes.

## Constraints
- Edit only existing files: backend/main.py, backend/routes.py, frontend/index.html, backend/tests/test_logs.py
  (and models.py only if a path constant naturally lives there). No new files.
- The frontend path must resolve regardless of the current working directory (the server is started from backend/).
- Update the tests to the new paths; all existing coverage must remain. Add tests for GET / (returns the HTML),
  /static/style.css and /static/app.js (200), and that /logs no longer exists.
- OUT OF SCOPE: serving uploaded photos over HTTP, app.js/style.css content, edit/delete/get-one endpoints, Docker, docs.
- Leave no DB, uploads files, __pycache__ or .pytest_cache in the project.
