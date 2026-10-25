# T005 request: app.js loads and displays existing logs; serve photos from /uploads/

Project root: C:/Users/Ivan/Desktop/A-Finals. Windows host, Git Bash, Python at .venv/Scripts/python.exe.
The user builds in explicit stages. Implement ONLY this stage.

## Current state (passed verification, must keep working)
- backend/main.py: create_app(db_path, uploads_dir, ...), serves frontend/ at /static/, GET / returns frontend/index.html.
- backend/routes.py: POST /api/logs (create, upload rules), GET /api/logs (list newest first).
  Each log: {id, description, photos: ["uploads/<uuid>.<ext>", ...], created_at, updated_at}, with UTC ISO timestamps.
- backend/models.py (constants incl. UPLOADS_URL_PREFIX = "uploads"), backend/database.py
- backend/tests/test_logs.py: 55 passing tests.
- frontend/index.html: header, create form, <section id="logs"> with <ul id="log-list"> and <p id="empty-message" hidden>,
  and <template id="log-template"> containing li.log > time.log-date, p.log-description, div.log-photos,
  div.log-actions > button.edit-button, button.delete-button. Loads /static/style.css and /static/app.js.
- frontend/app.js and frontend/style.css are EMPTY.
Previous spec for reference: .claude/team/T004/spec.xml (same root).

## What the user asked (binding)
"app.js make the page load the existing entries from api and display them. the [page] should request the
existing logs endpoint when the page is open; each log's description and date appear on page. its photo
should load from /uploads/"
1. When the page opens, app.js requests GET /api/logs and renders every log in #log-list using #log-template,
   keeping the API's newest-first order.
2. Each rendered log shows its description, its date (created_at in a readable local format; the <time> element's
   datetime attribute holds the original ISO value), and all its photos as <img> elements loaded from /uploads/<filename>.
3. If there are no logs, show #empty-message.
4. If the request fails, show a visible error message on the page instead of failing silently.
5. Backend: serve the uploads directory (the one passed to create_app) at /uploads/ so those images load.
   Serving must stay confined to the uploads directory (no path traversal out of it).

## Constraints
- Edit only existing files: frontend/app.js, backend/main.py, backend/tests/test_logs.py
  (index.html only if strictly needed for the error message; models.py only if a constant naturally lives there). No new files.
- Insert descriptions as text, never as HTML (no innerHTML with user data), so markup in a description is not executed.
- Plain JavaScript, no libraries, no build step.
- OUT OF SCOPE: form submit/Save, Edit and Delete behavior, style.css, docs, Docker. Edit/Delete buttons are rendered but do nothing.
- Add backend tests: an uploaded photo is retrievable at /uploads/<filename> with 200, a missing file returns 404, traversal is refused.
  All 55 existing tests must still pass.
- Leave no DB, uploads files, __pycache__ or .pytest_cache in the project.
