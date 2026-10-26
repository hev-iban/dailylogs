"""Concurrent edits of one log: the row lock serializes them (SELECT ... FOR UPDATE).

Overlap is forced by holding the row lock from a separate connection. Every wait is
polled with a timeout (no sleeps as synchronization) so a broken lock fails the test.
"""
import threading
import time
from contextlib import contextmanager

import psycopg

from conftest import make_image, make_log, put, rows, snapshot

TIMEOUT = 15


def _blocked_count(db):
    with psycopg.connect(db, autocommit=True) as conn:
        return conn.execute(
            "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() "
            "AND pid <> pg_backend_pid() AND wait_event_type = 'Lock'").fetchone()[0]


def wait_blocked(db, n=1):
    """Poll until n sessions wait on a lock; fail after TIMEOUT."""
    deadline = time.monotonic() + TIMEOUT
    pause = threading.Event()
    while time.monotonic() < deadline:
        if _blocked_count(db) >= n:
            return
        pause.wait(0.02)
    raise AssertionError(f"{n} session(s) never blocked on the row lock")


class Call(threading.Thread):
    """Run fn() in a thread and keep its result; join with a timeout."""

    def __init__(self, fn):
        super().__init__(daemon=True)
        self.fn = fn
        self.result = None
        self.error = None

    def run(self):
        try:
            self.result = self.fn()
        except Exception as exc:  # surfaced by finish()
            self.error = exc

    def finish(self):
        self.join(TIMEOUT)
        assert not self.is_alive(), "edit did not finish: lock never released"
        assert self.error is None, self.error
        return self.result


@contextmanager
def holder(db, log_id):
    """A separate connection that holds the row lock on the log."""
    conn = psycopg.connect(db)
    try:
        conn.execute("SELECT id FROM logs WHERE id = %s FOR UPDATE", (log_id,))
        yield conn
    finally:
        conn.rollback()
        conn.close()


def referenced_files(db):
    return {p["path"].rsplit("/", 1)[-1] for p in rows(db)[1]}


def assert_files_match_rows(db, uploads):
    on_disk = {p.name for p in uploads.iterdir()}
    assert on_disk == referenced_files(db)


def test_edit_blocks_until_holder_ends(env):
    client, db, uploads = env
    log = make_log(client, 2)
    with holder(db, log["id"]) as conn:
        t = Call(lambda: put(client, log["id"], description="new"))
        t.start()
        wait_blocked(db)
        assert t.is_alive()
        conn.rollback()
    assert t.finish().status_code == 200


def test_waiting_edit_sees_photos_committed_by_holder(env):
    client, db, uploads = env
    log = make_log(client, 3)
    victim = log["photos"][0]
    before = snapshot(db, uploads)
    with holder(db, log["id"]) as conn:
        t = Call(lambda: put(client, log["id"], description="late", remove=[victim],
                             add=[make_image()]))
        t.start()
        wait_blocked(db)
        conn.execute("UPDATE photos SET path = %s WHERE path = %s",
                     ("/uploads/replaced.png", victim))
        conn.commit()
    resp = t.finish()
    assert resp.status_code == 422
    assert resp.json()["detail"] == "remove_photos must be photos of this log"
    after_rows, after_files = snapshot(db, uploads)
    assert after_files == before[1]
    assert after_rows[0] == before[0][0]  # log row unchanged
    assert [p["path"] for p in after_rows[1]].count("/uploads/replaced.png") == 1


def test_two_edits_removing_same_photo_one_wins(env):
    client, db, uploads = env
    log = make_log(client, 3)
    victim = log["photos"][0]
    with holder(db, log["id"]):
        threads = [Call(lambda: put(client, log["id"], remove=[victim])) for _ in range(2)]
        for t in threads:
            t.start()
        wait_blocked(db, 2)
    codes = sorted(t.finish().status_code for t in threads)
    assert codes == [200, 422]
    assert_files_match_rows(db, uploads)


def test_two_concurrent_edits_leave_no_orphans(env):
    client, db, uploads = env
    for _ in range(3):
        log = make_log(client, 3)
        a, b = log["photos"][0], log["photos"][1]
        with holder(db, log["id"]):
            threads = [
                Call(lambda: put(client, log["id"], remove=[a], add=[make_image()])),
                Call(lambda: put(client, log["id"], remove=[b], add=[make_image()])),
            ]
            for t in threads:
                t.start()
            wait_blocked(db, 2)
        assert [t.finish().status_code for t in threads] == [200, 200]
        logs, photos = rows(db)
        assert len([p for p in photos if p["log_id"] == log["id"]]) == 3
        assert_files_match_rows(db, uploads)
        client.delete(f"/api/logs/{log['id']}")
        assert list(uploads.iterdir()) == []


def test_later_edit_over_five_photos_is_rejected_without_files(env):
    client, db, uploads = env
    log = make_log(client, 3)
    with holder(db, log["id"]):
        threads = [Call(lambda: put(client, log["id"], add=[make_image(), make_image()]))
                   for _ in range(2)]
        for t in threads:
            t.start()
        wait_blocked(db, 2)
    assert sorted(t.finish().status_code for t in threads) == [200, 422]
    assert len(rows(db)[1]) == 5
    assert_files_match_rows(db, uploads)


def test_edit_of_log_deleted_while_waiting_returns_404(env):
    client, db, uploads = env
    log = make_log(client, 2)
    with holder(db, log["id"]) as conn:
        t = Call(lambda: put(client, log["id"], add=[make_image()]))
        t.start()
        wait_blocked(db)
        conn.execute("DELETE FROM logs WHERE id = %s", (log["id"],))
        conn.commit()
        for p in uploads.iterdir():  # the delete's own file removal
            p.unlink()
    resp = t.finish()
    assert resp.status_code == 404
    assert resp.json()["detail"] == "log not found"
    assert list(uploads.iterdir()) == []


def test_unknown_id_returns_404_without_files(env):
    client, db, uploads = env
    resp = put(client, 999, add=[make_image()])
    assert resp.status_code == 404
    assert resp.json()["detail"] == "log not found"
    assert not uploads.exists() or list(uploads.iterdir()) == []


def _assert_lock_free(db, log_id):
    with psycopg.connect(db) as conn:
        conn.execute("SET lock_timeout = '3s'")
        conn.execute("SELECT id FROM logs WHERE id = %s FOR UPDATE", (log_id,))
        conn.execute("UPDATE logs SET description = 'x' WHERE id = %s", (log_id,))
        conn.rollback()


def test_rejected_edits_release_the_lock(env):
    client, db, uploads = env
    log = make_log(client, 2)
    bad_remove = put(client, log["id"], remove=["/uploads/nope.png"])
    assert bad_remove.status_code == 422
    _assert_lock_free(db, log["id"])
    bad_count = put(client, log["id"], remove=log["photos"])
    assert bad_count.status_code == 422
    assert bad_count.json()["detail"] == "a log needs between 1 and 5 photos"
    _assert_lock_free(db, log["id"])
    assert put(client, log["id"]).status_code == 200
    _assert_lock_free(db, log["id"])
