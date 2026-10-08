"""Actual retained news/posts and paid labels; authored arrivals/faults only."""

from copy import deepcopy
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
from thesis import service, review_digest
from thesis.models import SaveIdea
from thesis.db import transaction, one
from thesis.providers import ledger
from thesis.monitoring import news_watch
from thesis.research import sentiment_history
from retained_watch_replay import Replay

pytestmark = pytest.mark.skipif(
    not os.environ.get("THESIS_WATCH_REPLAY_CORPUS"),
    reason="Optional retained alert replay corpus; never fetch sources",
)


def save_reasoning(replay, revision=0):
    return service.save_idea(
        replay.owner,
        SaveIdea(
            instrument_id=replay.iid,
            expected_revision=revision,
            question="Which reported legal developments need further investigation?",
            reasoning=f"Authored replay reasoning, revision {revision + 1}. I want to inspect original legal reporting before judging its implications.",
            status="draft",
            conditions=[],
        ),
    )


def test_real_labels_survive_new_repeat_gap_failure_stop_recovery_and_review(owner):
    replay = Replay(owner)
    save_reasoning(replay)
    # Same two retained texts establish the baseline and later sample gap.
    baseline = replay.append(["item_7", "item_13"], 0)
    replay.start()
    assert replay.run(baseline, 0)["alert_count"] == 0
    changed = replay.append(["item_7", "item_13", "item_6"], 1)
    assert replay.run(changed, 1)["alert_count"] == 1
    first = replay.alerts()[0]
    assert [i["id"] for i in first["payload"]["items"]] == ["item_6"]
    assert "-1.7%" in json.dumps(first["payload"])
    first_immutable = deepcopy(first["payload"])
    news_watch.review(owner, first["id"], "reviewed")
    assert replay.run(changed, 2)["alert_count"] == 0
    gap = replay.append(["item_7", "item_13"], 3)
    assert replay.run(gap, 3)["alert_count"] == 0
    back = replay.append(["item_7", "item_13", "item_6"], 4)
    assert replay.run(back, 4)["alert_count"] == 0
    assert ledger.snapshot() == replay.initial_budget
    with transaction(owner) as c:
        before_state = one(
            c, "SELECT baseline_id FROM news_watches WHERE owner_id=%s", (owner,)
        )
    later = replay.append(["item_7", "item_13", "item_6", "item_8"], 5)

    def fail(_):
        raise ValueError("Authored source interruption")

    failed = replay.run(later, 5, refresh=fail)
    assert failed["status"] == "failed" and failed["details"]["analysis"] == "not_run"
    with transaction(owner) as c:
        assert (
            one(c, "SELECT baseline_id FROM news_watches WHERE owner_id=%s", (owner,))
            == before_state
        )

    def stop(_):
        news_watch.configure(owner, replay.iid, False)
        return {"id": str(later["id"])}

    stopped = replay.run(later, 6, analyzer=stop)
    assert stopped["status"] == "stopped" and stopped["alert_count"] == 0
    assert len(replay.alerts()) == 1
    save_reasoning(replay, 1)
    replay.start(7)
    recovered = replay.run(later, 7)
    assert recovered["alert_count"] == 1
    alerts = replay.alerts()
    assert len(alerts) == 2
    second = next(a for a in alerts if a["id"] != first["id"])
    assert [i["id"] for i in second["payload"]["items"]] == ["item_8"]
    assert "$3.2" in json.dumps(second["payload"])
    assert (
        second["review_action"] is None
        and second["payload"]["saved_idea"]["revision"] == 2
    )
    original = next(a for a in alerts if a["id"] == first["id"])
    assert (
        original["review_action"] == "reviewed"
        and original["payload"] == first_immutable
    )
    assert replay.run(later, 8)["alert_count"] == 0
    assert replay.run(changed, 9)["alert_count"] == 0
    with transaction(owner) as c:
        assert str(
            one(c, "SELECT baseline_id FROM news_watches WHERE owner_id=%s", (owner,))[
                "baseline_id"
            ]
        ) == str(later["id"])
    assert ledger.snapshot() == replay.initial_budget
    comparison = sentiment_history.compare(replay.iid, baseline["id"], later["id"])
    assert comparison["channels"]["news"]["counts"] == dict(
        added=2, removed=0, relabeled=0, unchanged=1
    )
    html = review_digest.download(owner)[1]
    assert "-1.7%" in html and "$3.2" in html
    other = str(uuid4())
    with transaction(other) as c:
        assert news_watch.list_alerts(c, other) == []
    feed = next(
        p["feed"]
        for p in replay.case["tables"]["social_posts"]
        if p["id"]
        == next(
            s["id"] for s in replay.case["packet"]["sources"] if s["label"] == "item_13"
        )
    )
    with transaction(admin=True) as c:
        c.execute("UPDATE social_feeds SET enabled=false WHERE feed=%s", (feed,))
    assert all(a["withheld"] and not a["payload"] for a in replay.alerts())
    assert "$3.2" not in review_digest.download(owner)[1]
    with transaction(admin=True) as c:
        c.execute("UPDATE social_feeds SET enabled=true WHERE feed=%s", (feed,))
    assert [a["payload"] for a in replay.alerts()] == [a["payload"] for a in alerts]
    assert ledger.snapshot() == replay.initial_budget
    news_watch.configure(owner, replay.iid, False)
    if report := os.environ.get("THESIS_WATCH_REPLAY_REPORT"):
        Path(report).write_text(
            json.dumps(
                dict(
                    company="GOOGL",
                    steps=10,
                    publications=2,
                    source_fields_unchanged=True,
                    labels_unchanged=True,
                    repeat_gap_recovery_quiet=True,
                    review_preserved=True,
                    source_withdrawal_restoration=True,
                    paid_requests=0,
                    source_requests=0,
                    prospective=False,
                ),
                indent=2,
            )
        )


