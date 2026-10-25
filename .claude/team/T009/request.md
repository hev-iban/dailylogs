# T009 request: description length 1..200 characters

Project root: C:/Users/Ivan/Desktop/A-Finals. Windows host, Git Bash, Python at .venv/Scripts/python.exe, Node 22,
Chrome at "C:/Program Files/Google/Chrome/Application/chrome.exe" (headless + CDP).
The user builds in explicit stages. Implement ONLY this stage.

## Current state (verified, must keep working)
- backend/routes.py: _validate_description(value) rejects missing/blank with 422 "description is required and cannot be blank";
  used by POST /api/logs and PUT /api/logs/{id}. Description is stored trimmed. No max length today.
- backend/models.py: constants (MIN_PHOTOS, MAX_PHOTOS, ...).
- backend/tests/test_logs.py: 112 passing tests incl. test_real_paths_untouched.
- frontend/index.html: textarea#description (required) in form#log-form.
- frontend/app.js: inline edit form creates its own description textarea; ERROR_HINTS maps API detail strings to
  "what to do next" hints (T008 format: "Couldn't <verb> your log: <detail>. <hint>").
- frontend/style.css: X-inspired styling, all states (T008).

## What the user asked (binding)
"add a description constrain 1 minimum and 200 maximum text"

## Binding behavior (orchestrator defaults)
- Length = number of characters (Python len, i.e. Unicode code points) of the description AFTER stripping leading/trailing
  whitespace. 1..200 inclusive is valid. Whitespace-only stays invalid (existing 422 message unchanged).
- More than 200 -> 422 with a clear detail, e.g. "description must be at most 200 characters".
- Exactly 200 accepted; 201 rejected; 200 chars plus surrounding spaces accepted (trimmed to 200).
- Applies to both create (POST) and edit (PUT). A rejected request stores nothing / changes nothing (existing guarantees).
- MAX constant lives in models.py next to the other limits.
- Frontend: both the create textarea and the edit textarea get maxlength="200" (and minlength is not needed since `required`
  plus server check covers blank). Add an ERROR_HINTS entry for the new detail ("Shorten your description to 200 characters
  or fewer and try again."). Note: browser maxlength counts UTF-16 code units, so emoji may be limited slightly earlier in the
  browser than on the server; record this, do not try to reconcile it.
- No visual counter (not asked).

## Constraints
- Edit only existing files: backend/routes.py, backend/models.py, backend/tests/test_logs.py, frontend/index.html, frontend/app.js.
  style.css only if the new error needs nothing special (it should not). No new files.
- Tests: all 112 pass (update any existing test that sends >200 chars, and record which); add tests for 1, 200, 201,
  200+surrounding spaces, whitespace-only, on both POST and PUT, and that a rejected PUT changes nothing.
- NEVER touch the project's real logs.db or uploads/ (user's real posts). Use temp paths. No new caches.
- OUT OF SCOPE: docs, Docker, the image-height and label-spacing styling tweaks.
