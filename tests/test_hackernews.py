"""Authored inputs and mocked providers only. No network or paid calls."""

from copy import deepcopy
from datetime import datetime, timezone, timedelta
import pytest
import httpx
from thesis.db import transaction, rows, one
from thesis import service
from thesis.research import hackernews as hn, social, sentiment
from thesis.monitoring import news_watch
from test_market import prepare
from test_sentiment import provider, add_social, feed


def item(
    key="123", text="I dislike Microsoft's software subscription terms.", now=None
):
    now = now or datetime.now(timezone.utc)
    return dict(
        id=int(key),
        type="comment",
        text=text,
        by="author-test",
        time=int((now - timedelta(minutes=1)).timestamp()),
        parent=99,
    )


def transport(data=None):
    data = data or {"123": item()}
    return lambda kind, value, now: (
        dict(
            hits=[
                dict(
                    objectID=k,
                    story_title="Misleading parent says Microsoft is wonderful",
                    comment_text="Stale search text",
                )
                for k in data
            ]
        )
        if kind == "search"
        else data[str(value)]
    )


def unlock(iid):
    with transaction(source=True) as c:
        c.execute(
            "UPDATE hn_refresh_state SET last_attempt_at=NULL,lease_until=NULL WHERE instrument_id=%s",
            (iid,),
        )


def test_original_only_text_identity_negation_and_hasher():
    now = datetime.now(timezone.utc)
    result, deleted = hn.parse_item(
        item(text="<p>I do not trust Microsoft &amp; its pricing.</p>"),
        "123",
        "MSFT",
        now,
    )
    assert not deleted and result["body"] == "I do not trust Microsoft & its pricing."
    assert result["title"] == "Hacker News comment" and result["post_key"] == "hn:123"
    assert "author-test" not in str(result) and len(result["author_hash"]) == 64
    assert result["url"] == "https://news.ycombinator.com/item?id=123"


@pytest.mark.parametrize(
    "change", [dict(id=124), dict(type="story"), dict(time="123"), dict(text=None)]
)
def test_rejects_mismatched_or_incomplete_original(change):
    with pytest.raises(ValueError):
        hn.parse_item(item() | change, "123", "MSFT", datetime.now(timezone.utc))


@pytest.mark.parametrize("change", [dict(dead=True), dict(deleted=True)])
def test_withdrawn_original_has_no_text(change):
    assert hn.parse_item(
        item() | change, "123", "MSFT", datetime.now(timezone.utc)
    ) == (None, True)


@pytest.mark.parametrize(
    "change",
    [
        dict(text="A company that is not the target."),
        dict(text="x" * 12001),
        dict(time=1),
        dict(time=9999999999),
    ],
)
def test_excludes_wrong_target_age_and_size(change):
    assert hn.parse_item(
        item() | change, "123", "MSFT", datetime.now(timezone.utc)
    ) == (None, False)


def test_discovery_bounded_and_no_search_text_used():
    assert hn.candidates(
        dict(
            hits=[
                dict(objectID="../private"),
                dict(objectID="123"),
                dict(objectID="123"),
            ]
        )
    ) == ["123"]
    assert (
        len(hn.candidates(dict(hits=[dict(objectID=str(k)) for k in range(1, 80)])))
        == 12
    )
    with pytest.raises(ValueError):
        hn.candidates(dict(error="bad"))


def test_persisted_cooldown_exact_source_and_disabled_access(owner):
    iid = prepare(owner)
    assert hn.refresh(iid, fetcher=transport())["failures"] == 0
    with pytest.raises(service.Conflict):
        hn.refresh(iid, fetcher=lambda *_: pytest.fail("Repeated HTTP"))
    with transaction() as c:
        posts = social.documents(c, iid, datetime.now(timezone.utc))
        assert len(posts) == 1 and posts[0]["body"] == item()["text"]
        assert social.publisher(posts[0]) == "Hacker News · comments"
        assert social.status(c, iid)[-1]["matched_count"] == 1
        assert len(social.status(c)) == 3
    result = sentiment.generate(iid, transport=provider())
    assert result["summary"]["social_platforms"]["hackernews"]["selected"] == 1
    assert result["summary"]["social"]["tone"] == "separate platform samples"
    with transaction(admin=True) as c:
        c.execute("UPDATE social_feeds SET enabled=false WHERE feed='hackernews'")
    try:
        with transaction() as c:
            assert sentiment.latest(c, iid)["withheld"]
    finally:
        with transaction(admin=True) as c:
            c.execute("UPDATE social_feeds SET enabled=true WHERE feed='hackernews'")


def test_rechecks_missing_search_items_and_withholds_deleted_history(owner):
    iid = prepare(owner)
    hn.refresh(iid, fetcher=transport())
    original = sentiment.generate(iid, transport=provider())
    unlock(iid)
    seen = []

    def removed(kind, key, now):
        seen.append((kind, key))
        return dict(hits=[]) if kind == "search" else dict(id=int(key), deleted=True)

    hn.refresh(iid, fetcher=removed)
    assert seen == [("search", "MSFT"), ("item", "123")]
    with transaction() as c:
        assert not social.documents(c, iid, datetime.now(timezone.utc))
        assert sentiment.latest(c, iid)["id"] == original["id"]
        assert sentiment.latest(c, iid)["withheld"]
        assert one(c, "SELECT count(*) n FROM social_posts")["n"] == 1


