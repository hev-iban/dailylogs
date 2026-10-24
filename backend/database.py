"""SQLite connection and schema."""
import sqlite3
from contextlib import closing
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_id INTEGER NOT NULL REFERENCES logs(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    position INTEGER NOT NULL
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path) -> None:
    with closing(connect(db_path)) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def list_logs(conn: sqlite3.Connection) -> list[dict]:
    """All logs, newest first (ties: higher id first), photos in upload order."""
    logs = conn.execute(
        "SELECT id, description, created_at, updated_at FROM logs "
        "ORDER BY created_at DESC, id DESC"
    ).fetchall()
    photos: dict[int, list[str]] = {}
    for row in conn.execute("SELECT log_id, path FROM photos ORDER BY position, id"):
        photos.setdefault(row["log_id"], []).append(row["path"])
    return [
        {
            "id": r["id"],
            "description": r["description"],
            "photos": photos.get(r["id"], []),
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }
        for r in logs
    ]


def insert_log(conn: sqlite3.Connection, description: str,
               photo_paths: list[str], now: str) -> dict:
    """Insert a log and its photos. Does not commit; the caller owns the transaction."""
    cur = conn.execute(
        "INSERT INTO logs (description, created_at, updated_at) VALUES (?, ?, ?)",
        (description, now, now),
    )
    log_id = cur.lastrowid
    conn.executemany(
        "INSERT INTO photos (log_id, path, position) VALUES (?, ?, ?)",
        [(log_id, p, i) for i, p in enumerate(photo_paths)],
    )
    return {
        "id": log_id,
        "description": description,
        "photos": list(photo_paths),
        "created_at": now,
        "updated_at": now,
    }


def get_log(conn: sqlite3.Connection, log_id: int) -> dict | None:
    """One log in the list_logs shape, or None if the id is unknown."""
    row = conn.execute(
        "SELECT id, description, created_at, updated_at FROM logs WHERE id = ?",
        (log_id,),
    ).fetchone()
    if row is None:
        return None
    paths = [r["path"] for r in conn.execute(
        "SELECT path FROM photos WHERE log_id = ? ORDER BY position, id", (log_id,))]
    return {
        "id": row["id"],
        "description": row["description"],
        "photos": paths,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def delete_log(conn: sqlite3.Connection, log_id: int) -> list[str] | None:
    """Delete a log; its photo rows go with it (ON DELETE CASCADE).

    Returns the deleted photo paths in upload order, or None if the id is unknown.
    Does not commit; the caller owns the transaction.
    """
    paths = [r["path"] for r in conn.execute(
        "SELECT path FROM photos WHERE log_id = ? ORDER BY position, id", (log_id,))]
    cur = conn.execute("DELETE FROM logs WHERE id = ?", (log_id,))
    if cur.rowcount == 0:
        return None
    return paths


def update_log(conn: sqlite3.Connection, log_id: int, description: str,
               photo_paths: list[str], now: str) -> dict | None:
    """Set description/updated_at and replace the photo rows with photo_paths, in order.

    Does not commit; the caller owns the transaction. None if the id is unknown.
    """
    cur = conn.execute(
        "UPDATE logs SET description = ?, updated_at = ? WHERE id = ?",
        (description, now, log_id),
    )
    if cur.rowcount == 0:
        return None
    conn.execute("DELETE FROM photos WHERE log_id = ?", (log_id,))
    conn.executemany(
        "INSERT INTO photos (log_id, path, position) VALUES (?, ?, ?)",
        [(log_id, p, i) for i, p in enumerate(photo_paths)],
    )
    return get_log(conn, log_id)
