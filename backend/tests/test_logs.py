"""Tests for creating, listing, updating and deleting log entries."""
from datetime import datetime
from pathlib import Path

import pytest

from conftest import make_image, make_log, post, put, execute_sql, rows, snapshot


SHAPE = {"id", "description", "photos", "created_at", "updated_at"}


def test_create_ok_response_and_storage(env):
    client, db, uploads = env
    r = post(client, [make_image("PNG")], description="  hello  ")
    assert r.status_code == 201
    body = r.json()
    assert set(body) == {"id", "description", "photos", "created_at", "updated_at"}
    assert body["description"] == "hello"
    assert body["created_at"] == body["updated_at"]
    assert len(body["photos"]) == 1
    assert (uploads / Path(body["photos"][0]).name).is_file()
    assert body["photos"][0].startswith("uploads/")
    logs, photos = rows(db)
    assert len(logs) == 1 and len(photos) == 1
    assert logs[0]["description"] == "hello" and logs[0]["created_at"] == logs[0]["updated_at"]
    assert logs[0]["created_at"] == datetime.fromisoformat(body["created_at"])
    assert photos[0]["path"] == body["photos"][0]


def test_list_empty(env):
    client, db, uploads = env
    r = client.get("/api/logs")
    assert r.status_code == 200 and r.json() == []


def test_list_order_shape_and_photos(env):
    client, db, uploads = env
    created = [post(client, [make_image() for _ in range(n)], description=d).json()
               for n, d in [(1, "A"), (3, "B"), (2, "C")]]
    r = client.get("/api/logs")
    assert r.status_code == 200
    body = r.json()
    assert [x["id"] for x in body] == [c["id"] for c in reversed(created)]
    stamps = [x["created_at"] for x in body]
    assert stamps == sorted(stamps, reverse=True)
    by_id = {c["id"]: c for c in created}
    for item in body:
        assert set(item) == SHAPE
        assert item == by_id[item["id"]]  # same as POST, photos in upload order
    assert [len(x["photos"]) for x in body] == [2, 3, 1]


def test_put_description_only(env):
    client, db, uploads = env
    log = make_log(client, 2)
    r = put(client, log["id"], description="  new text  ")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == SHAPE
    assert body["description"] == "new text" and body["photos"] == log["photos"]
    assert body["created_at"] == log["created_at"]
    assert body["updated_at"] > log["updated_at"]
    assert body["updated_at"].endswith("+00:00") and len(body["updated_at"]) == len(log["updated_at"])
    assert client.get("/api/logs").json() == [body]
    assert len(list(uploads.iterdir())) == 2


def test_put_unknown_id_404_writes_nothing(env):
    client, db, uploads = env
    log = make_log(client, 1)
    before = snapshot(db, uploads)
    assert put(client, log["id"] + 99, add=[make_image()]).status_code == 404
    assert snapshot(db, uploads) == before


def test_put_does_not_touch_other_log(env):
    client, db, uploads = env
    a = make_log(client, 1)
    b = make_log(client, 2, description="other")
    put(client, a["id"], add=[make_image()])
    assert {x["id"]: x for x in client.get("/api/logs").json()}[b["id"]] == b


# ---- DELETE /api/logs/{id} ----
# Choices: success is 204 (no body); a non-integer id is 422 (FastAPI default).

def file_bytes(uploads):
    return {p.name: p.read_bytes() for p in uploads.iterdir()}


def test_delete_removes_rows_files_and_listing(env):
    client, db, uploads = env
    log = make_log(client, 3)
    r = client.delete(f"/api/logs/{log['id']}")
    assert r.status_code == 204 and r.content == b""
    assert client.get("/api/logs").json() == []
    assert rows(db) == ([], [])
    for p in log["photos"]:
        assert not (uploads / Path(p).name).exists()
    assert list(uploads.iterdir()) == []


def test_delete_leaves_other_log_untouched(env):
    client, db, uploads = env
    a = make_log(client, 2)
    b = make_log(client, 2, description="other")
    other_files = {Path(p).name: (uploads / Path(p).name).read_bytes() for p in b["photos"]}
    logs_b = [x for x in rows(db)[0] if x["id"] == b["id"]]
    photos_b = [x for x in rows(db)[1] if x["log_id"] == b["id"]]
    assert client.delete(f"/api/logs/{a['id']}").status_code == 204
    assert client.get("/api/logs").json() == [b]
    assert file_bytes(uploads) == other_files
    assert rows(db) == (logs_b, photos_b)


def test_delete_unknown_id_404_unchanged(env):
    client, db, uploads = env
    log = make_log(client, 2)
    before = snapshot(db, uploads)
    r = client.delete(f"/api/logs/{log['id'] + 99}")
    assert r.status_code == 404 and r.json()["detail"]
    assert snapshot(db, uploads) == before


@pytest.mark.parametrize("bad", ["abc", "1.5", "-x"])
def test_delete_non_integer_id_422_unchanged(env, bad):
    client, db, uploads = env
    make_log(client, 2)
    before = snapshot(db, uploads)
    assert client.delete(f"/api/logs/{bad}").status_code == 422
    assert snapshot(db, uploads) == before


def test_delete_with_missing_files_ok(env):
    client, db, uploads = env
    log = make_log(client, 3)
    (uploads / Path(log["photos"][0]).name).unlink()
    assert client.delete(f"/api/logs/{log['id']}").status_code == 204
    assert rows(db) == ([], [])
    assert list(uploads.iterdir()) == []


def test_delete_file_removal_error_still_success(env, monkeypatch):
    client, db, uploads = env
    log = make_log(client, 2)

    def boom(*a, **k):
        raise OSError("locked")

    monkeypatch.setattr("os.remove", boom)
    r = client.delete(f"/api/logs/{log['id']}")
    monkeypatch.undo()
    assert r.status_code == 204
    assert client.get("/api/logs").json() == []
    assert rows(db) == ([], [])


def test_delete_log_without_photos_and_twice(env):
    client, db, uploads = env
    log = make_log(client, 1)
    execute_sql(db, "DELETE FROM photos")
    assert client.delete(f"/api/logs/{log['id']}").status_code == 204
    assert client.delete(f"/api/logs/{log['id']}").status_code == 404
    assert rows(db) == ([], [])


def test_delete_never_removes_outside_uploads(env, tmp_path):
    client, db, uploads = env
    log = make_log(client, 1)
    victim = tmp_path / "victim.txt"
    victim.write_text("keep")
    execute_sql(db, "UPDATE photos SET path = %s", ("../victim.txt",))
    assert client.delete(f"/api/logs/{log['id']}").status_code == 204
    assert victim.read_text() == "keep"
