"""Shared pytest setup: import path, the test-database fixtures, helpers and the uploads guard."""
import io
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg  # noqa: E402
import pytest  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

import database  # noqa: E402
import models  # noqa: E402
from main import create_app  # noqa: E402

EXAMPLE_TEST_URL = "postgresql://postgres@localhost:5432/dailylog_test"


def check_test_url(test_url, database_url):
    """Refuse a missing TEST_DATABASE_URL, one equal to DATABASE_URL, or a name not ending _test.

    Pure string logic; never connects.
    """
    test_url = (test_url or "").strip()
    if not test_url:
        raise pytest.UsageError(
            "TEST_DATABASE_URL is not set. Set it to a throwaway PostgreSQL database "
            f"whose name ends in _test, e.g. {EXAMPLE_TEST_URL}")
    if database_url is not None and test_url == database_url.strip():
        raise pytest.UsageError("TEST_DATABASE_URL must not equal DATABASE_URL")
    name = urlsplit(test_url).path.lstrip("/")
    if not name.endswith("_test"):
        raise pytest.UsageError(
            f"TEST_DATABASE_URL database name {name!r} must end in _test "
            "(the tests wipe it)")
    return test_url


# Checked at import, before any connection is opened.
TEST_DATABASE_URL = check_test_url(
    os.environ.get("TEST_DATABASE_URL"), os.environ.get("DATABASE_URL"))


@pytest.fixture
def test_url():
    return TEST_DATABASE_URL


def execute_sql(db, sql, params=()):
    """Run one statement on a short connection, commit, close."""
    with psycopg.connect(db) as conn:
        conn.execute(sql, params)
        conn.commit()


@pytest.fixture(autouse=True)
def _clean_db():
    database.init_db(TEST_DATABASE_URL)
    execute_sql(TEST_DATABASE_URL, "TRUNCATE logs, photos RESTART IDENTITY CASCADE")


def make_image(fmt="PNG", size=(8, 8)):
    buf = io.BytesIO()
    Image.new("RGB", size, (200, 30, 30)).save(buf, fmt)
    return buf.getvalue()


@pytest.fixture
def env(tmp_path):
    uploads = tmp_path / "up"
    app = create_app(database_url=TEST_DATABASE_URL, uploads_dir=uploads)
    with TestClient(app) as client:
        yield client, TEST_DATABASE_URL, uploads


def rows(db):
    with psycopg.connect(db, row_factory=dict_row) as conn:
        logs = conn.execute("SELECT * FROM logs ORDER BY id").fetchall()
        photos = conn.execute("SELECT * FROM photos ORDER BY id").fetchall()
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
    """Metadata only (name, size, mtime_ns) of the real uploads/; never reads contents."""
    def stat(p):
        s = p.stat()
        return (s.st_size, s.st_mtime_ns)

    up = models.DEFAULT_UPLOADS_DIR
    return {
        "uploads": (
            {c.name: stat(c) for c in up.iterdir()} if up.is_dir() else None
        ),
    }


_REAL_BEFORE = _real_state()


@pytest.fixture(scope="session", autouse=True)
def _real_paths_guard():
    yield
    assert _real_state() == _REAL_BEFORE, "test suite modified the real uploads/"
