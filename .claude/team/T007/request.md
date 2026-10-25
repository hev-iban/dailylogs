# T007 request: Delete button deletes a post and its uploaded photos

Project root: C:/Users/Ivan/Desktop/A-Finals. Windows host, Git Bash, Python at .venv/Scripts/python.exe, Node 22 available.
Chrome at "C:/Program Files/Google/Chrome/Application/chrome.exe" (headless + CDP works for real clicks; Page.javascriptDialogOpening / Page.handleJavaScriptDialog handle confirm()).
The user builds in explicit stages. Implement ONLY this stage.

## Current state (passed verification, must keep working)
- backend/routes.py: POST /api/logs (create), GET /api/logs (newest first), PUT /api/logs/{id} (edit: description, photos, remove_photos).
- backend/database.py: logs(id, description, created_at, updated_at), photos(id, log_id REFERENCES logs(id) ON DELETE CASCADE, path, position); PRAGMA foreign_keys=ON.
- backend/main.py: serves /, /static/, /uploads/; body-limit middleware. backend/models.py constants.
- backend/tests/test_logs.py: 101 passing tests, incl. test_real_paths_untouched (before/after snapshot of real logs.db and uploads/).
- frontend/app.js: renders posts from the template (button.delete-button exists but has no handler), create form, inline edit (one post at a time; module-level `editing` state).
- frontend/index.html and frontend/style.css (EMPTY) must stay unchanged.
Reference: .claude/team/T006/spec.xml (edit behavior), .claude/team/T001/spec.xml criterion 12.

## What the user asked
"delete function for the next one that will delete the uploaded post"

## Binding behavior (orchestrator defaults from the user's original brief: "Delete logs: Remove entries and their associated images")
Backend: DELETE /api/logs/{id}
- 200 (or 204, implementer's choice, record it) on success; the log row and all its photo rows are removed and every one of its
  photo files is deleted from the uploads dir. Subsequent GET /api/logs no longer lists it. Other logs and their files are untouched.
- Unknown id -> 404, nothing changed. Non-integer id -> 422 (FastAPI default) or 404, record which.
- A photo file already missing on disk must not make the delete fail.
- Delete the DB rows first (commit), then the files; a file-removal failure after commit must not resurrect the row or 500 the request.
- Unexpected DB error -> 500 and nothing deleted.
Frontend:
- Clicking a post's Delete button asks for confirmation (window.confirm is fine). Cancel -> no request, nothing changes.
- Confirm -> DELETE /api/logs/{id}; on success reload the list (empty-message appears if it was the last post);
  on failure show the API's detail message visibly for that post, and leave the post in place.
- Deleting the post currently in edit mode, or while another post is in edit mode, must not leave stale edit state.
- Disable the Delete button while the request is in flight.

## Constraints
- Edit only existing files: backend/routes.py, backend/database.py, backend/tests/test_logs.py, frontend/app.js. No new files.
- Do not change existing endpoints' behavior.
- Tests: all 101 pass; add tests for every backend rule above, including on-disk file effects and other-log isolation.
- NEVER touch the project's real logs.db or uploads/ (the user has real posts there). Use temp paths.
  Leave no new __pycache__/.pytest_cache.
- OUT OF SCOPE: style.css, docs, Docker, an "edited" indicator, undo/trash.
