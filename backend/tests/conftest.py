"""Shared pytest setup: import path, the temp-app fixture, test helpers and the real-path guard."""
import io
import sqlite3
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

import models  # noqa: E402
from main import create_app  # noqa: E402


def make_image(fmt="PNG", size=(8, 8)):
    buf = io.BytesIO()
    Image.new("RGB", size, (200, 30, 30)).save(buf, fmt)
    return buf.getvalue()


@pytest.fixture
def env(tmp_path):
    uploads = tmp_path / "up"
    db = tmp_path / "t.db"
    app = create_app(db_path=db, uploads_dir=uploads)
    with TestClient(app) as client:
        yield client, db, uploads


def rows(db):
    conn = sqlite3.connect(db)
    try:
        logs = conn.execute("SELECT * FROM logs").fetchall()
        photos = conn.execute("SELECT * FROM photos").fetchall()
    finally:
        conn.close()
    return logs, photos


def assert_nothing_stored(db, uploads):
    logs, photos = rows(db)
    assert logs == [] and photos == []
    assert list(uploads.iterdir()) == []


def post(client, photos, description="a log", name="p.png", ctype="image/png"):
    files = [("photos", (name, d, ctype)) for d in photos]
    data = {} if description is None else {"description": description}
    return client.post("/api/logs", data=data, files=files or None)


def put(client, log_id, description="edited", add=(), remove=(), name="n.png"):
    data = {"remove_photos": list(remove)}
    if description is not None:
        data["description"] = description
    files = [("photos", (name, d, "image/png")) for d in add]
    return client.put(f"/api/logs/{log_id}", data=data, files=files or None)


def snapshot(db, uploads):
    return rows(db), sorted(p.name for p in uploads.iterdir())


def make_log(client, n=3, description="orig"):
    return post(client, [make_image() for _ in range(n)], description=description).json()


def _real_state():
    """Metadata only (name, size, mtime_ns) of the real logs.db and uploads/; never reads contents."""
    def stat(p):
        s = p.stat()
        return (s.st_size, s.st_mtime_ns)

    db = models.DEFAULT_DB_PATH
    up = models.DEFAULT_UPLOADS_DIR
    return {
        "db": stat(db) if db.exists() else None,
        "uploads": (
            {c.name: stat(c) for c in up.iterdir()} if up.is_dir() else None
        ),
    }


_REAL_BEFORE = _real_state()


@pytest.fixture(scope="session", autouse=True)
def _real_paths_guard():
    yield
    assert _real_state() == _REAL_BEFORE, "test suite modified real logs.db or uploads/"
