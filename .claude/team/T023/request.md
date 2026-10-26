# T023 request (from the user, verbatim)

Problem: Every request loads every log and every photo row, which becomes slower as the
journal grows.

Implementation:
- Return 5 logs per request by default.
- Set a maximum limit of 20 logs per request.
- Retrieve logs in newest-first order.
- Fetch photo records only for the logs included in the response.
- Preserve the existing API response format.

Test:
- Confirm that the default request returns up to 5 logs.
- Confirm that a custom limit works.
- Confirm that requests exceeding 20 logs return no more than 20.
- Verify newest-first ordering and correct photo retrieval.

# Orchestrator notes (verify, do not trust blindly)

Binding decisions from the user's text; do not ask about these again:
- Optional query parameter `limit` on GET /api/logs, default 5, maximum 20.
- A limit above 20 is CLAMPED to 20 ("return no more than 20"), not rejected.
- Response format unchanged: still a JSON list of LogOut objects. No envelope, no count.
- Ordering unchanged: created_at DESC, id DESC (see database.list_logs).

Left to the planner (pick the conventional option, state it in the spec, do not block):
- limit < 1 or non-integer: suggest 422, consistent with the API's other input errors.

Code facts:
- backend/database.py list_logs currently selects every log, then every photo row
  ("SELECT log_id, path FROM photos ORDER BY position, id"). The change: LIMIT on the logs
  query, then fetch photos only WHERE log_id = ANY(%s) for those ids, keeping the
  position, id order. Plain SQL with psycopg, %s placeholders, as the file does now.
- backend/routes.py list_logs endpoint calls _list(database_url) in a threadpool.
- Limits live in backend/models.py (MAX_PHOTOS etc.); put the default and max there.
- specs.md says core feature 2 is "all entries, newest first" and documents GET /api/logs;
  update it to match. README if it describes the endpoint.
- Existing tests that call GET /api/logs may assume all logs are returned (e.g. creating
  more than 5 logs then listing). Find and adjust them. Do not weaken what they check.

Known consequence, out of scope unless the user asks: frontend/app.js loads the list with a
plain GET, so after this change the page shows only the newest 5 logs and older ones are not
reachable in the UI (there is no paging). Do NOT add paging or change the frontend. Record
this consequence in the spec's notes so the user sees it.

Constraints: no new dependencies, PEP 8, existing patterns. Tests use TEST_DATABASE_URL
only. Never use port 8000, the real `dailylog` database or the real uploads/. No git writes.
