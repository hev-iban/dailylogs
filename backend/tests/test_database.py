"""Tests for PostgreSQL rows, ordering, rollback, server-set timestamps and the real-path check."""

import psycopg
import pytest
from fastapi.testclient import TestClient

import database
from main import create_app
from conftest import (
    check_test_url,
    _REAL_BEFORE,
    _real_state,
    assert_nothing_stored,
    execute_sql,
    make_image,
    make_log,
    post,
    put,
    snapshot,
)


def test_db_error_cleans_up_500(env, monkeypatch):
    client, db, uploads = env

    def boom(*a, **k):
        raise psycopg.OperationalError("db down")

    monkeypatch.setattr(database, "insert_log", boom)
    r = post(client, [make_image(), make_image()])
    assert r.status_code == 500
    assert_nothing_stored(db, uploads)


def test_db_failure_rolls_back_row(env, monkeypatch):
    client, db, uploads = env
    real = database.insert_log

    def insert_then_fail(conn, *a, **k):
        real(conn, *a, **k)
        raise psycopg.OperationalError("after insert")

    monkeypatch.setattr(database, "insert_log", insert_then_fail)
    assert post(client, [make_image()]).status_code == 500
    assert_nothing_stored(db, uploads)


def test_list_tie_break_higher_id_first(env):
    client, db, uploads = env
    ids = [post(client, [make_image()]).json()["id"] for _ in range(3)]
    execute_sql(db, "UPDATE logs SET created_at = '2026-01-01T00:00:00.000000+00:00'")
    assert [x["id"] for x in client.get("/api/logs").json()] == sorted(ids, reverse=True)


def test_list_orders_by_timestamp_not_id(env):
    client, db, uploads = env
    a = post(client, [make_image()]).json()["id"]
    b = post(client, [make_image()]).json()["id"]
    execute_sql(db, "UPDATE logs SET created_at = '2030-01-01T00:00:00.000000+00:00' WHERE id = %s", (a,))
    assert [x["id"] for x in client.get("/api/logs").json()] == [a, b]


def test_list_photos_order_by_position(env):
    client, db, uploads = env
    created = post(client, [make_image() for _ in range(3)]).json()
    other = post(client, [make_image()]).json()
    execute_sql(db, "UPDATE photos SET id = id + 100 WHERE log_id = %s", (created["id"],))
    by_id = {x["id"]: x for x in client.get("/api/logs").json()}
    assert by_id[created["id"]]["photos"] == created["photos"]
    assert by_id[other["id"]]["photos"] == other["photos"]


def test_client_created_at_ignored(env):
    client, db, uploads = env
    fake = "1999-01-01T00:00:00+00:00"
    files = [("photos", ("p.png", make_image(), "image/png")),
             ("created_at", ("c.txt", fake.encode(), "text/plain"))]
    r1 = client.post("/api/logs", data={"description": "x", "created_at": fake,
                                    "updated_at": fake}, files=files,
                     params={"created_at": fake})
    r2 = post(client, [make_image()])
    assert r1.status_code == 201 and r2.status_code == 201
    for r in (r1, r2):
        b = r.json()
        assert b["created_at"] != fake and b["updated_at"] != fake
        assert b["created_at"].startswith("20") and b["created_at"].endswith("+00:00")
    listed = client.get("/api/logs").json()
    assert all(not x["created_at"].startswith("1999") for x in listed)
    assert [x["id"] for x in listed] == [r2.json()["id"], r1.json()["id"]]


def test_real_paths_untouched():
    # Mid-run check; the session guard above repeats it after the last test.
    assert _real_state() == _REAL_BEFORE


def test_put_db_error_500_cleans_up_new_files_keeps_old(env, monkeypatch):
    client, db, uploads = env
    log = make_log(client, 2)
    before = snapshot(db, uploads)
    real = database.update_log

    def update_then_fail(conn, *a, **k):
        real(conn, *a, **k)
        raise psycopg.OperationalError("after update")

    monkeypatch.setattr(database, "update_log", update_then_fail)
    r = put(client, log["id"], description="changed", remove=[log["photos"][0]],
            add=[make_image(), make_image()])
    assert r.status_code == 500
    assert snapshot(db, uploads) == before


def test_delete_db_error_500_nothing_deleted(env, monkeypatch):
    client, db, uploads = env
    log = make_log(client, 2)
    before = snapshot(db, uploads)
    real = database.delete_log

    def delete_then_fail(conn, *a, **k):
        real(conn, *a, **k)
        raise psycopg.OperationalError("after delete")

    monkeypatch.setattr(database, "delete_log", delete_then_fail)
    assert client.delete(f"/api/logs/{log['id']}").status_code == 500
    monkeypatch.undo()
    assert snapshot(db, uploads) == before
    assert client.get("/api/logs").json() == [log]


def test_startup_without_database_url_fails_fast(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL") as exc:
        with TestClient(create_app(uploads_dir=tmp_path / "up")):
            pass
    assert "postgresql://postgres@localhost:5432/dailylog" in str(exc.value)


def test_blank_database_url_fails_fast(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "   ")
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        with TestClient(create_app(uploads_dir=tmp_path / "up")):
            pass


def test_create_app_without_database_url_does_not_raise(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    create_app(uploads_dir=tmp_path / "up")


def test_check_test_url_rules():
    ok = "postgresql://postgres@localhost:5432/dailylog_test"
    assert check_test_url(ok, None) == ok
    assert check_test_url(ok + "?connect_timeout=5", "postgresql://x/dailylog") is not None
    for test_url, db_url in [
        (ok, ok),
        (ok, "  " + ok + " "),
        ("postgresql://postgres@localhost:5432/dailylog", None),
        ("postgresql://postgres@localhost:5432/dailylog?x=_test", None),
        ("", None),
        ("   ", None),
        (None, None),
    ]:
        with pytest.raises(pytest.UsageError):
            check_test_url(test_url, db_url)
