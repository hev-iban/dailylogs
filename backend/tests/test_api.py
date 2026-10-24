"""End-to-end workflow tests that use only the public HTTP API."""
from fastapi.testclient import TestClient

from conftest import make_image, post, put
from main import create_app


def test_lifecycle_create_list_edit_list_delete_list(env):
    client, db, uploads = env
    r = post(client, [make_image()], description="first")
    assert r.status_code == 201
    created = r.json()
    listed = client.get("/api/logs")
    assert listed.status_code == 200 and listed.json() == [created]
    r = put(client, created["id"], description="second")
    assert r.status_code == 200
    edited = r.json()
    assert edited["description"] == "second" and edited["photos"] == created["photos"]
    listed = client.get("/api/logs")
    assert listed.status_code == 200 and listed.json() == [edited]
    assert client.delete(f"/api/logs/{created['id']}").status_code == 204
    listed = client.get("/api/logs")
    assert listed.status_code == 200 and listed.json() == []


def test_log_and_photo_survive_app_restart(tmp_path):
    db, uploads = tmp_path / "t.db", tmp_path / "up"
    data = make_image()
    with TestClient(create_app(db_path=db, uploads_dir=uploads)) as client:
        created = post(client, [data], description="kept").json()
        before = client.get("/api/logs").json()
    with TestClient(create_app(db_path=db, uploads_dir=uploads)) as client:
        assert client.get("/api/logs").json() == before == [created]
        r = client.get("/" + created["photos"][0])
        assert r.status_code == 200 and r.content == data
