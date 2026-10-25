"""Tests for description, format, size and other invalid-data rules."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import models
from conftest import assert_nothing_stored, execute_sql, make_image, make_log, post, put, snapshot
from main import create_app


MAX = models.MAX_PHOTO_BYTES


def padded_png(total):
    data = make_image("PNG")
    return data + b"\0" * (total - len(data))


TOO_LONG = "description must be at most 200 characters"


@pytest.mark.parametrize("desc", [None, "", "   ", "\t\n "])
def test_bad_description_422(env, desc):
    client, db, uploads = env
    assert post(client, [make_image()], description=desc).status_code == 422
    assert_nothing_stored(db, uploads)


def test_description_sent_as_file_422(env):
    client, db, uploads = env
    files = [("description", ("d.txt", b"hi", "text/plain")),
             ("photos", ("p.png", make_image(), "image/png"))]
    assert client.post("/api/logs", files=files).status_code == 422
    assert_nothing_stored(db, uploads)


def test_zero_photos_422(env):
    client, db, uploads = env
    assert post(client, []).status_code == 422
    assert_nothing_stored(db, uploads)


def test_photos_as_text_value_422(env):
    client, db, uploads = env
    r = client.post("/api/logs", data={"description": "x", "photos": "notafile"})
    assert r.status_code == 422
    assert_nothing_stored(db, uploads)


@pytest.mark.parametrize("n", [6, 7])
def test_too_many_photos_422(env, n):
    client, db, uploads = env
    assert post(client, [make_image() for _ in range(n)]).status_code == 422
    assert_nothing_stored(db, uploads)


@pytest.mark.parametrize("name", ["a.gif", "a.txt", "a", "a.png.exe", "a.bmp"])
def test_bad_extension_422(env, name):
    client, db, uploads = env
    assert post(client, [make_image()], name=name).status_code == 422
    assert_nothing_stored(db, uploads)


@pytest.mark.parametrize("name,fmt", [("A.JPG", "JPEG"), ("a.jpeg", "JPEG"),
                                      ("a.PnG", "PNG"), ("a.webp", "WEBP")])
def test_allowed_extensions_ok(env, name, fmt):
    client, db, uploads = env
    r = post(client, [make_image(fmt)], name=name)
    assert r.status_code == 201
    assert Path(r.json()["photos"][0]).suffix in {".jpg", ".png", ".webp"}


def test_text_content_422(env):
    client, db, uploads = env
    assert post(client, [b"not an image at all"], name="a.png").status_code == 422
    assert_nothing_stored(db, uploads)


def test_truncated_image_422(env):
    client, db, uploads = env
    data = make_image("PNG", size=(64, 64))
    assert post(client, [data[: len(data) // 2]]).status_code == 422
    assert_nothing_stored(db, uploads)


def test_disallowed_real_format_422(env):
    client, db, uploads = env
    assert post(client, [make_image("GIF")], name="a.png").status_code == 422
    assert post(client, [make_image("BMP")], name="a.jpg").status_code == 422
    assert_nothing_stored(db, uploads)


def test_empty_file_and_empty_filename_422(env):
    client, db, uploads = env
    assert post(client, [b""]).status_code == 422
    assert post(client, [make_image()], name="").status_code == 422
    assert_nothing_stored(db, uploads)


def test_exact_5mib_ok_and_one_more_413(env):
    client, db, uploads = env
    assert post(client, [padded_png(MAX)]).status_code == 201
    for p in uploads.iterdir():
        p.unlink()
    execute_sql(db, "DELETE FROM photos")
    execute_sql(db, "DELETE FROM logs")
    assert post(client, [padded_png(MAX + 1)]).status_code == 413
    assert_nothing_stored(db, uploads)


def test_body_limit_413_declared(env):
    client, db, uploads = env
    # 6 files under the per-photo cap but total over the request limit.
    big = [padded_png(MAX) for _ in range(5)]
    body_over = models.MAX_REQUEST_BYTES + 1
    r = client.post("/api/logs", data={"description": "x"},
                    files=[("photos", ("p.png", d, "image/png")) for d in big] +
                    [("extra", ("e.bin", b"\0" * (body_over - 5 * MAX), "x/y"))])
    assert r.status_code == 413
    assert_nothing_stored(db, uploads)


def test_body_limit_413_streamed_without_content_length(tmp_path, test_url):
    uploads = tmp_path / "up"
    app = create_app(database_url=test_url, uploads_dir=uploads, max_request_bytes=2000)

    def gen():
        yield b"--b\r\n"
        for _ in range(10):
            yield b"x" * 1000

    with TestClient(app) as client:
        r = client.post("/api/logs", content=gen(),
                        headers={"content-type": "multipart/form-data; boundary=b"})
        assert r.status_code == 413
    assert list(uploads.iterdir()) == []


def test_precedence_422_shape_beats_413_size(env):
    client, db, uploads = env
    r = post(client, [padded_png(MAX + 1), make_image()], description="  ")
    assert r.status_code == 422
    r = post(client, [padded_png(MAX + 1), b"junk"])
    assert r.status_code == 413  # size beats content
    assert_nothing_stored(db, uploads)


def test_mixed_valid_and_invalid_leaves_nothing(env):
    client, db, uploads = env
    r = post(client, [make_image(), make_image(), b"corrupt"])
    assert r.status_code == 422
    assert_nothing_stored(db, uploads)


def test_body_limit_constant_is_large_enough():
    assert models.MAX_REQUEST_BYTES >= 5 * 5 * 1024 * 1024 + 1


@pytest.mark.parametrize("desc", [None, "", "   ", "\t\n "])
def test_put_bad_description_422_unchanged(env, desc):
    client, db, uploads = env
    log = make_log(client, 2)
    before = snapshot(db, uploads)
    assert put(client, log["id"], description=desc, add=[make_image()]).status_code == 422
    assert snapshot(db, uploads) == before


@pytest.mark.parametrize("desc,ok", [
    ("a", True), ("  a  ", True), ("x" * 200, True), ("  " + "x" * 200 + "\n ", True),
    ("x" * 201, False), ("  " + "x" * 201 + "  ", False), ("\U0001F600" * 201, False),
    ("\U0001F600" * 200, True),
])
def test_post_description_length(env, desc, ok):
    client, db, uploads = env
    r = post(client, [make_image()], description=desc)
    if ok:
        assert r.status_code == 201 and r.json()["description"] == desc.strip()
    else:
        assert r.status_code == 422 and r.json()["detail"] == TOO_LONG
        assert_nothing_stored(db, uploads)


@pytest.mark.parametrize("desc,ok", [
    ("a", True), ("  a  ", True), ("x" * 200, True), ("  " + "x" * 200 + "\n ", True),
    ("x" * 201, False), ("  " + "x" * 201 + "  ", False), ("\U0001F600" * 201, False),
    ("\U0001F600" * 200, True),
])
def test_put_description_length(env, desc, ok):
    client, db, uploads = env
    log = make_log(client, 2)
    before = snapshot(db, uploads)
    r = put(client, log["id"], description=desc)
    if ok:
        assert r.status_code == 200 and r.json()["description"] == desc.strip()
    else:
        assert r.status_code == 422 and r.json()["detail"] == TOO_LONG
        assert snapshot(db, uploads) == before
        listed = client.get("/api/logs").json()
        assert listed == [log]


def test_blank_description_message_unchanged(env):
    client, _, _ = env
    for r in (post(client, [make_image()], description="   "),
              post(client, [make_image()], description=None)):
        assert r.status_code == 422
        assert r.json()["detail"] == "description is required and cannot be blank"


def test_max_description_constant():
    assert models.MAX_DESCRIPTION_CHARS == 200


def test_put_remove_all_422_unchanged(env):
    client, db, uploads = env
    log = make_log(client, 2)
    before = snapshot(db, uploads)
    assert put(client, log["id"], remove=log["photos"]).status_code == 422
    assert snapshot(db, uploads) == before


def test_put_over_five_422_unchanged(env):
    client, db, uploads = env
    log = make_log(client, 5)
    log2 = make_log(client, 2)
    before = snapshot(db, uploads)
    assert put(client, log["id"], add=[make_image()]).status_code == 422
    assert put(client, log2["id"], add=[make_image() for _ in range(6)]).status_code == 422
    assert put(client, log2["id"], add=[make_image() for _ in range(4)]).status_code == 422
    assert snapshot(db, uploads) == before


@pytest.mark.parametrize("name,kind", [
    ("a.gif", "png"), ("a.txt", "png"), ("a.png", "text"), ("a.png", "empty"),
    ("a.png", "gif")])
def test_put_invalid_new_file_rejects_whole_request(env, name, kind):
    client, db, uploads = env
    log = make_log(client, 1)
    before = snapshot(db, uploads)
    bad = {"png": make_image(), "text": b"not an image", "empty": b"",
           "gif": make_image("GIF")}[kind]
    r = client.put(f"/api/logs/{log['id']}", data={"description": "x"},
                   files=[("photos", ("ok.png", make_image(), "image/png")),
                          ("photos", (name, bad, "image/png"))])
    assert r.status_code == 422
    assert snapshot(db, uploads) == before


def test_put_5mib_boundary(env):
    client, db, uploads = env
    log = make_log(client, 1)
    assert put(client, log["id"], add=[padded_png(MAX)]).status_code == 200
    before = snapshot(db, uploads)
    assert put(client, log["id"], add=[padded_png(MAX + 1)]).status_code == 413
    assert snapshot(db, uploads) == before


def test_put_body_limit_413(tmp_path, test_url):
    uploads = tmp_path / "up"
    db = test_url
    app = create_app(database_url=test_url, uploads_dir=uploads, max_request_bytes=5000)
    with TestClient(app) as client:
        log = post(client, [make_image()]).json()
        before = snapshot(db, uploads)
        r = client.put(f"/api/logs/{log['id']}", data={"description": "x"},
                       files=[("photos", ("p.png", padded_png(6000), "image/png"))])
        assert r.status_code == 413
        assert snapshot(db, uploads) == before


@pytest.mark.parametrize("bad", ["uploads/nope.png", "../x.png", "/etc/passwd",
                                 "uploads/../../x.png", "", "C:\\x.png"])
def test_put_remove_foreign_or_malformed_422(env, bad):
    client, db, uploads = env
    log = make_log(client, 2)
    before = snapshot(db, uploads)
    assert put(client, log["id"], remove=[bad], add=[make_image()]).status_code == 422
    assert snapshot(db, uploads) == before


def test_put_remove_other_logs_photo_422_other_untouched(env):
    client, db, uploads = env
    a = make_log(client, 2)
    b = make_log(client, 2)
    before = snapshot(db, uploads)
    r = put(client, a["id"], remove=[b["photos"][0]], add=[make_image()])
    assert r.status_code == 422
    assert snapshot(db, uploads) == before
    assert (uploads / Path(b["photos"][0]).name).is_file()


def test_put_remove_as_file_part_422(env):
    client, db, uploads = env
    log = make_log(client, 2)
    before = snapshot(db, uploads)
    r = client.put(f"/api/logs/{log['id']}", data={"description": "x"},
                   files=[("remove_photos", ("r.txt", b"x", "text/plain"))])
    assert r.status_code == 422
    assert snapshot(db, uploads) == before
