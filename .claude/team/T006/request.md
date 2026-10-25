# T006 request: Edit button updates a log's description and photos

Project root: C:/Users/Ivan/Desktop/A-Finals. Windows host, Git Bash, Python at .venv/Scripts/python.exe, Node 22 available.
Chrome at "C:/Program Files/Google/Chrome/Application/chrome.exe" (headless + --remote-debugging-port works for driving clicks via CDP).
The user builds in explicit stages. Implement ONLY this stage.

## Current state (passed verification, must keep working)
- backend/main.py: create_app(db_path, uploads_dir, ...); serves / (index.html), /static/ (frontend/), /uploads/ (uploads dir); body-limit middleware.
- backend/routes.py: POST /api/logs (create; all upload validation helpers live here), GET /api/logs (newest first).
  Log shape: {id, description, photos: ["uploads/<uuid>.<ext>", ...], created_at, updated_at}; UTC ISO timestamps with fixed microseconds.
- backend/database.py: schema logs(id, description, created_at, updated_at), photos(id, log_id, path, position); insert_log, list_logs.
- backend/models.py: constants (MIN_PHOTOS=1, MAX_PHOTOS=5, MAX_PHOTO_BYTES=5 MiB, allowed formats), LogOut.
- backend/tests/test_logs.py: 70 passing tests.
- frontend/index.html: form#log-form, ul#log-list, template#log-template (li.log > time.log-date, p.log-description,
  div.log-photos, div.log-actions > button.edit-button, button.delete-button).
- frontend/app.js: loadLogs() renders the list; Save on the create form POSTs to /api/logs, shows errors in #form-error,
  resets and reloads on success. Descriptions are inserted with textContent only.
- frontend/style.css: EMPTY, leave it empty.
Earlier full-app spec with edit rules, for reference: .claude/team/T001/spec.xml (criteria 7, 10, 11).

## What the user asked
"make the edit button update the log description and photos"

## Binding behavior (orchestrator defaults, derived from the user's original brief)
Backend: PUT /api/logs/{id} (multipart):
- fields: description (required, same rules as create), photos (new files to add, 0..n, same per-file validation as create),
  remove_photos (repeatable; existing photo paths exactly as returned by the API, e.g. "uploads/<uuid>.png").
- The final photo count (existing - removed + added) must be 1..5, else 422.
- remove_photos values not belonging to this log -> 422.
- Same status codes as create: 422 validation, 413 oversize photo/body, 404 unknown log id, 500 unexpected.
- On success: 200 with the updated log (same shape); updated_at set to now; created_at unchanged; kept photos keep their
  order and new photos are appended; removed photo files are deleted from disk.
- On any failure: the log row, its photos, and the files on disk are all unchanged, and no new files are left behind.
Frontend:
- Clicking a post's Edit button switches that post to an inline edit form with: a description textarea pre-filled,
  each existing photo shown with a "Remove" checkbox, a file input for new photos (same accept list, multiple),
  Save and Cancel buttons, and an error area.
- Save PUTs to /api/logs/{id}; on success reload the list; on error show the API's detail message in that post's error area
  and keep the edit form open with the user's input.
- Cancel restores the normal view with no request.
- Only one post in edit mode at a time is acceptable either way; implementer's choice, record it.
- User text goes in only via textContent/value, never innerHTML.

## Constraints
- Edit only existing files (backend/routes.py, backend/database.py, backend/models.py if needed, backend/tests/test_logs.py,
  frontend/app.js, frontend/index.html only if strictly needed). No new files. Reuse the existing create validation helpers.
- The log id must be available to the frontend (it already is in the API response).
- OUT OF SCOPE: Delete button, GET /api/logs/{id} (unless strictly needed), style.css, docs, Docker.
- Tests: all 70 existing pass; add backend tests for every rule above, including file-on-disk effects.
- Do NOT touch the user's real project logs.db or uploads/ contents; use temp paths. Leave no __pycache__/.pytest_cache.
