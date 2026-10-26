"""Tests for GET /api/logs: default and custom limit, clamping, 422, ordering, photos."""
import pytest

from conftest import execute_sql, make_image, post
from models import DEFAULT_LIST_LIMIT, MAX_LIST_LIMIT


def _create(client, n, photos=1):
    return [post(client, [make_image() for _ in range(photos)]).json() for _ in range(n)]


def _ids(client, **params):
    r = client.get("/api/logs", params=params)
    assert r.status_code == 200
    return [x["id"] for x in r.json()]


def test_constants():
    assert (DEFAULT_LIST_LIMIT, MAX_LIST_LIMIT) == (5, 20)


@pytest.mark.parametrize("stored,expected", [(0, 0), (1, 1), (3, 3), (5, 5), (8, 5)])
def test_default_limit(env, stored, expected):
    client, _, _ = env
    _create(client, stored)
    r = client.get("/api/logs")
    assert r.status_code == 200 and len(r.json()) == expected


def test_default_equals_explicit_five(env):
    client, _, _ = env
    _create(client, 8)
    assert client.get("/api/logs").json() == client.get("/api/logs", params={"limit": 5}).json()


@pytest.mark.parametrize("limit,expected", [(1, 1), (2, 2), (8, 8), (20, 8)])
def test_custom_limit(env, limit, expected):
    client, _, _ = env
    _create(client, 8)
    assert len(_ids(client, limit=limit)) == expected


@pytest.mark.parametrize("limit", [20, 21, 100, 10**12])
def test_over_max_clamps_to_20(env, limit):
    client, _, _ = env
    _create(client, 25)
    assert len(_ids(client, limit=limit)) == 20


@pytest.mark.parametrize("limit", ["0", "-1", "abc", "", "2.5"])
def test_invalid_limit_is_422(env, limit):
    client, _, _ = env
    _create(client, 2)
    r = client.get("/api/logs", params={"limit": limit})
    assert r.status_code == 422
    assert "detail" in r.json()


def test_newest_first_cut_in_id_order(env):
    client, _, _ = env
    ids = [x["id"] for x in _create(client, 8)]
    assert _ids(client, limit=3) == ids[::-1][:3]
    assert _ids(client) == ids[::-1][:5]


def test_newest_by_timestamp_not_id(env):
    client, db, _ = env
    ids = [x["id"] for x in _create(client, 8)]
    # The two lowest ids get the newest timestamps; they must survive the cut.
    execute_sql(db, "UPDATE logs SET created_at = '2030-01-01T00:00:00.000000+00:00' "
                    "WHERE id = %s", (ids[0],))
    execute_sql(db, "UPDATE logs SET created_at = '2029-01-01T00:00:00.000000+00:00' "
                    "WHERE id = %s", (ids[1],))
    assert _ids(client, limit=4) == [ids[0], ids[1], ids[7], ids[6]]


def test_tie_break_decides_cut(env):
    client, db, _ = env
    ids = [x["id"] for x in _create(client, 8)]
    execute_sql(db, "UPDATE logs SET created_at = '2026-01-01T00:00:00.000000+00:00'")
    assert _ids(client, limit=3) == sorted(ids, reverse=True)[:3]


def test_photos_belong_to_their_logs(env):
    client, db, _ = env
    created = [post(client, [make_image() for _ in range(n)]).json()
               for n in (1, 2, 3, 4, 5, 2, 1)]
    # Photo ids out of position order must still list by position.
    execute_sql(db, "UPDATE photos SET id = id + 1000 WHERE log_id = %s", (created[4]["id"],))
    listed = client.get("/api/logs", params={"limit": 4}).json()
    expected = created[::-1][:4]
    assert listed == expected
    returned = {x["id"] for x in listed}
    all_paths = {p for c in created if c["id"] not in returned for p in c["photos"]}
    assert not all_paths & {p for x in listed for p in x["photos"]}


def test_response_shape(env):
    client, _, _ = env
    _create(client, 2)
    body = client.get("/api/logs").json()
    assert isinstance(body, list)
    for x in body:
        assert set(x) == {"id", "description", "photos", "created_at", "updated_at"}
