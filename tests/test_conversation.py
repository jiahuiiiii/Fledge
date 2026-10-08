"""Mocked original-source inspection; never network or paid providers."""

from copy import deepcopy
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import httpx
import psycopg
import pytest
from fastapi.testclient import TestClient
from thesis import service
from thesis.db import transaction, one
from thesis.research import conversation as cv, sentiment, social
from thesis.providers import ledger
from test_hackernews import item, transport, hn
from test_market import prepare
from test_sentiment import provider


def setup(owner):
    iid = prepare(owner)
    child = item()
    hn.refresh(iid, fetcher=transport({"123": child}))
    with transaction() as c:
        p = social.documents(c, iid, datetime.now(timezone.utc))[0]
    parent = dict(
        id=99,
        type="comment",
        text="I think Microsoft software is excellent. Do you agree?",
        time=child["time"] - 60,
        by="another-test-author",
        parent=88,
    )
    return iid, p, child, parent


def fetcher(child, parent, calls):
    def run(kind, key, now):
        calls.append((kind, key))
        assert len(calls) <= 2
        return deepcopy(child if key == "123" else parent)

    return run


def unlock(pid):
    with transaction(source=True) as c:
        c.execute(
            "UPDATE social_conversation_state SET last_attempt_at=NULL,lease_until=NULL WHERE post_id=%s",
            (pid,),
        )


def test_original_parent_separate_no_recursion_no_ai_and_read_only(owner, monkeypatch):
    iid, p, child, parent = setup(owner)
    calls = []
    budget = ledger.snapshot()
    monkeypatch.setattr(
        hn, "fetch", lambda *_: pytest.fail("Read made a source request")
    )
    assert cv.read(p["id"])["result"] is None
    result = cv.collect(p["id"], fetcher=fetcher(child, parent, calls))
    assert calls == [("item", "123"), ("item", "99")]
    assert result["result"]["outcome"] == "available"
    assert (
        result["result"]["body"] == parent["text"]
        and result["result"]["parent_type"] == "comment"
    )
    assert result["result"]["url"] == "https://news.ycombinator.com/item?id=99"
    assert "another-test-author" not in str(result)
    assert cv.read(p["id"]) == result
    assert ledger.snapshot() == budget
    with pytest.raises(service.Conflict):
        cv.collect(p["id"], fetcher=lambda *_: pytest.fail("Repeated source call"))
    with transaction() as c:
        assert (
            social.documents(c, iid, datetime.now(timezone.utc))[0]["body"]
            == child["text"]
        )
    with pytest.raises(psycopg.Error):
        with transaction(source=True) as c:
            c.execute("UPDATE social_conversation_results SET body='changed'")
    with pytest.raises(psycopg.Error):
        with transaction() as c:
            c.execute("DELETE FROM social_conversation_results")


def test_story_headline_is_not_child_opinion(owner):
    _, p, child, parent = setup(owner)
    parent.update(type="story", title="Microsoft product announcement", text="")
    result = cv.collect(p["id"], fetcher=fetcher(child, parent, []))["result"]
    assert (
        result["title"] == parent["title"]
        and result["body"] == ""
        and result["parent_type"] == "story"
    )
    assert "Loading context does not change saved AI labels" in result["explanation"]


@pytest.mark.parametrize(
    "change", [dict(text="I changed my view on Microsoft."), dict(time=1)]
)
def test_changed_child_does_not_borrow_current_parent(owner, change):
    _, p, child, parent = setup(owner)
    calls = []
    result = cv.collect(p["id"], fetcher=fetcher(child | change, parent, calls))[
        "result"
    ]
    assert result["outcome"] == "source_changed" and calls == [("item", "123")]
    assert "body" not in result


@pytest.mark.parametrize(
    "change",
    [dict(parent="../secret"), dict(parent=123), dict(id=321), dict(type="story")],
)
def test_bad_child_identity_or_parent_has_no_second_request(owner, change):
    _, p, child, parent = setup(owner)
    calls = []
    assert (
        cv.collect(p["id"], fetcher=fetcher(child | change, parent, calls))["result"][
            "outcome"
        ]
        == "unavailable"
    )
    assert calls == [("item", "123")]


