"""Saved AI readings kept in memory: never stale, independent copies, bounded."""
from thesis.db import one, transaction
from thesis.research import sentiment
from test_sentiment_history import original, variant


def count_loads(monkeypatch):
    loads = []
    real = sentiment.rows

    def counting(conn, sql, params=()):
        if "FROM sentiment_analyses WHERE id=ANY" in sql:
            loads.append(list(params[0]))
        return real(conn, sql, params)

    monkeypatch.setattr(sentiment, "rows", counting)
    return loads


def test_a_reading_is_loaded_once_and_each_caller_gets_its_own_copy(owner, monkeypatch):
    iid, first = original(owner)
    loads = count_loads(monkeypatch)
    with transaction() as c:
        mine = sentiment.reading(c, first["id"], iid)
        mine["packet"]["sources"].clear()
        two = sentiment.reading(c, first["id"])
    assert len(loads) == 1
    assert two["packet"]["sources"], "a caller's change leaked into the cache"
    with transaction() as c:
        assert sentiment.reading(c, first["id"], "00000000-0000-4000-8000-000000000000") is None
        assert sentiment.reading(c, None) is None
        assert sentiment.readings(c, [first["id"], "11111111-1111-4111-8111-111111111111"]).keys() == {first["id"]}


def test_latest_record_and_presentation_match_the_uncached_query(owner):
    iid, first = original(owner)
    later = variant(iid, first["id"], minutes=5)
    with transaction() as c:
        uncached = sentiment.present(c, one(c, sentiment.LATEST_SQL, (iid,)), partial=True)
        assert str(sentiment.latest_record(c, iid)["id"]) == later
        assert sentiment.latest(c, iid) == uncached
        # Served from memory the second time, still the same answer.
        assert sentiment.latest(c, iid) == uncached


def test_memory_is_bounded(owner, monkeypatch):
    iid, first = original(owner)
    ids = [first["id"]] + [variant(iid, first["id"], minutes=m) for m in (5, 10, 15, 20, 25)]
    with transaction() as c:
        sentiment.reading(c, first["id"])
        size = sentiment._reading_bytes
        assert size > 0
        # Room for about four readings: the oldest-used ones are dropped.
        monkeypatch.setattr(sentiment, "READING_CACHE_BYTES", int(size * 4.5))
        sentiment.clear_reading_cache()
        for identity in ids:
            assert sentiment.reading(c, identity)
        assert 0 < len(sentiment._readings) < len(ids)
        assert sentiment._reading_bytes <= sentiment.READING_CACHE_BYTES
        assert ids[-1] in sentiment._readings and ids[0] not in sentiment._readings
        # A reading bigger than a quarter of the room is served but not kept.
        monkeypatch.setattr(sentiment, "READING_CACHE_BYTES", size)
        sentiment.clear_reading_cache()
        assert sentiment.reading(c, first["id"])
        assert len(sentiment._readings) == 0


def test_ids_only_permission_checks_match_the_full_reads(owner):
    """permitted_ids now reads ids only; it must agree with the full reads it
    replaced, including after a withdrawal."""
    from datetime import datetime, timezone
    from thesis import service
    from thesis.research import social
    iid, first = original(owner)
    with transaction() as c:
        record = sentiment.reading(c, first["id"])
        cutoff = datetime.fromisoformat(record["packet"]["cutoff"])
        full_docs = {str(d["id"]) for d in service.permitted_documents(c, cutoff, iid)}
        full_posts = {str(d["id"]) for d in social.documents(c, iid, cutoff, 7)}
        assert full_docs | full_posts, "fixture has no sources to compare"
        assert service.permitted_document_ids(c, cutoff, iid) == full_docs
        assert social.document_ids(c, iid, cutoff, 7) == full_posts
        posts = social.documents(c, iid, cutoff, 7)
    if posts:
        with transaction(admin=True) as c:
            c.execute("INSERT INTO social_withdrawals VALUES(%s,%s)", (posts[0]["post_key"], datetime.now(timezone.utc)))
        with transaction() as c:
            after = {str(d["id"]) for d in social.documents(c, iid, cutoff, 7)}
            assert social.document_ids(c, iid, cutoff, 7) == after
            assert str(posts[0]["id"]) not in after
