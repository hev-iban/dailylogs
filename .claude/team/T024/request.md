# T024 request (from the user, verbatim)

"all test passed, add a next button and previous button and fetch the old logs and must still
be formatted to newest to oldest"

Context: T023 (done, user-verified) added ?limit to GET /api/logs: default 5, max 20, clamped
above 20, 422 below 1 or non-integer, response a bare list of LogOut, ordered created_at DESC,
id DESC. The app page currently shows only the newest 5 and cannot reach older logs. T023's
spec: .claude/team/T023/spec.xml. This task adds paging so older logs are reachable.

# Orchestrator design guidance (adopt unless you find a concrete problem; state any deviation)

API:
- Add an optional `offset` query parameter to GET /api/logs: integer >= 0, default 0;
  negative or non-integer -> 422, consistent with `limit`. LIMIT/OFFSET in list_logs, same
  ORDER BY created_at DESC, id DESC (id DESC keeps pages stable on equal timestamps).
  Photos still fetched only for the returned ids.
- Keep the response a bare list (T023 requirement: preserve the response format). No
  envelope, no total count, no headers.
- Default behavior with no params must stay exactly as T023 (newest 5).

Frontend (frontend/app.js, index.html, style.css):
- Page size 5. To know whether an older page exists without changing the response format,
  request limit=6 and render only the first 5; a 6th item means "Next" is enabled.
- "Previous" (newer logs) disabled on the first page. "Next" (older logs) disabled when no
  older page exists. Within every page, logs stay newest to oldest; page 1 is the newest.
- After creating a log: go to page 1. After editing: stay on the current page. After
  deleting: reload the current page; if it is now empty and not page 1, step back one page.
- Hide the buttons, or keep both disabled, when everything fits on one page. Pick one.
- Follow the existing frontend style: plain DOM code, the existing error display
  (loadError), aria attributes like the rest of the page, light/dark theme tokens in
  style.css. Buttons disabled while a page is loading.
- An edit form open when paging: paging re-renders the list, which already resets edit
  state (renderLogs / cancelEdit). Keep that behavior.

Docs/tests:
- specs.md: document offset; replace T023's "older logs unreachable in the UI" note with
  the paging behavior.
- Backend tests for offset (pages do not overlap, together cover every log exactly once in
  newest-first order, offset past the end returns [], 422 cases, photos correct per page).
- There are no frontend unit tests in this repo; do not add a JS test framework. The
  verifier will drive the page.

Constraints: no new dependencies, PEP 8, existing patterns, no git writes. Tests use
TEST_DATABASE_URL=postgresql://postgres@localhost:5432/dailylog_test only. Never use port
8000, the real `dailylog` database or the real uploads/.
