import json
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import pytest
from thesis import service
from thesis.db import transaction, one, rows
from thesis.research import sentiment, social
from thesis.monitoring import news_watch
from thesis.providers import ledger
from test_market import prepare, commit, news
from test_model_budget import response


def feed(
    title="Microsoft earnings outlook worries investors",
    body="I am concerned about Microsoft margins, but I am not saying a collapse is certain.",
    key="abc123",
    date=None,
):
    date = date or (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    from xml.sax.saxutils import escape

    return f'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>t3_{key}</id><title>{escape(title)}</title><link href="https://www.reddit.com/r/stocks/comments/{key}/discussion/"/><published>{date}</published><author><name>/u/public-example</name></author><content>{escape(body)}</content></entry></feed>'.encode()


def provider(tone="negative", kind="reported_development", mutate=None):
    def call(body):
        packet = json.loads(body["input"][1]["content"])
        items = []
        for s in packet["sources"]:
            items.append(
                dict(
                    id=s["label"],
                    relevance="relevant",
                    sentiment=tone,
                    statement="opinion" if s["channel"] == "social" else kind,
                    topic="earnings",
                    basis=(
                        "descriptive"
                        if tone == "neutral"
                        else "unclear" if tone == "unclear" else "expressed_evaluation"
                    ),
                    previous_passages=[],
                    price_claims=[],
                    passages=[
                        next(
                            p["id"]
                            for p in s["passages"]
                            if not s.get("conversation") or p["id"] != "p0"
                        )
                    ],
                    context_passages=(
                        [s["conversation"]["passages"][0]["id"]]
                        if s.get("conversation")
                        else []
                    ),
                )
            )
        if mutate:
            items = mutate(items)
        branches = body["text"]["format"]["schema"]["properties"]["items"]["items"]["anyOf"]
        for item, branch in zip(items, branches):
            if "reporting" in branch["properties"]:
                event = item["statement"] in {"reported_development", "rumour"} and item["relevance"] == "relevant"
                item["reporting"] = dict(kind="reported_event" if event else "not_applicable", passages=item["passages"] if event else [], impact="adverse" if event and item["sentiment"] in {"negative", "mixed"} else "not_stated")
        return response() | dict(
            model=body["model"],
            id="resp_" + str(uuid4()),
            output=[
                dict(
                    type="message",
                    content=[
                        dict(
                            type="output_text",
                            text=json.dumps(dict(items=items, coverage_links=[])),
                        )
                    ],
                )
            ],
        )

    return call


def add_social(iid, body=None):
    with transaction(source=True) as c:
        c.execute(
            "UPDATE social_refresh_lock SET last_attempt_at=NULL,lease_until=NULL"
        )
    social.refresh(fetcher=lambda _: body or feed())


def test_social_parse_retains_negation_and_removes_markup_and_identity():
    posts, n = social.parse_feed(
        feed(
            body="<p>Microsoft has not collapsed.</p> submitted by /u/public-example [link] [comments]"
        ),
        "stocks",
        datetime.now(timezone.utc),
    )
    assert n == 0 and posts[0]["body"] == "Microsoft has not collapsed."
    assert posts[0]["author_hash"] and "public-example" not in posts[0]["body"]
    assert social.mentions(posts[0], "MSFT") and not social.mentions(posts[0], "AAPL")


@pytest.mark.parametrize(
    "body", [b"<!DOCTYPE feed><feed/>", b'<!ENTITY x "bad"><feed/>', b"x" * 2000001]
)
def test_social_rejects_unsafe_or_oversized_xml(body):
    with pytest.raises(ValueError):
        social.parse_feed(body, "stocks", datetime.now(timezone.utc))


def test_social_rejects_future_old_missing_dates_and_foreign_links():
    now = datetime.now(timezone.utc)
    for date in [
        (now + timedelta(days=1)).isoformat(),
        (now - timedelta(days=8)).isoformat(),
        "not a timestamp",
    ]:
        p, n = social.parse_feed(feed(date=date), "stocks", now)
        assert not p and n == 1
    p, n = social.parse_feed(
        feed().replace(b"https://www.reddit.com", b"https://evil.example"),
        "stocks",
        now,
    )
    assert not p and n == 1


def test_social_refresh_is_deduplicated_and_cooldown_is_persisted(owner):
    iid = prepare(owner)
    add_social(iid)
    with transaction() as c:
        assert len(social.documents(c, iid, datetime.now(timezone.utc))) == 1
    with pytest.raises(service.Conflict):
        social.refresh(fetcher=lambda _: pytest.fail("network repeated"))


def test_sentiment_separates_sources_exact_quotes_cache_and_thin_samples(owner):
    iid = prepare(owner)
    add_social(iid)
    result = sentiment.generate(iid, transport=provider())
    assert not result["withheld"]
    assert (
        result["summary"]["news"]["selected"] == 1
        and result["summary"]["social"]["selected"] == 1
    )
    assert result["summary"]["social"]["tone"] == "thin sample"
    assert {i["statement"] for i in result["items"]} == {
        "reported_development",
        "opinion",
    }
    budget = ledger.snapshot()
    repeat = sentiment.generate(iid, transport=lambda _: pytest.fail("cached"))
    assert repeat["id"] == result["id"] and ledger.snapshot() == budget
    with transaction() as c:
        stored = one(c, "SELECT * FROM sentiment_analyses WHERE id=%s", (result["id"],))
        for item in result["items"]:
            source = next(
                s for s in stored["packet"]["sources"] if s["id"] == item["source_id"]
            )
            for quote in item["citations"]:
                assert quote["quote"] in source["title"] + "\n" + source["text"]


@pytest.mark.parametrize(
    "fault", ["missing", "duplicate", "foreign_passage", "wrong_direction"]
)
def test_invalid_sentiment_batch_publishes_nothing(owner, fault):
    iid = prepare(owner)
    add_social(iid)

    def mutate(items):
        if fault == "missing":
            return items[:-1]
        if fault == "duplicate":
            return [items[0], items[0]]
        if fault == "foreign_passage":
            items[0]["passages"] = ["invented"]
        if fault == "wrong_direction":
            items[0]["relevance"] = "unrelated"
        return items

    with pytest.raises(ValueError):
        sentiment.generate(iid, transport=provider(mutate=mutate))
    with transaction() as c:
        assert not rows(c, "SELECT * FROM sentiment_analyses")


def test_withdrawn_social_source_withholds_aggregate_and_alerts(owner):
    iid = prepare(owner)
    add_social(iid)
    result = sentiment.generate(iid, transport=provider())
    with transaction(admin=True) as c:
        c.execute("UPDATE social_feeds SET enabled=false")
    try:
        with transaction() as c:
            current = sentiment.latest(c, iid)
            assert (
                current["withheld"]
                and not current["items"]
                and not current["sources"]
                and not current["summary"]
            )
    finally:
        with transaction(admin=True) as c:
            c.execute("UPDATE social_feeds SET enabled=true")


def test_new_risk_alert_is_grouped_idempotent_and_private(owner):
    iid = prepare(owner)
    add_social(iid)
    first = sentiment.generate(iid, transport=provider("neutral"))
    news_watch.configure(owner, iid, True)
    commit(
        iid,
        [
            news(
                id=2,
                url="https://example.test/negative",
                headline="Microsoft reports weaker margins",
                summary="Microsoft says operating margins decreased in the reported period.",
            )
        ],
    )
    second = sentiment.generate(iid, transport=provider())
    assert news_watch.publish(owner, iid, second["id"]) == 1
    assert news_watch.publish(owner, iid, second["id"]) == 0
    with transaction(owner) as c:
        alerts = news_watch.list_alerts(c, owner)
        assert len(alerts) == 1 and not alerts[0]["review_action"]
        assert alerts[0]["payload"]["items"] and not alerts[0]["withheld"]
    with transaction(str(uuid4())) as c:
        assert not news_watch.list_alerts(c, str(uuid4()))
    assert news_watch.review(owner, alerts[0]["id"], "reviewed") == news_watch.review(
        owner, alerts[0]["id"], "reviewed"
    )
    with pytest.raises(service.Conflict):
        news_watch.review(owner, alerts[0]["id"], "unresolved")
    with pytest.raises(service.Missing):
        news_watch.review(str(uuid4()), alerts[0]["id"], "reviewed")
    with transaction(owner) as c:
        with pytest.raises(Exception):
            c.execute(
                "UPDATE research_alerts SET payload='{}' WHERE owner_id=%s", (owner,)
            )

    with transaction(admin=True) as c:
        c.execute("UPDATE social_feeds SET enabled=false")
    try:
        with transaction(owner) as c:
            hidden = news_watch.list_alerts(c, owner)[0]
            assert hidden["withheld"]
            assert not any(
                hidden[k]
                for k in ("payload", "sources", "previous_items", "previous_sources")
            )
    finally:
        with transaction(admin=True) as c:
            c.execute("UPDATE social_feeds SET enabled=true")


def test_first_sample_does_not_invent_change_and_stopped_watch_does_not_alert(owner):
    iid = prepare(owner)
    news_watch.configure(owner, iid, True)
    first = sentiment.generate(iid, transport=provider())
    assert news_watch.publish(owner, iid, first["id"]) == 0
    news_watch.configure(owner, iid, False)
    commit(
        iid,
        [
            news(
                id=4,
                url="https://example.test/later",
                headline="Microsoft warns on demand",
            )
        ],
    )
    newer = sentiment.generate(iid, transport=provider())
    assert news_watch.publish(owner, iid, newer["id"]) == 0
    with transaction(owner) as c:
        assert not news_watch.list_alerts(c, owner)


def test_shift_needs_distinct_new_evidence_and_separates_news_social():
    def make(tone, kind, prefix):
        items = [
            dict(
                id=str(i),
                source_id=str(i),
                channel=kind,
                relevance="relevant",
                sentiment=tone,
                statement="opinion",
            )
            for i in range(5)
        ]
        return dict(
            packet={
                "sources": [
                    dict(id=str(i), content_hash=prefix + str(i), channel=kind)
                    for i in range(5)
                ]
            },
            result={
                "items": items,
                "summary": sentiment.summarize(items),
                "summary_policy": sentiment.POLICY,
                "prompt_version": sentiment.PROMPT,
                "model": sentiment.REASONING_MODEL,
            },
        )

    old = make("positive", "social", "old")
    new = make("negative", "social", "new")
    changes = news_watch.changes(old, new)
    assert len(changes) == 1 and changes[0]["kind"] == "sentiment"
    assert changes[0]["shifts"][0]["channel"] == "social"
    assert not news_watch.changes(old, make("negative", "social", "old"))
    assert not news_watch.changes(
        old, make("negative", "news", "new")
    )  # Different source sample; no former news baseline; opinion is not an adverse-report alert.


def test_scheduler_uses_opt_in_and_lease_and_records_failure(owner):
    iid = prepare(owner)
    now = datetime.now(timezone.utc)
    assert not news_watch.run_once(
        owner, now=now, market_refresh=lambda _: pytest.fail("unrequested")
    )
    news_watch.configure(owner, iid, True, 60, now)
    calls = []
    assert not news_watch.run_once(
        owner, now=now, market_refresh=lambda _: pytest.fail("early")
    )

    def fail(i):
        calls.append(i)
        raise ValueError("mock paid error")

    assert news_watch.run_once(
        owner,
        now=now + timedelta(minutes=61),
        market_refresh=lambda _: None,
        social_refresh=lambda: None,
        analyzer=fail,
    )
    assert calls == [iid]
    assert not news_watch.run_once(
        owner,
        now=now + timedelta(minutes=61),
        market_refresh=lambda _: pytest.fail("immediate retry"),
    )
    with transaction(owner) as c:
        w = one(c, "SELECT * FROM news_watches WHERE owner_id=%s", (owner,))
        assert w["error"] and w["lease_until"] is None


def test_disabled_during_check_does_not_analyse_or_publish(owner):
    iid = prepare(owner)
    now = datetime.now(timezone.utc)
    news_watch.configure(owner, iid, True, 60, now)
    news_watch.run_once(
        owner,
        now=now + timedelta(minutes=61),
        market_refresh=lambda _: news_watch.configure(owner, iid, False),
        social_refresh=lambda: None,
        analyzer=lambda _: pytest.fail("disabled during refresh"),
    )


def test_seen_stories_do_not_realert_when_they_return_in_later_samples(owner):
    iid = prepare(owner)
    first = sentiment.generate(iid, transport=provider())
    news_watch.configure(owner, iid, True)
    with transaction(owner) as c:
        original = one(
            c, "SELECT * FROM sentiment_analyses WHERE id=%s", (first["id"],)
        )
        hashes = {
            (s["channel"], sentiment.coverage_key(s))
            for s in original["packet"]["sources"]
        }
        seen = {
            (s["channel"], s["content_hash"])
            for s in rows(c, "SELECT * FROM watch_seen_sources")
        }
        assert hashes == seen
    previous = deepcopy(original)
    for s in previous["packet"]["sources"]:
        s["content_hash"] = "different-between-samples"
    assert news_watch.changes(previous, original)
    assert not news_watch.changes(previous, original, seen)


def test_watch_fences_reconfigured_claim_and_older_cutoff(owner):
    from psycopg.types.json import Jsonb

    iid = prepare(owner)
    first = sentiment.generate(iid, transport=provider())
    news_watch.configure(owner, iid, True)
    assert news_watch.publish(owner, iid, first["id"], claim_token=uuid4()) == 0
    with transaction() as c:
        original = one(
            c, "SELECT * FROM sentiment_analyses WHERE id=%s", (first["id"],)
        )
        packet = deepcopy(original["packet"])
        packet["cutoff"] = (
            datetime.fromisoformat(packet["cutoff"]) - timedelta(hours=1)
        ).isoformat()
        older_id = uuid4()
        c.execute(
            "INSERT INTO sentiment_analyses VALUES(%s,%s,%s,%s,%s,%s,now())",
            (
                older_id,
                iid,
                "old-cutoff-test",
                original["call_id"],
                Jsonb(packet),
                Jsonb(original["result"]),
            ),
        )
    assert news_watch.publish(owner, iid, older_id) == 0
    with transaction(owner) as c:
        assert (
            str(one(c, "SELECT baseline_id FROM news_watches")["baseline_id"])
            == first["id"]
        )
        assert sentiment.latest(c, iid)["id"] == first["id"]


def test_social_denial_is_visible_and_cached_posts_remain(owner):
    import httpx

    iid = prepare(owner)
    add_social(iid)
    with transaction(source=True) as c:
        c.execute("UPDATE social_refresh_lock SET last_attempt_at=NULL")

    def denied(_):
        r = httpx.Response(403, request=httpx.Request("GET", "https://www.reddit.com/"))
        r.raise_for_status()

    assert social.refresh(fetcher=denied)["failures"] == 3
    with transaction() as c:
        statuses = social.status(c)
        assert all("403" in s["error"] for s in statuses if s['feed'] in social.LEGACY_FEEDS)
        assert all(s['error'] is None for s in statuses if s['feed'] not in social.LEGACY_FEEDS)
        assert len(social.documents(c, iid, datetime.now(timezone.utc))) == 1


def test_recent_manual_refresh_does_not_prevent_due_watch_analysis(owner):
    iid = prepare(owner)
    first = sentiment.generate(iid, transport=provider())
    now = datetime.now(timezone.utc)
    news_watch.configure(owner, iid, True, now=now)

    def cooldown(*args):
        raise service.Conflict("recently checked")

    assert news_watch.run_once(
        owner,
        now=now + timedelta(minutes=61),
        market_refresh=cooldown,
        social_refresh=cooldown,
        analyzer=lambda _: first,
    )
    with transaction(owner) as c:
        assert one(c, "SELECT error FROM news_watches")["error"] is None


def test_copied_bodies_count_once_and_direction_requires_majority():
    items = []
    sources = []
    for i, tone in enumerate(
        ["positive", "positive", "mixed", "mixed", "mixed", "neutral"]
    ):
        items.append(
            dict(source_id=str(i), channel="news", relevance="relevant", sentiment=tone)
        )
        sources.append(
            dict(
                id=str(i),
                channel="news",
                text=("A shared substantive body. " * 10 if i < 2 else str(i) * 200),
                content_hash=str(i),
            )
        )
    result = sentiment.summarize(items, sources)["news"]
    assert (
        result["selected"] == 6
        and result["relevant"] == 6
        and result["counted_groups"] == 5
    )
    assert result["counts"]["positive"] == 1 and result["tone"] == "mixed / balanced"
    items[1]["sentiment"] = "negative"
    result = sentiment.summarize(items, sources)["news"]
    assert result["counts"]["mixed"] == 4 and result["counts"]["negative"] == 0


def test_summary_policy_upgrade_reuses_paid_response(owner, monkeypatch):
    iid = prepare(owner)
    first = sentiment.generate(iid, transport=provider())
    before = ledger.snapshot()
    monkeypatch.setattr(sentiment, "POLICY", "mock-policy-upgrade")
    after = sentiment.generate(
        iid,
        transport=lambda _: pytest.fail(
            "An aggregate policy change must not re-dispatch the same model input"
        ),
    )
    assert (
        after["id"] != first["id"] and after["summary_policy"] == "mock-policy-upgrade"
    )
    assert ledger.snapshot() == before


def test_old_method_warning_preserves_saved_output_and_makes_no_call(
    owner, monkeypatch
):
    iid = prepare(owner)
    first = sentiment.generate(iid, transport=provider())
    before = ledger.snapshot()
    with transaction() as c:
        record = one(c, "SELECT * FROM sentiment_analyses WHERE id=%s", (first["id"],))
        original = deepcopy(record)
        assert not sentiment.present(c, record)["earlier_method"]
        monkeypatch.setattr(sentiment, "PROMPT", "future-test-method")
        shown = sentiment.present(c, record)
        assert shown["earlier_method"] and shown["items"] == first["items"]
        assert record == original
        assert (
            one(c, "SELECT * FROM sentiment_analyses WHERE id=%s", (first["id"],))
            == original
        )
    assert before == ledger.snapshot()
