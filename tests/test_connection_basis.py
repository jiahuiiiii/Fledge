"""Delivery depends on an explicit source relationship, not a speculative bridge."""

import json
from copy import deepcopy
from pathlib import Path
import pytest
from thesis.db import transaction, one
from thesis.research import idea_alerts as A
from thesis.monitoring import news_watch
from thesis.providers import ledger
from test_idea_alerts import setup, provider, newer
from test_check_purpose import question_provider


def test_mixed_alert_keeps_possible_link_quiet_and_explicit_in_periodic_export(owner):
    from thesis import review_digest

    iid, _, reading = setup(owner, social=True)

    def change(items):
        assert len(items) > 1
        items[0].update(
            relation="supports",
            connection_basis="direct_evidence",
            missing_evidence=None,
        )
        items[1][
            "missing_evidence"
        ] = "A renewal report <script>not executable</script>"
        return items

    check = A.generate(
        owner, iid, reading["id"], transport=provider("possible_link", mutate=change)
    )
    with transaction(owner) as c:
        assert A.list_for(c, owner)[0]["noteworthy_count"] == 1
    report = review_digest.prepare(owner)
    assert report["total"] == 1
    _, html = review_digest.download(owner)
    assert "Possible connection (no alert)" in html
    assert "What would establish the link" in html
    assert "&lt;script&gt;" in html and "<script>" not in html


def test_possible_connection_is_private_quiet_history_with_a_specific_gap(owner):
    iid, _, reading = setup(owner)
    check = A.generate(owner, iid, reading["id"], transport=provider("possible_link"))
    before = ledger.snapshot()
    with transaction(owner) as c:
        shown = A.list_for(c, owner)[0]
        assert not one(
            c, "SELECT 1 FROM idea_alert_publications WHERE check_id=%s", (check["id"],)
        )
    assert not shown["published"] and shown["noteworthy_count"] == 0
    assert shown["possible_link_count"] == len(shown["items"])
    assert shown["items"][0]["missing_evidence"]
    html = A.download(owner, check["id"])[1]
    assert (
        "Possible connection (no alert)" in html
        and "What would establish the link" in html
    )
    assert (
        A.generate(
            owner,
            iid,
            reading["id"],
            transport=lambda _: pytest.fail("cached check dispatched twice"),
        )["id"]
        == check["id"]
    )
    assert ledger.snapshot() == before


@pytest.mark.parametrize("relation", ["supports", "challenges", "risk", "answers"])
@pytest.mark.parametrize("basis", ["direct_evidence", "source_argument"])
def test_direct_evidence_and_attributed_arguments_remain_alert_eligible(
    owner, relation, basis
):
    iid, _, reading = setup(owner)

    def change(items):
        for item in items:
            item["connection_basis"] = basis
        return items

    result = A.generate(
        owner, iid, reading["id"], transport=provider(relation, mutate=change)
    )
    with transaction(owner) as c:
        assert one(
            c,
            "SELECT 1 FROM idea_alert_publications WHERE check_id=%s",
            (result["id"],),
        )
        assert A.list_for(c, owner)[0]["noteworthy_count"] > 0


@pytest.mark.parametrize(
    "fault",
    [
        "missing_basis",
        "inferred_risk",
        "inferred_support",
        "inferred_challenge",
        "inferred_answer",
        "direct_possible",
        "no_gap",
        "empty_gap",
        "gap_for_alert",
        "no_anchor",
    ],
)
def test_invalid_relationship_cannot_publish(owner, fault):
    iid, _, reading = setup(owner)
    relation = (
        "possible_link"
        if fault in {"direct_possible", "no_gap", "empty_gap", "no_anchor"}
        else "risk"
    )

    def change(items):
        i = items[0]
        if fault == "missing_basis":
            i.pop("connection_basis")
        elif fault.startswith("inferred_"):
            i["relation"] = {
                "inferred_risk": "risk",
                "inferred_support": "supports",
                "inferred_challenge": "challenges",
                "inferred_answer": "answers",
            }[fault]
            i["connection_basis"] = "inferred_link"
        elif fault == "direct_possible":
            i["connection_basis"] = "direct_evidence"
        elif fault == "no_gap":
            i["missing_evidence"] = None
        elif fault == "empty_gap":
            i["missing_evidence"] = "       "
        elif fault == "gap_for_alert":
            i["missing_evidence"] = "An unstated link to customer churn."
        else:
            i.update(reasoning_segment_id=None, question_segment_id=None)
        return items

    with pytest.raises(ValueError):
        A.generate(
            owner, iid, reading["id"], transport=provider(relation, mutate=change)
        )
    with transaction(owner) as c:
        assert not one(c, "SELECT 1 FROM idea_alert_checks WHERE owner_id=%s", (owner,))


