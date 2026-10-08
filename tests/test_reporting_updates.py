"""Company watches must retain substantive updates even with neutral tone."""

from copy import deepcopy
import pytest
from thesis.monitoring import news_watch
from test_news_coverage import source, analyse, relation
from datetime import timedelta
from uuid import uuid4
from thesis.db import transaction, one
from thesis.providers import ledger
from thesis.monitoring import watch_history
from thesis import review_digest
from reporting_update_fixture import begin, acquire, run


@pytest.mark.parametrize("tone", ["neutral", "positive"])
@pytest.mark.parametrize("kind", ["adds_detail", "contradicts"])
def test_seen_story_update_alert_does_not_require_adverse_tone(tone, kind):
    earlier = source("item_1", "Microsoft may close the service.", 0)
    current = source(
        "item_2", "Microsoft confirmed that the service will remain open.", 1
    )
    before = analyse([earlier], [])
    after = analyse(
        [current], [relation(kind=kind)], comparisons=[earlier], tones={"item_2": tone}
    )
    alerts = news_watch.changes(before, after)
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["kind"] == "new_reporting"
    assert alert["items"][0]["source_id"] == "item_2"
    assert alert["coverage_links"][0]["relation"] == kind
    assert alert["coverage_links"][0]["reference_source_id"] == "item_1"


def test_unseen_reference_is_not_a_change_to_previously_watched_reporting():
    earlier = source("item_1", "Microsoft may close the service.", 0)
    other = source("item_0", "Microsoft describes an unrelated service.", 0)
    current = source("item_2", "Microsoft says the service remains open.", 1)
    before = analyse([other], [])
    after = analyse(
        [current],
        [relation(kind="contradicts")],
        comparisons=[earlier],
        tones={"item_2": "neutral"},
    )
    assert news_watch.changes(before, after) == []
    alerts = news_watch.changes(before, after, {("news", "content:item_1")})
    assert len(alerts) == 1 and alerts[0]["coverage_links"]


def test_repeated_correction_and_new_method_do_not_redeliver_seen_text():
    earlier = source("item_1", "Microsoft may close the service.", 0)
    current = source("item_2", "Microsoft says the service remains open.", 1)
    before = analyse([earlier], [])
    after = analyse(
        [current],
        [relation(kind="contradicts")],
        comparisons=[earlier],
        tones={"item_2": "positive"},
    )
    seen = {("news", "content:item_2")}
    assert news_watch.changes(before, after, seen) == []
    changed = deepcopy(after)
    changed["result"]["prompt_version"] = "different-method"
    assert news_watch.changes(before, changed, seen) == []


def test_adverse_and_updated_reporting_share_one_grouped_alert():
    earlier = source("item_1", "Microsoft may close the service.", 0)
    update = source("item_2", "Microsoft says the service remains open.", 1)
    adverse = source("item_3", "Microsoft reports a separate outage.", 2)
    before = analyse([earlier], [])
    after = analyse(
        [update, adverse],
        [relation(kind="contradicts")],
        comparisons=[earlier],
        tones={"item_2": "neutral"},
    )
    alerts = news_watch.changes(before, after)
    assert len(alerts) == 1 and alerts[0]["kind"] == "new_reporting"
    assert {i["source_id"] for i in alerts[0]["items"]} == {"item_2", "item_3"}
    assert len(alerts[0]["coverage_links"]) == 1


def test_guarded_repeat_is_reviewable_but_not_claimed_as_verified_contradiction():
    earlier = source("item_1", "Microsoft says the service is closed.", 0)
    current = source("item_2", "Microsoft says the service is not closed.", 1)
    before = analyse([earlier], [])
    after = analyse(
        [current], [relation()], comparisons=[earlier], tones={"item_2": "neutral"}
    )
    assert after["result"]["coverage_links"][0]["review_note"]
    alerts = news_watch.changes(before, after)
    assert len(alerts) == 1
    assert alerts[0]["coverage_links"][0]["relation"] == "repeats"
    assert "interpretation, not a verified correction" in alerts[0]["reason"]


