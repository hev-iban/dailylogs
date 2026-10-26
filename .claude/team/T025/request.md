# T025 request (from the user, verbatim)

Problem: PostgreSQL currently stores timestamps as text, which can cause incorrect
chronological ordering if timestamp formats or timezone offsets differ.

Implementation:
- Change the relevant PostgreSQL timestamp columns from TEXT to TIMESTAMPTZ.
- Ensure timestamps are timezone-aware and preferably written in UTC.
- Handle existing database rows and schema migration or initialization safely without
  losing data.
- Preserve the existing API response timestamp format.

Test:
- Insert timestamps with different UTC offsets.
- Verify that logs are ordered by actual chronological time.
- Run existing tests to confirm compatibility.

# Orchestrator notes (verify, do not trust blindly)

Current state:
- backend/database.py SCHEMA: logs.created_at / updated_at are TEXT NOT NULL, created with
  CREATE TABLE IF NOT EXISTS, so an existing database keeps TEXT columns forever unless
  migrated. init_db runs at app startup (backend/main.py ~line 70) and in the test fixture.
- Values are written by routes.py as
  datetime.now(timezone.utc).isoformat(timespec="microseconds"), e.g.
  "2026-10-26T12:00:00.123456+00:00". models.LogOut has created_at: str, updated_at: str.
- Ordering: list_logs ORDER BY created_at DESC, id DESC, with LIMIT/OFFSET (T023/T024).

Real data at stake: the user's real `dailylog` database and the Docker `pgdata` volume both
hold rows with TEXT timestamps. The migration will run against them on next app start.

Guidance:
- Migrate in init_db: for each of logs.created_at / logs.updated_at whose data_type is
  still 'text' (information_schema.columns), ALTER COLUMN ... TYPE timestamptz USING
  <col>::timestamptz. Do it in one transaction (Postgres DDL is transactional): if any row
  fails to parse, everything rolls back, the app refuses to start with a clear error, and no
  data is lost or half-converted. Idempotent: a second start is a no-op. Fresh databases get
  TIMESTAMPTZ straight from SCHEMA.
- Response format MUST stay byte-identical for the same instant: UTC, "+00:00" offset,
  microseconds always present (isoformat(timespec="microseconds")). psycopg returns
  timestamptz as an aware datetime in the SESSION time zone, which depends on the server's
  TimeZone setting (the user's machine may not be UTC). Do not rely on it: either set the
  session time zone to UTC on connect, or convert with .astimezone(timezone.utc) before
  formatting. Pick one, apply it everywhere a timestamp leaves the database (list_logs,
  get_log, insert_log/update_log return values), and test it with the session/server time
  zone set to a non-UTC zone.
- Write datetime objects (UTC) rather than strings when inserting/updating.
- Tests: the existing fixture TRUNCATEs but does not drop tables; the test DB may still
  have TEXT columns from earlier runs, which the migration will convert. Add tests for: (a)
  migration of a TEXT-column table with rows at different offsets (create the old-schema
  table in the test DB, insert, run init_db, check types, values and that row count is
  unchanged), (b) idempotency, (c) a bad text value makes init_db fail with nothing changed,
  (d) chronological ordering across offsets where text order and time order disagree
  (e.g. "2026-01-01T10:00:00+05:00" is earlier than "2026-01-01T06:00:00+00:00"), (e)
  response format unchanged under a non-UTC session/server time zone.
- specs.md / README: update where they describe storage. Add a short README note telling
  the user to back up first (pg_dump) before starting the app on a real database, since the
  migration runs automatically.

Constraints: no new dependencies (no Alembic), PEP 8, existing patterns, no git writes.
Tests and runs use TEST_DATABASE_URL=postgresql://postgres@localhost:5432/dailylog_test
only. NEVER connect to the real `dailylog` database, never start the app against it, never
use port 8000, never touch the real uploads/ or Docker volumes.
