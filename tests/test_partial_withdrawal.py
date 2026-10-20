"""A withdrawn source withholds only what depends on it; offline, disposable DB."""

import json
from datetime import datetime, timezone
from uuid import uuid4
import pytest
from psycopg.types.json import Jsonb
from thesis import review_digest
from thesis.db import transaction, one
from thesis.research import sentiment
from thesis.monitoring import news_watch, telegram, telegram_message
from test_market import commit, news, prepare
from test_sentiment import add_social, provider

REDDIT_BODY = "I am concerned about Microsoft margins"


def strict_and_partial(c, iid):
    """The stored reading stays whole-withheld; the company view drops only social parts."""
    record = one(c, "SELECT * FROM sentiment_analyses WHERE instrument_id=%s ORDER BY created_at DESC LIMIT 1", (iid,))
    assert sentiment.present(c, record)["withheld"]
    current = sentiment.latest(c, iid)
    assert not current["withheld"] and current["withheld_sources"]
    assert not any(i["channel"] == "social" for i in current["items"])
    assert not any(s["kind"] == "social" for s in current["sources"])
    return current


def withdraw_reddit():
    with transaction(source=True) as c:
        c.execute(
            "INSERT INTO social_withdrawals VALUES('t3_abc123',%s)",
            (datetime.now(timezone.utc),),
        )


def stored(identity):
    with transaction() as c:
        return one(c, "SELECT * FROM sentiment_analyses WHERE id=%s", (identity,))


def reading(owner):
    iid = prepare(owner)
    add_social(iid)
    return iid, sentiment.generate(iid, transport=provider())


def split(result):
    social = next(i for i in result["items"] if i["channel"] == "social")
    news_item = next(i for i in result["items"] if i["channel"] == "news")
    return news_item, social


def authored_alert(owner, iid, analysis_id, payload, kind="sentiment"):
    # Authored delivery fixture: tests the presentation boundary, not alert rules.
    identity = uuid4()
    with transaction(owner) as c:
        c.execute(
            "INSERT INTO research_alerts VALUES(%s,%s,%s,%s,%s,%s,NULL,%s,now())",
            (identity, owner, iid, kind, analysis_id, analysis_id, Jsonb(payload)),
        )
    return str(identity)


def alert(owner, identity):
    with transaction(owner) as c:
        return news_watch.list_alerts(c, owner, ids=[identity])[0]


def test_reading_with_withdrawn_reddit_comment_still_shows_its_news(owner):
    iid, result = reading(owner)
    before = stored(result["id"])
    news_item, _ = split(result)
    withdraw_reddit()
    with transaction() as c:
        current = sentiment.latest(c, iid)
        # Other consumers keep the whole-reading rule until they are adapted.
        assert sentiment.present(c, stored(result["id"]))["withheld"]
    assert not current["withheld"]
    assert [i["source_id"] for i in current["items"]] == [news_item["source_id"]]
    assert {s["kind"] for s in current["sources"]} == {"news"}
    assert current["withheld_sources"] == 1
    assert current["withheld_summaries"] == {"reddit": 1, "social": 1}
    # The news total is complete; totals that counted the comment are withheld.
    assert current["summary"]["news"] == result["summary"]["news"]
    assert "social" not in current["summary"]
    assert "reddit" not in current["summary"].get("social_platforms", {})
    assert REDDIT_BODY not in json.dumps(current, default=str)
    # Presentation only: the append-only record is unchanged.
    assert stored(result["id"]) == before


def test_alert_with_unaffected_items_stays_visible_and_exports(owner):
    iid = prepare(owner)
    add_social(iid)
    sentiment.generate(iid, transport=provider("neutral"))
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
    with transaction(owner) as c:
        original = news_watch.list_alerts(c, owner)[0]
    withdraw_reddit()
    with transaction(owner) as c:
        shown = news_watch.list_alerts(c, owner)[0]
    assert not shown["withheld"]
    assert shown["payload"] == original["payload"]
    assert "withheld_items" not in shown["payload"]
    assert shown["sources"] == original["sources"]
    assert all(i["channel"] == "news" for i in shown["previous_items"])
    assert {s["kind"] for s in shown["previous_sources"]} <= {"news"}
    assert REDDIT_BODY not in json.dumps(shown, default=str)
    html = review_digest.download(owner)[1]
    assert "Microsoft reports weaker margins" in html
    assert "details withheld" not in html and REDDIT_BODY not in html


def test_alert_citing_withdrawn_source_is_withheld_everywhere(owner):
    iid, result = reading(owner)
    _, social = split(result)
    news_watch.configure(owner, iid, False)
    identity = authored_alert(
        owner, iid, result["id"], dict(kind="sentiment", reason="Authored.", items=[social])
    )
    assert not alert(owner, identity)["withheld"]
    withdraw_reddit()
    hidden = alert(owner, identity)
    assert hidden["withheld"] and not hidden["payload"] and not hidden["sources"]
    html = review_digest.download(owner)[1]
    assert "details withheld" in html and REDDIT_BODY not in html
    with transaction(owner) as c:
        record = telegram.event(c, owner, "company", identity)
    with pytest.raises(ValueError, match="Source access changed"):
        telegram_message.render(record)


def test_partly_affected_alert_keeps_unaffected_parts_and_is_not_forwarded(owner):
    iid, result = reading(owner)
    news_item, social = split(result)
    news_watch.configure(owner, iid, False)
    sample = dict(tone="negative leaning", selected=5)
    shift = lambda channel, platform, item: dict(
        channel=channel, platform=platform, title="Changed", before=sample, after=sample, items=[item]
    )
    shifts = authored_alert(
        owner,
        iid,
        result["id"],
        dict(
            kind="sentiment",
            reason="Authored.",
            shifts=[shift("news", None, news_item), shift("social", "reddit", social)],
            items=[news_item, social],
        ),
    )
    reporting = authored_alert(
        owner,
        iid,
        result["id"],
        dict(kind="new_reporting", reason="Authored.", items=[news_item, social]),
        kind="new_reporting",
    )
    withdraw_reddit()
    for identity in (shifts, reporting):
        shown = alert(owner, identity)
        assert not shown["withheld"]
        assert [i["source_id"] for i in shown["payload"]["items"]] == [news_item["source_id"]]
        assert shown["payload"]["withheld_items"] == 1
        assert {s["kind"] for s in shown["sources"]} == {"news"}
        assert REDDIT_BODY not in json.dumps(shown, default=str)
    assert [s["channel"] for s in alert(owner, shifts)["payload"]["shifts"]] == ["news"]
    html = review_digest.download(owner)[1]
    assert "1 cited source is no longer available" in html and REDDIT_BODY not in html
    with transaction(owner) as c:
        record = telegram.event(c, owner, "company", reporting)
    # Telegram never forwards an alert with withheld evidence.
    with pytest.raises(ValueError, match="Source access changed"):
        telegram_message.render(record)


def test_withdrawn_comparison_link_withholds_the_linked_claim(owner):
    iid, result = reading(owner)
    news_item, _ = split(result)
    news_watch.configure(owner, iid, False)
    link = dict(source_id=news_item["source_id"], reference_source_id=str(uuid4()), relation="adds_detail")
    identity = authored_alert(
        owner,
        iid,
        result["id"],
        dict(kind="new_reporting", reason="Authored.", items=[news_item], coverage_links=[link]),
        kind="new_reporting",
    )
    # The current reading does not show this link, so the linked claim is withheld.
    assert alert(owner, identity)["withheld"]