def test_watch_sequence_risk_clarification_repeat_failure_recovery_and_withdrawal(
    owner,
):
    iid, now = begin(owner)
    acquire(iid)
    assert run(owner, now)
    with transaction(owner) as c:
        first = news_watch.list_alerts(c, owner)[0]
    assert first["payload"]["title"] == "New adverse or mixed company reporting"
    news_watch.review(owner, first["id"], "reviewed")
    acquire(iid, clarification=True)
    assert run(owner, now + timedelta(hours=1))
    with transaction(owner) as c:
        alerts = news_watch.list_alerts(c, owner)
    assert len(alerts) == 2
    change = alerts[0]
    assert change["payload"]["title"] == "New reporting changes an earlier story"
    assert len(change["payload"]["items"]) == 1
    assert change["payload"]["items"][0]["sentiment"] == "neutral"
    assert change["review_action"] is None and alerts[1]["review_action"] == "reviewed"
    link = change["payload"]["coverage_links"][0]
    assert "denies" in link["citations"][0]["quote"]
    assert "unconfirmed" in link["reference_citations"][0]["quote"]
    before = ledger.snapshot()
    assert run(owner, now + timedelta(hours=2))
    assert ledger.snapshot() == before
    assert watch_history.history(owner, iid)["items"][0]["alert_count"] == 0

    def denied(_):
        raise ValueError("Authored unavailable feed")

    assert run(owner, now + timedelta(hours=3), refresh=denied)
    failed = watch_history.history(owner, iid)["items"][0]
    assert failed["status"] == "completed" and failed["details"]["coverage_gap"]
    assert "Some sources could not be refreshed" in failed["reason"]
    assert run(owner, now + timedelta(hours=4))
    assert ledger.snapshot() == before
    with transaction(owner) as c:
        assert len(news_watch.list_alerts(c, owner)) == 2
    _, html = review_digest.download(owner)
    assert "Earlier report: Authored Microsoft service-closure report" in html
    assert "AI comparison: these reports appear to make conflicting claims." in html
    assert "Earlier AI-written summary" not in html
    assert "Microsoft denies that the service will close." in html
    assert "An unconfirmed report says Microsoft will close the service." in html
    with transaction(str(uuid4())) as c:
        assert news_watch.list_alerts(c, str(uuid4())) == []
    # Withdrawal and recovery affect visibility, not old evidence or delivery.
    with transaction(admin=True) as c:
        definition = c.execute("SELECT pg_get_constraintdef(oid) definition FROM pg_constraint WHERE conrelid='sources'::regclass AND conname='sources_entitlement_check'").fetchone()["definition"]
        c.execute("ALTER TABLE sources DROP CONSTRAINT sources_entitlement_check")
        c.execute("UPDATE sources SET entitlement='restricted' WHERE id='finnhub-news'")
    try:
        with transaction(owner) as c:
            hidden = news_watch.list_alerts(c, owner)
        assert all(
            a["withheld"] and not a["payload"] and not a["sources"] for a in hidden
        )
        _, hidden_html = review_digest.download(owner)
        assert "Microsoft denies that the service will close." not in hidden_html
    finally:
        with transaction(admin=True) as c:
            c.execute(
                "UPDATE sources SET entitlement='finnhub-pitch' WHERE id='finnhub-news'"
            )
            c.execute(
                "ALTER TABLE sources ADD CONSTRAINT sources_entitlement_check " + definition
            )
    with transaction(owner) as c:
        restored = news_watch.list_alerts(c, owner)
    assert [a["payload"] for a in restored] == [a["payload"] for a in alerts]
    assert ledger.snapshot() == before


def test_opinion_only_repeat_guard_does_not_create_changed_reporting():
    earlier = source("item_1", "Microsoft may close the service.", 0)
    current = source("item_2", "Microsoft may close the service.", 1)
    before = analyse([earlier], [])
    after = analyse([current], [], comparisons=[earlier], tones={"item_2": "neutral"})
    after["result"]["coverage_links"] = [
        dict(
            source_id="item_2",
            reference_source_id="item_1",
            relation="repeats",
            repeat_suppression_allowed=False,
            review_note="Opinion or uncertain reporting remains separately reviewable.",
        )
    ]
    assert news_watch.changes(before, after) == []
