"""Tests for status codes, content types and the frontend/static routes."""
import pytest

import models
from conftest import make_image, post


def test_index_served_at_root(env):
    client, db, uploads = env
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert r.content == (models.FRONTEND_DIR / "index.html").read_bytes()
    assert b'href="/static/style.css"' in r.content
    assert b'src="/static/app.js"' in r.content


@pytest.mark.parametrize("path", ["/static/style.css", "/static/app.js"])
def test_static_assets_served(env, path):
    client, db, uploads = env
    r = client.get(path)
    assert r.status_code == 200
    assert r.content == (models.FRONTEND_DIR / path.rsplit("/", 1)[1]).read_bytes()


def test_static_missing_404(env):
    client, db, uploads = env
    assert client.get("/static/missing.txt").status_code == 404


def test_old_logs_paths_gone(env):
    client, db, uploads = env
    assert client.get("/logs").status_code == 404
    assert post_old(client).status_code == 404


def post_old(client):
    files = [("photos", ("p.png", make_image(), "image/png"))]
    return client.post("/logs", data={"description": "x"}, files=files)


def test_uploads_missing_file_404(env):
    client, db, uploads = env
    assert client.get("/uploads/nope.png").status_code == 404


def test_uploads_dir_listing_not_exposed(env):
    client, db, uploads = env
    post(client, [make_image()])
    for path in ("/uploads/", "/uploads"):
        r = client.get(path, follow_redirects=False)
        assert r.status_code != 200
