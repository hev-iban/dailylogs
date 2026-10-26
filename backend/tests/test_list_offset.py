"""Tests for GET /api/logs?offset=: paging, ordering, past-the-end, 422, photos."""
import pytest

from conftest import execute_sql, make_image, post


def _create(client, n, photos=1):
    return [post(client, [make_image() for _ in range(photos)]).json() for _ in range(n)]


def _ids(client, **params):
    r = client.get("/api/logs", params=params)
    assert r.status_code == 200
    return [x["id"] for x in r.json()]


def test_pages_cover_all_logs_once(env):
    client, _, _ = env
    ids = [x["id"] for x in _create(client, 12)]
    pages = [_ids(client, limit=5, offset=o) for o in (0, 5, 10)]
    assert [len(p) for p in pages] == [5, 5, 2]
    assert pages[0] + pages[1] + pages[2] == ids[::-1]


def test_pages_with_out_of_order_and_tied_timestamps(env):
    client, db, _ = env
    ids = [x["id"] for x in _create(client, 12)]
    execute_sql(db, "UPDATE logs SET created_at = '2030-01-01T00:00:00.000000+00:00' "
                    "WHERE id = %s", (ids[0],))
    execute_sql(db, "UPDATE logs SET created_at = '2026-01-01T00:00:00.000000+00:00' "
                    "WHERE id = ANY(%s)", (ids[1:9],))
    expected = [ids[0]] + ids[9:][::-1] + sorted(ids[1:9], reverse=True)
    pages = [_ids(client, limit=5, offset=o) for o in (0, 5, 10)]
    assert pages[0] + pages[1] + pages[2] == expected
    assert len({i for p in pages for i in p}) == 12


@pytest.mark.parametrize("stored,offset", [(0, 0), (0, 3), (5, 5), (5, 6), (3, 1000000)])
def test_offset_past_end_is_empty(env, stored, offset):
    client, _, _ = env
    _create(client, stored)
    r = client.get("/api/logs", params={"offset": offset})
    assert r.status_code == 200 and r.json() == []


def test_zero_and_absent_offset_match(env):
    client, _, _ = env
    ids = [x["id"] for x in _create(client, 8)]
    assert client.get("/api/logs").json() == client.get("/api/logs", params={"offset": 0}).json()
    assert _ids(client) == ids[::-1][:5]


@pytest.mark.parametrize("offset", ["-1", "abc", "", "2.5"])
def test_invalid_offset_is_422(env, offset):
    client, _, _ = env
    _create(client, 2)
    r = client.get("/api/logs", params={"offset": offset})
    assert r.status_code == 422
    assert "detail" in r.json()


def test_huge_offset_is_never_500(env):
    client, _, _ = env
    _create(client, 2)
    r = client.get("/api/logs", params={"offset": 99999999999999999999})
    assert r.status_code in (422, 200)
    if r.status_code == 200:
        assert r.json() == []


def test_limit_rules_with_offset(env):
    client, _, _ = env
    ids = [x["id"] for x in _create(client, 30)]
    assert _ids(client, offset=5, limit=100) == ids[::-1][5:25]
    assert client.get("/api/logs", params={"offset": 1, "limit": 0}).status_code == 422
    assert client.get("/api/logs", params={"offset": 1, "limit": "x"}).status_code == 422


def test_photos_per_page(env):
    client, _, _ = env
    created = [post(client, [make_image() for _ in range(n)]).json()
               for n in (1, 2, 3, 4, 5, 2, 1)]
    newest_first = created[::-1]
    page2 = client.get("/api/logs", params={"limit": 3, "offset": 3}).json()
    assert page2 == newest_first[3:6]
    assert all(len(x["photos"]) > 0 for x in page2)


def test_response_shape_with_offset(env):
    client, _, _ = env
    _create(client, 7)
    body = client.get("/api/logs", params={"offset": 5}).json()
    assert isinstance(body, list) and len(body) == 2
    for x in body:
        assert set(x) == {"id", "description", "photos", "created_at", "updated_at"}
