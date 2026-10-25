# T010 request: visible over-200 description error that blocks posting (replace silent maxlength truncation)

Project root: C:/Users/Ivan/Desktop/A-Finals. Windows host, Git Bash, Python at .venv/Scripts/python.exe, Node 22,
Chrome at "C:/Program Files/Google/Chrome/Application/chrome.exe" (headless + CDP: Input.insertText, Fetch interception, Network events).
The user builds in explicit stages. Implement ONLY this stage.

## Current state (verified, must keep working)
- backend: MAX_DESCRIPTION_CHARS=200 in models.py; POST/PUT reject >200 (after trim, Python len = code points) with 422
  "description must be at most 200 characters"; blank -> 422 "description is required and cannot be blank". 130 tests pass. UNCHANGED in this task.
- frontend/index.html: textarea#description has required + maxlength="200".
- frontend/app.js: create form submit (POST, aria-busy "Saving...", errors in #form-error with T008 format
  "Couldn't <verb> your log: <detail>. <hint>"); inline edit form builds its own textarea with maxLength=200;
  ERROR_HINTS includes the 200-char hint. One edit at a time.
- frontend/style.css: X-inspired, all interaction states from T008 (hover only on fine pointers, :focus-visible ring,
  contrast >= 4.5:1 light+dark, aria-busy loading indicator, error area with "⚠ Error:" prefix, nothing disabled without a visible reason).

## What the user asked (binding)
"when exceeding 200 text it should raise an error or notify that more than 200 text is not allowed and it should not be able to post it."
Problem today: maxlength silently truncates typed/pasted text, so the user never sees an error.

## Binding behavior (orchestrator defaults, X-style)
- Remove maxlength from BOTH description textareas (create and edit) so over-length text is visible, not truncated.
- Live character counter under each description textarea, "N/200", updated on every input (typing, paste, programmatic value set
  when the edit form opens). Count = Unicode code points of the trimmed text ([...value.trim()].length), matching the server.
- When count > 200: counter turns error-styled, and an inline message appears tied to that textarea
  (aria-describedby, live region, polite) e.g. "Description is too long: 237/200 characters. Remove 37 characters to post."
  textarea gets aria-invalid="true". Not color-only (text message present).
- While over 200, that form cannot post: its Save button is disabled AND the visible message explains why (meets T008
  "disabled must explain the reason"); also guard in the submit handler so no request is sent even if submit is triggered
  another way. Distinguish this from loading (no aria-busy, no spinner, label stays "Save").
- Going back to <= 200 removes the error, aria-invalid, and re-enables Save immediately.
- After a successful create, the form reset leaves the counter at 0/200 and no error.
- Opening Edit on a pre-existing post longer than 200 immediately shows the over-limit state.
- Blank handling unchanged (required + server 422).
- Keep the server 422 + hint as a safety net.
- Contrast >= 4.5:1 for counter and message in both themes; counter readable at 360px; no layout break.

## Constraints
- Edit only existing files: frontend/index.html, frontend/app.js, frontend/style.css. No backend changes. No new files.
- No innerHTML with user data. Match existing code style.
- Backend 130 tests must still pass (unchanged).
- NEVER touch the project's real logs.db or uploads/. The user often runs their own server on port 8000: any temp server
  must use a different free port, confirm the port is free first (netstat), and confirm GET /api/logs on the temp server
  returns [] before writing anything.
- OUT OF SCOPE: image-height / label-spacing tweaks, docs, Docker.