def test_real_apple_same_time_duplicate_counts_and_same_sample_resume_stay_quiet(owner):
    replay = Replay(owner, "AAPL")
    baseline = replay.append(["item_3", "item_4", "item_9"], 0)
    assert baseline["result"]["summary"]["news"]["counted_groups"] == 1
    replay.start()
    assert replay.run(baseline, 0)["alert_count"] == 0
    news_watch.configure(owner, replay.iid, False)
    replay.start(1)
    assert replay.run(baseline, 1)["alert_count"] == 0
    assert not replay.alerts() and ledger.snapshot() == replay.initial_budget
    news_watch.configure(owner, replay.iid, False)


def test_private_failure_retains_unseen_work_after_company_baseline_advances(owner):
    from thesis.research import idea_alerts as A
    from test_check_purpose import question_provider

    replay = Replay(owner)
    save_reasoning(replay)
    baseline = replay.append(["item_7", "item_13"], 0)
    replay.start(match_idea=True, idea_purpose="question")
    assert replay.run(baseline, 0)["alert_count"] == 0
    later = replay.append(["item_7", "item_13", "item_8"], 1)

    def failure(*args, **kwargs):
        raise ValueError("Authored stop before private model dispatch")

    failed = replay.run(later, 1, idea_analyzer=failure)
    assert failed["status"] == "failed" and not failed["alert_count"]
    with transaction(owner) as c:
        assert (
            one(c, "SELECT baseline_id FROM news_watches WHERE owner_id=%s", (owner,))[
                "baseline_id"
            ]
            == later["id"]
        )
        assert (
            one(
                c,
                "SELECT baseline_id FROM idea_watch_state WHERE owner_id=%s",
                (owner,),
            )["baseline_id"]
            == baseline["id"]
        )
    seen_packets = []

    def checked(*args, **kwargs):
        with transaction(owner) as c:
            packet, status = A.prepare(
                c,
                owner,
                replay.iid,
                later["id"],
                automatic=True,
                token=kwargs["claim_token"],
            )
        assert packet and not status and len(packet["sources"]) == 1
        assert packet["sources"][0]["label"] == "item_8"
        seen_packets.append(packet)
        if path := os.environ.get("THESIS_WATCH_PRIVATE_PACKET"):
            Path(path).write_text(
                json.dumps(
                    dict(
                        packet=packet,
                        request=A.request_for(packet),
                        method=A.method_for(packet),
                        expected_relation="answers",
                        source_kind="retained Alphabet legal report; authored question and replay arrivals",
                    ),
                    indent=2,
                    default=str,
                )
            )
        response_path = os.environ.get("THESIS_WATCH_PRIVATE_RESPONSE")
        if response_path:
            frozen = json.loads(Path(response_path).read_text())

            # Identifier and replay clock metadata are authored; the question,
            # original source text/schema/instructions must match the live check.
            def semantic(body):
                body = deepcopy(body)
                wire = json.loads(body["input"][1]["content"])
                wire.pop("version_id")
                wire.pop("cutoff")
                body["input"][1]["content"] = json.dumps(wire, sort_keys=True)
                return body

            assert semantic(A.request_for(packet)) == semantic(frozen["request"])
            transport = lambda _: deepcopy(frozen["call"]["response_body"])
        else:
            transport = question_provider("answers")
        return A.generate(*args, **kwargs, transport=transport)

    recovered = replay.run(later, 2, idea_analyzer=checked)
    assert recovered["status"] == "completed" and recovered["alert_count"] == 1
    with transaction(owner) as c:
        check = A.list_for(c, owner)[0]
        assert check["published"] and check["delivery_mode"] == "watch"
        assert check["items"][0]["relation"] == "answers"
        assert len(check["items"]) == 1 and not news_watch.list_alerts(c, owner)
        assert (
            one(
                c,
                "SELECT baseline_id FROM idea_watch_state WHERE owner_id=%s",
                (owner,),
            )["baseline_id"]
            == later["id"]
        )
    settled = ledger.snapshot()
    repeated = replay.run(
        later,
        3,
        idea_analyzer=lambda *a, **kw: A.generate(
            *a, **kw, transport=lambda _: pytest.fail("Repeated paid private check")
        ),
    )
    assert (
        repeated["alert_count"] == 0
        and repeated["details"]["idea_status"] == "no_new_sources"
    )
    assert ledger.snapshot() == settled and len(seen_packets) == 1
    A.review(owner, check["id"], "unresolved")
    assert "$3.2" in A.download(owner, check["id"])[1]
    news_watch.configure(owner, replay.iid, False)