def test_quiet_possible_link_does_not_prevent_later_direct_evidence_alert(owner):
    iid, _, first = setup(owner)
    news_watch.configure(owner, iid, True, match_idea=True)
    second = newer(iid)
    quiet = A.generate(
        owner, iid, second["id"], automatic=True, transport=provider("possible_link")
    )
    with transaction(owner) as c:
        assert not one(
            c, "SELECT 1 FROM idea_alert_publications WHERE check_id=%s", (quiet["id"],)
        )
    assert (
        A.generate(
            owner,
            iid,
            second["id"],
            automatic=True,
            transport=lambda _: pytest.fail("seen lead repeated"),
        )["status"]
        == "no_new_sources"
    )
    from test_market import commit, news
    from test_sentiment import provider as classify
    from thesis.research import sentiment

    commit(
        iid,
        [
            news(
                id=81,
                url="https://example.test/later-margin-observation",
                headline="Microsoft reports higher margins",
                summary="Microsoft says operating margins increased this quarter.",
            )
        ],
    )
    later = sentiment.generate(iid, transport=classify("positive"))
    result = A.generate(
        owner, iid, later["id"], automatic=True, transport=provider("supports")
    )
    with transaction(owner) as c:
        assert one(
            c,
            "SELECT 1 FROM idea_alert_publications WHERE check_id=%s",
            (result["id"],),
        )


def test_question_route_does_not_accept_connection_basis_or_possible_links(owner):
    iid, _, reading = setup(owner)

    def change(items):
        items[0]["connection_basis"] = "inferred_link"
        return items

    with pytest.raises(ValueError):
        A.generate(
            owner,
            iid,
            reading["id"],
            purpose="question",
            transport=question_provider(mutate=change),
        )


def test_possible_connection_gap_is_escaped_and_source_withdrawal_withholds_it(owner):
    iid, _, reading = setup(owner)

    def change(items):
        items[0][
            "missing_evidence"
        ] = "Specific retention evidence <script>not executable</script>"
        return items

    check = A.generate(
        owner, iid, reading["id"], transport=provider("possible_link", mutate=change)
    )
    html = A.download(owner, check["id"])[1]
    assert "&lt;script&gt;" in html and "<script>" not in html
    with transaction(admin=True) as c:
        original_constraint = one(
            c,
            "SELECT pg_get_constraintdef(oid) AS definition FROM pg_constraint WHERE conrelid='sources'::regclass AND conname='sources_entitlement_check'",
        )["definition"]
        c.execute("ALTER TABLE sources DROP CONSTRAINT sources_entitlement_check")
        c.execute(
            "UPDATE sources SET entitlement='withdrawn' WHERE entitlement='finnhub-pitch'"
        )
    try:
        html = A.download(owner, check["id"])[1]
        assert "Specific retention evidence" not in html and "withheld" in html
    finally:
        with transaction(admin=True) as c:
            c.execute(
                "UPDATE sources SET entitlement='finnhub-pitch' WHERE entitlement='withdrawn'"
            )
            from psycopg import sql

            c.execute(
                sql.SQL(
                    "ALTER TABLE sources ADD CONSTRAINT sources_entitlement_check {}"
                ).format(sql.SQL(original_constraint))
            )