@pytest.mark.parametrize(
    "change",
    [
        dict(id=98),
        dict(type="job"),
        dict(time=9999999999),
        dict(time=True),
        dict(text="x" * 6001),
        dict(text="My résumé. Microsoft developer."),
        dict(text=None),
    ],
)
def test_invalid_or_out_of_scope_parent_not_exposed(owner, change):
    _, p, child, parent = setup(owner)
    result = cv.collect(p["id"], fetcher=fetcher(child, parent | change, []))["result"]
    assert result["outcome"] == "unavailable" and "body" not in result


def test_removed_parent_withholds_retained_parent_not_child(owner):
    iid, p, child, parent = setup(owner)
    cv.collect(p["id"], fetcher=fetcher(child, parent, []))
    with transaction(source=True) as c:
        c.execute("INSERT INTO hn_withdrawals VALUES(%s,now())", ("hn:99",))
    assert cv.read(p["id"])["result"]["outcome"] == "unavailable"
    assert "body" not in cv.read(p["id"])["result"]
    with transaction() as c:
        assert social.documents(c, iid, datetime.now(timezone.utc))


def test_removed_child_withholds_its_saved_analysis(owner):
    iid, p, child, parent = setup(owner)
    analysis = sentiment.generate(iid, transport=provider())
    calls = []
    result = cv.collect(
        p["id"], fetcher=fetcher(dict(id=123, deleted=True), parent, calls)
    )
    assert result["source_removed"] and calls == [("item", "123")]
    with pytest.raises(service.Missing):
        cv.read(p["id"])
    with transaction() as c:
        assert sentiment.latest(c, iid)["withheld"]


def test_parent_denial_recorded_once_hides_old_parent(owner):
    _, p, child, parent = setup(owner)
    cv.collect(p["id"], fetcher=fetcher(child, parent, []))
    unlock(p["id"])
    calls = []

    def denied(kind, key, now):
        calls.append((kind, key))
        if key == "123":
            return child
        r = httpx.Response(
            403, request=httpx.Request("GET", "https://hacker-news.firebaseio.com/")
        )
        raise httpx.HTTPStatusError("denied", request=r.request, response=r)

    result = cv.collect(p["id"], fetcher=denied)["result"]
    assert (
        result["outcome"] == "failed"
        and "body" not in result
        and "403" in result["explanation"]
    )
    assert len(calls) == 2
    with transaction() as c:
        assert one(c, "SELECT count(*) n FROM social_conversation_results")["n"] == 2


def test_late_attempt_cannot_replace_newer_claim(owner):
    _, p, child, parent = setup(owner)

    def changed(kind, key, now):
        if key == "123":
            return child
        with transaction(source=True) as c:
            c.execute(
                "UPDATE social_conversation_state SET attempt_id=%s WHERE post_id=%s",
                (uuid4(), p["id"]),
            )
        return parent

    with pytest.raises(service.Conflict):
        cv.collect(p["id"], fetcher=changed)
    with transaction() as c:
        assert one(c, "SELECT count(*) n FROM social_conversation_results")["n"] == 0


def test_disabled_feed_denies_read_and_collection(owner):
    _, p, _, _ = setup(owner)
    with transaction(admin=True) as c:
        c.execute("UPDATE social_feeds SET enabled=false WHERE feed='hackernews'")
    try:
        with pytest.raises(service.Missing):
            cv.read(p["id"])
        with pytest.raises(service.Missing):
            cv.collect(
                p["id"], fetcher=lambda *_: pytest.fail("Disabled source requested")
            )
    finally:
        with transaction(admin=True) as c:
            c.execute("UPDATE social_feeds SET enabled=true WHERE feed='hackernews'")


def test_api_session_read_and_explicit_post_boundary(owner, monkeypatch):
    from thesis import app as web

    _, p, child, parent = setup(owner)
    calls = []
    monkeypatch.setattr(hn, "fetch", fetcher(child, parent, calls))
    client = TestClient(web.app)
    url = f"/api/v1/social-sources/{p['id']}/conversation"
    assert client.get(url).status_code == 401
    client.get("/api/v1/session")
    assert client.get(url).json()["result"]["result"] is None
    assert not calls and client.post(url).status_code == 403
    assert (
        client.post(url, headers={"x-thesis-request": "local-ui"}).json()["result"][
            "result"
        ]["body"]
        == parent["text"]
    )
    assert client.get(url).status_code == 200 and len(calls) == 2