def test_failure_keeps_original_and_never_uses_unverified_search_text(owner):
    iid = prepare(owner)
    hn.refresh(iid, fetcher=transport())
    unlock(iid)

    def failed(kind, key, now):
        if kind == "search":
            return dict(
                hits=[
                    dict(
                        objectID="456",
                        comment_text="Microsoft collapse",
                        story_title="BAD",
                    )
                ]
            )
        raise httpx.ConnectTimeout("offline")

    assert hn.refresh(iid, fetcher=failed)["failures"] == 1
    with transaction() as c:
        posts = social.documents(c, iid, datetime.now(timezone.utc))
        assert len(posts) == 1 and posts[0]["post_key"] == "hn:123"
        assert social.status(c, iid)[-1]["error"]


def test_selection_balances_sources_and_platforms_count_independently(owner):
    iid = prepare(owner)
    hn.refresh(
        iid,
        fetcher=transport(
            {
                str(k): item(str(k), f"Microsoft's terms concern me for reason {k}.")
                for k in range(1, 13)
            }
        ),
    )
    parts = [
        feed(
            key="reddit" + str(k),
            body=f"Microsoft's pricing concerns me in example {k}.",
        )
        for k in range(8)
    ]
    merged = (
        parts[0].split(b"<entry>")[0]
        + b"".join(
            b"<entry>" + p.split(b"<entry>")[1].split(b"</feed>")[0] for p in parts
        )
        + b"</feed>"
    )
    add_social(iid, merged)
    with transaction() as c:
        packet = sentiment.prepare(c, iid)
    social_sources = [s for s in packet["sources"] if s["channel"] == "social"]
    assert [s["platform"] for s in social_sources] == ["reddit", "hackernews"] * 4
    assert packet["available_social_platforms"] == dict(reddit=8, hackernews=12)
    result = sentiment.generate(iid, transport=provider())
    assert all(
        result["summary"]["social_platforms"][platform]["counted_groups"] == 4 for platform in ("reddit", "hackernews")
    )
    assert result["coverage"]["platform_authors"] == dict(reddit=1, hackernews=1, x=0)


def sample(prefix, platform, tone):
    sources = [
        dict(
            id=f"{prefix}{k}",
            channel="social",
            platform=platform,
            content_hash=f"{prefix}{k}",
            title="Comment",
            text=f"Different view {prefix}{k}",
        )
        for k in range(3)
    ]
    items = [
        dict(
            id=s["id"],
            source_id=s["id"],
            channel="social",
            relevance="relevant",
            sentiment=tone,
            statement="opinion",
        )
        for s in sources
    ]
    return dict(
        packet=dict(sources=sources),
        result=dict(
            items=items,
            summary=sentiment.summarize(items, sources),
            summary_policy=sentiment.POLICY,
            prompt_version=sentiment.PROMPT,
            model="test",
        ),
    )


def test_platform_replacement_never_becomes_reversal_but_same_source_can():
    before = sample("a", "reddit", "positive")
    after = sample("b", "hackernews", "negative")
    assert news_watch.changes(before, after) == []
    hn_before = sample("c", "hackernews", "positive")
    changes = news_watch.changes(hn_before, after)
    assert len(changes) == 1 and changes[0]["shifts"][0]["platform"] == "hackernews"
    assert changes[0]["shifts"][0]["title"].startswith("Hacker News")
    assert news_watch.changes(after, after) == []


def test_refresh_company_checks_hn_despite_reddit_cooldown(monkeypatch):
    def recent(*args, **kwargs):
        raise service.Conflict("recent")

    from thesis.research import reddit_research
    monkeypatch.setattr(reddit_research, "refresh", recent)
    monkeypatch.setattr(
        hn, "refresh", lambda iid, **kwargs: dict(checked=["hackernews"], failures=0)
    )
    result = social.refresh_company("test")
    assert {key: result[key] for key in ("checked", "failures", "recent")} == dict(
        checked=["hackernews"], failures=0, recent=["reddit"]
    )
    assert result["x"]["status"] == "blocked"


@pytest.mark.parametrize(
    "body",
    [
        "Location: anywhere. Remote: Yes. Willing to relocate: Yes. Technologies: Nvidia, Microsoft.",
        "Microsoft Azure developer. Résumé: private.example.",
    ],
)
def test_personal_job_ads_excluded_from_company_discussion(body):
    assert hn.parse_item(
        item(text=body), "123", "MSFT", datetime.now(timezone.utc)
    ) == (None, False)


def test_access_denial_stops_remaining_original_requests(owner):
    iid = prepare(owner)
    seen = []

    def denied(kind, key, now):
        seen.append((kind, key))
        if kind == "search":
            return dict(hits=[dict(objectID="123"), dict(objectID="124")])
        r = httpx.Response(
            429, request=httpx.Request("GET", "https://hacker-news.firebaseio.com/")
        )
        raise httpx.HTTPStatusError("limited", request=r.request, response=r)

    assert hn.refresh(iid, fetcher=denied)["failures"] == 1
    assert seen == [("search", "MSFT"), ("item", "123")]


def test_link_schema_only_allows_news_labels_not_uuids_or_social(owner):
    iid = prepare(owner)
    hn.refresh(iid, fetcher=transport())
    with transaction() as c:
        packet = sentiment.prepare(c, iid)
    schema = sentiment.request_for(packet)["text"]["format"]["schema"]
    allowed = schema["$defs"]["Link"]["properties"]
    assert allowed["item_id"]["enum"] == [
        s["label"] for s in packet["sources"] if s["channel"] == "news"
    ]
    assert all(
        s["id"] not in allowed["reference_id"]["enum"] for s in packet["sources"]
    )
    packet["sources"] = [s for s in packet["sources"] if s["channel"] == "social"]
    packet["comparison_sources"] = []
    assert (
        sentiment.request_for(packet)["text"]["format"]["schema"]["properties"][
            "coverage_links"
        ]["maxItems"]
        == 0
    )
