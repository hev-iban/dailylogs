"""Tests for photo uploads, stored paths, serving and multi-photo handling."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conftest import assert_nothing_stored, make_image, make_log, post, put, rows, snapshot
from main import create_app


@pytest.mark.parametrize("n", [1, 5])
def test_photo_count_boundaries_ok(env, n):
    client, db, uploads = env
    r = post(client, [make_image() for _ in range(n)])
    assert r.status_code == 201
    assert len(r.json()["photos"]) == n
    assert len(list(uploads.iterdir())) == n
    assert len(set(r.json()["photos"])) == n


def test_extension_content_mismatch_accepted_with_real_extension(env):
    # Policy: real format must be allowed; stored extension follows real format.
    client, db, uploads = env
    r = post(client, [make_image("PNG")], name="x.jpg")
    assert r.status_code == 201
    assert r.json()["photos"][0].endswith(".png")


@pytest.mark.parametrize("name", ["../../evil.png", "..\\..\\evil.png", "/etc/evil.png",
                                  "C:\\Windows\\evil.png", "C:/x/evil.png", "a/../b.png"])
def test_hostile_filenames_stay_in_uploads(env, name, tmp_path):
    client, db, uploads = env
    r = post(client, [make_image()], name=name)
    assert r.status_code == 201
    stored = Path(r.json()["photos"][0])
    assert stored.parent.as_posix() == "uploads"
    assert "evil" not in stored.name
    created = [p for p in tmp_path.rglob("*") if p.is_file() and p != db]
    assert len(created) == 1 and created[0].parent == uploads


def test_same_original_name_does_not_overwrite(env):
    client, db, uploads = env
    a = post(client, [make_image()], name="same.png").json()["photos"][0]
    b = post(client, [make_image()], name="same.png").json()["photos"][0]
    assert a != b
    assert len(list(uploads.iterdir())) == 2


def test_disk_error_midway_cleans_up_500(env, monkeypatch):
    client, db, uploads = env
    real_open = open
    calls = {"n": 0}

    def flaky_open(file, mode="r", *a, **k):
        if "b" in mode and "x" in mode:
            calls["n"] += 1
            if calls["n"] == 2:
                real_open(file, mode).close()  # leave a partial file behind
                raise OSError("disk full")
        return real_open(file, mode, *a, **k)

    monkeypatch.setattr("builtins.open", flaky_open)
    r = post(client, [make_image(), make_image(), make_image()])
    monkeypatch.undo()
    assert r.status_code == 500
    assert_nothing_stored(db, uploads)


def test_missing_uploads_dir_is_created(tmp_path):
    uploads = tmp_path / "deep" / "up"
    app = create_app(db_path=tmp_path / "t.db", uploads_dir=uploads)
    with TestClient(app) as client:
        uploads.rmdir()
        uploads.parent.rmdir()
        assert post(client, [make_image()]).status_code == 201
    assert len(list(uploads.iterdir())) == 1


def test_uploaded_photo_served(env):
    client, db, uploads = env
    data = make_image("PNG")
    photo = post(client, [data]).json()["photos"][0]
    r = client.get("/" + photo)
    assert r.status_code == 200
    assert r.content == data
    assert r.headers["content-type"].startswith("image/")


@pytest.mark.parametrize("path", [
    "/uploads/../secret.txt", "/uploads/%2e%2e/secret.txt", "/uploads/..%2fsecret.txt",
    "/uploads/%2e%2e%2fsecret.txt", "/uploads/..%5csecret.txt", "/uploads/..\\secret.txt",
    "/uploads/%2fsecret.txt", "/uploads//secret.txt", "/uploads/%5Csecret.txt",
    "/uploads/....//secret.txt"])
def test_uploads_traversal_refused(env, tmp_path, path):
    client, db, uploads = env
    (tmp_path / "secret.txt").write_text("TOPSECRET")
    r = client.get(path)
    assert 400 <= r.status_code < 500
    assert b"TOPSECRET" not in r.content


def test_uploads_absolute_path_refused(env, tmp_path):
    client, db, uploads = env
    secret = tmp_path / "secret.txt"
    secret.write_text("TOPSECRET")
    from urllib.parse import quote
    r = client.get("/uploads/" + quote(str(secret), safe=""))
    assert 400 <= r.status_code < 500
    assert b"TOPSECRET" not in r.content


def test_uploads_dir_created_late_still_served(tmp_path):
    uploads = tmp_path / "late"
    app = create_app(db_path=tmp_path / "t.db", uploads_dir=uploads)
    with TestClient(app) as client:
        data = make_image()
        photo = post(client, [data]).json()["photos"][0]
        assert client.get("/" + photo).content == data
        assert client.get("/api/logs").status_code == 200
        assert client.get("/static/app.js").status_code == 200


def test_put_remove_and_add_order_and_disk(env):
    client, db, uploads = env
    log = make_log(client, 3)
    a, b, c = log["photos"]
    r = put(client, log["id"], remove=[b], add=[make_image(), make_image("JPEG")])
    assert r.status_code == 200
    photos = r.json()["photos"]
    assert photos[:2] == [a, c] and len(photos) == 4 and len(set(photos)) == 4
    assert not (uploads / Path(b).name).exists()
    assert sorted(p.name for p in uploads.iterdir()) == sorted(Path(p).name for p in photos)
    assert photos[3].endswith(".jpg")
    assert client.get("/api/logs").json() == [r.json()]
    logs, prows = rows(db)
    assert [x[2] for x in sorted(prows, key=lambda x: x[3])] == photos


def test_put_remove_four_add_four_ok(env):
    client, db, uploads = env
    log = make_log(client, 5)
    r = put(client, log["id"], remove=log["photos"][:4], add=[make_image() for _ in range(4)])
    assert r.status_code == 200 and len(r.json()["photos"]) == 5
    assert r.json()["photos"][0] == log["photos"][4]
    assert len(list(uploads.iterdir())) == 5


def test_put_remove_all_add_new_ok(env):
    client, db, uploads = env
    log = make_log(client, 2)
    r = put(client, log["id"], remove=log["photos"], add=[make_image()])
    assert r.status_code == 200 and len(r.json()["photos"]) == 1
    assert len(list(uploads.iterdir())) == 1


def test_put_duplicate_remove_counts_once(env):
    client, db, uploads = env
    log = make_log(client, 2)
    p = log["photos"][0]
    r = put(client, log["id"], remove=[p, p])
    assert r.status_code == 200
    assert r.json()["photos"] == [log["photos"][1]]
    assert not (uploads / Path(p).name).exists()


def test_put_removed_file_already_missing_ok(env):
    client, db, uploads = env
    log = make_log(client, 2)
    (uploads / Path(log["photos"][0]).name).unlink()
    r = put(client, log["id"], remove=[log["photos"][0]])
    assert r.status_code == 200 and r.json()["photos"] == [log["photos"][1]]


def test_put_disk_error_midway_500(env, monkeypatch):
    client, db, uploads = env
    log = make_log(client, 1)
    before = snapshot(db, uploads)
    real_open = open
    calls = {"n": 0}

    def flaky_open(file, mode="r", *a, **k):
        if "b" in mode and "x" in mode:
            calls["n"] += 1
            if calls["n"] == 2:
                real_open(file, mode).close()  # leave a partial file behind
                raise OSError("disk full")
        return real_open(file, mode, *a, **k)

    monkeypatch.setattr("builtins.open", flaky_open)
    r = put(client, log["id"], remove=log["photos"], add=[make_image() for _ in range(3)])
    monkeypatch.undo()
    assert r.status_code == 500
    assert snapshot(db, uploads) == before
