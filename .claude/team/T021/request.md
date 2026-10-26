# T021 request (from the user, verbatim)

Problem: Two requests edit the same log simultaneously. Both read the old photo list, then
change files and database rows based on outdated information.

Implementation: In _update, start a database transaction and lock the target log row using
PostgreSQL's SELECT ... FOR UPDATE before reading its photos. Keep the lock until the
transaction finishes.

Test: Run two edits against the same log concurrently and verify that every photo row points
to an existing file and no unreferenced uploaded file remains.

Important: The lock must be acquired before reading the photo rows, and all relevant database
changes must participate in the same transaction. File operations are not automatically rolled
back with the database, so cleanup and failure handling still matter.

# Orchestrator notes (from reading the code; verify, do not trust blindly)

- `_update` is in backend/routes.py (~line 128). It opens one connection, calls
  `database.get_log` (reads the photos), validates `remove` and the photo count against that
  read, writes the new files, then calls `database.update_log` and commits. Old files are
  unlinked after the commit. On any exception the new files are unlinked.
- backend/database.py: `connect()` uses autocommit off, so psycopg opens a transaction
  implicitly on the first statement. The SELECT ... FOR UPDATE therefore just has to be the
  first statement on that connection, and the commit or rollback in `_update` releases it.
  database.py functions never commit; the caller owns the transaction. Keep that convention
  (e.g. a small helper in database.py that runs the lock query and reports whether the row
  exists).
- The 404/422 HTTPExceptions raised before the update currently rely on closing the
  connection to discard the transaction. Make sure the lock is always released on those paths
  as well (explicit rollback, or the close is enough — state which and why).
- After the fix, a second concurrent edit must see the first edit's committed photos. For
  example, if both requests remove the same photo, the second must get 422 (it is no longer a
  photo of this log). Check that this matches specs.md, and do not change the API contract.
- `_delete` does not lock explicitly, but its DELETE takes the row lock, so it serializes with
  a locked update. After the delete commits, the waiting update must return 404 and leave no
  new files behind.
- Tests: fixtures and helpers live in backend/tests/conftest.py (`env`, `make_log`, `put`,
  `rows`, `snapshot`, `make_image`). Prefer a deterministic test, e.g. hold the row lock from a
  separate test connection, start the edit in a thread, confirm it blocks, change the log and
  commit from the holding connection, then check what the edit saw. Also add the user's
  stated test: two concurrent edits on one log, after which every photo row's file exists and
  no file in uploads is unreferenced. No sleeps-as-synchronization flakiness; bound every wait
  with a timeout so a broken lock cannot hang the suite.
- Constraints: no new dependencies, no new features, keep the existing patterns, PEP 8.
  Tests use TEST_DATABASE_URL only. Never use port 8000 (the user's dev server) and never
  touch the real `dailylog` database or the real uploads/.
