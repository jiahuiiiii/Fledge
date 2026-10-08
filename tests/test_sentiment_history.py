"""Read-only source-sample comparison; all responses and cloned variants are authored."""

from copy import deepcopy
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from psycopg.types.json import Jsonb
from fastapi.testclient import TestClient
import pytest
from thesis.db import transaction, one
from thesis import service
from thesis.research import sentiment, sentiment_history as history
from thesis.providers import ledger
from test_market import prepare, commit, news
from test_sentiment import provider, add_social


def original(owner):
    iid = prepare(owner)
    add_social(iid)
    value = sentiment.generate(iid, transport=provider("neutral"))
    return iid, value


def variant(iid, identity, mutate=None, minutes=1):
    with transaction() as c:
        source = history.record(c, iid, identity)
    packet, result = deepcopy(source["packet"]), deepcopy(source["result"])
    packet["cutoff"] = (
        datetime.fromisoformat(packet["cutoff"]) + timedelta(minutes=minutes)
    ).isoformat()
    if mutate:
        mutate(packet, result)
    identity = str(uuid4())
    with transaction() as c:
        c.execute(
            "INSERT INTO sentiment_analyses VALUES(%s,%s,%s,%s,%s,%s,%s)",
            (
                identity,
                iid,
                "authored-history-variant:" + identity,
                source["call_id"],
                Jsonb(packet),
                Jsonb(result),
                source["created_at"] + timedelta(minutes=minutes),
            ),
        )
    return identity


def test_history_and_comparison_are_readonly_and_cache_does_not_add_samples(owner):
    iid, first = original(owner)
    assert (
        sentiment.generate(iid, transport=lambda _: pytest.fail("paid repeat"))["id"]
        == first["id"]
    )
    second = variant(iid, first["id"])
    budget = ledger.snapshot()
    listing = history.history(iid)
    assert [s["id"] for s in listing["items"]] == [second, first["id"]]
    compared = history.compare(iid, first["id"], second)
    assert compared["same_selected_text"] and not compared["method_changed"]
    assert compared["channels"]["news"]["counts"] == dict(
        added=0, removed=0, relabeled=0, unchanged=1
    )
    assert compared["channels"]["social"]["counts"]["unchanged"] == 1
    assert ledger.snapshot() == budget


def test_new_report_and_changed_labels_are_separate(owner):
    iid, first = original(owner)
    commit(
        iid,
        [
            news(
                id=2,
                url="https://example.test/new",
                headline="Microsoft reports margin decline",
                summary="Microsoft reported lower margins.",
            )
        ],
    )
    second = sentiment.generate(iid, transport=provider("negative"))
    compared = history.compare(iid, first["id"], second["id"])
    assert compared["channels"]["news"]["counts"] == dict(
        added=1, removed=0, relabeled=1, unchanged=0
    )
    assert compared["channels"]["social"]["counts"]["relabeled"] == 1
    assert not compared["same_selected_text"]
    relabeled = next(
        i for i in compared["channels"]["news"]["items"] if i["change"] == "relabeled"
    )
    assert (
        relabeled["before"]["item"]["sentiment"] == "neutral"
        and relabeled["after"]["item"]["sentiment"] == "negative"
    )


def test_selection_limit_removes_text_without_claiming_retraction(owner):
    iid, first = original(owner)
    commit(
        iid,
        [
            news(
                id=n + 2,
                url=f"https://example.test/new-{n}",
                headline=f"Microsoft update number {n}",
                summary=f"Authored Microsoft report number {n}.",
                datetime=int(datetime.now(timezone.utc).timestamp()) - 1,
            )
            for n in range(8)
        ],
    )
    second = sentiment.generate(iid, transport=provider("neutral"))
    change = history.compare(iid, first["id"], second["id"])["channels"]["news"]
    assert change["counts"]["removed"] == 1 and change["counts"]["added"] == 8
    old = next(v for v in change["items"] if v["change"] == "removed")
    assert (
        old["after"] is None
        and old["before"]["item"]["source_id"] == first["items"][0]["source_id"]
    )


def test_method_change_and_same_text_reanalysis_are_explicit(owner):
    iid, first = original(owner)

    def change(p, r):
        r["prompt_version"] = "authored-other-method"
        r["summary_policy"] = "authored-other-counts"
        r["items"][0]["sentiment"] = "positive"

    second = variant(iid, first["id"], change)
    compared = history.compare(iid, first["id"], second)
    assert compared["method_changed"] and compared["same_selected_text"]
    assert compared["channels"]["news"]["counts"]["relabeled"] == 1
    assert history.history(iid)["items"][0]["earlier_method"]


def test_explanation_rewording_is_not_a_label_change(owner):
    iid, first = original(owner)
    second = variant(
        iid,
        first["id"],
        lambda p, r: r["items"][0].update(
            explanation="Different wording, same authored classification."
        ),
    )
    compared = history.compare(iid, first["id"], second)
    assert compared["channels"]["news"]["counts"]["unchanged"] == 1


def test_comparison_only_context_is_not_counted_as_new_selected_evidence(owner):
    iid, first = original(owner)

    def change(p, r):
        p["comparison_sources"] = [deepcopy(p["sources"][0])]

    second = variant(iid, first["id"], change)
    compared = history.compare(iid, first["id"], second)
    assert compared["comparison_context_changed"] and compared["same_selected_text"]
    assert compared["channels"]["news"]["counts"]["added"] == 0


def test_source_withdrawal_withholds_history_counts_and_both_comparison_sides(owner):
    iid, first = original(owner)
    second = variant(iid, first["id"])
    with transaction(admin=True) as c:
        c.execute("UPDATE social_feeds SET enabled=false")
    try:
        assert all(
            s["withheld"] and "summary" not in s and "coverage" not in s
            for s in history.history(iid)["items"]
        )
        c = history.compare(iid, first["id"], second)
        assert (
            c["withheld"]
            and c["channels"] == {}
            and "before" not in c
            and "after" not in c
        )
    finally:
        with transaction(admin=True) as c:
            c.execute("UPDATE social_feeds SET enabled=true")


def test_equal_reversed_and_foreign_sample_identities_rejected(owner):
    iid, first = original(owner)
    second = variant(iid, first["id"])
    for a, b in [(first["id"], first["id"]), (second, first["id"])]:
        with pytest.raises(ValueError):
            history.compare(iid, a, b)
    with pytest.raises(service.Missing):
        history.compare(str(uuid4()), first["id"], second)
    with pytest.raises(service.Missing):
        history.history(iid, str(uuid4()))


def test_pagination_preserves_all_tied_cutoffs_without_duplicates(owner):
    iid, first = original(owner)
    identities = {first["id"]}
    for _ in range(22):
        identities.add(variant(iid, first["id"], minutes=0))
    page = history.history(iid)
    rest = history.history(iid, page["next_cursor"])
    assert (
        len(page["items"]) == 20
        and len(rest["items"]) == 3
        and rest["next_cursor"] is None
    )
    got = [s["id"] for s in page["items"] + rest["items"]]
    assert len(got) == len(set(got)) and set(got) == identities


def test_sample_identity_includes_headline_not_only_copied_body(owner):
    iid, first = original(owner)
    commit(iid, [news(headline="Microsoft has now confirmed the reported contract.")])
    second = sentiment.generate(iid, transport=provider("neutral"))
    delta = history.compare(iid, first["id"], second["id"])["channels"]["news"][
        "counts"
    ]
    assert delta["added"] == 1 and delta["removed"] == 1 and delta["unchanged"] == 0


def test_api_session_company_scope_and_no_paid_or_watch_mutations(owner):
    from thesis.app import app

    iid, first = original(owner)
    second = variant(iid, first["id"])
    client = TestClient(app)
    url = f"/api/v1/companies/{iid}/sentiment-history"
    assert client.get(url).status_code == 401
    client.get("/api/v1/session")
    budget = ledger.snapshot()
    assert client.get(url).status_code == 200
    assert (
        client.get(
            f"/api/v1/companies/{iid}/sentiment-comparison",
            params=dict(before=first["id"], after=second),
        ).status_code
        == 200
    )
    assert client.get(url, params={"before": "bad-uuid"}).status_code == 422
    with transaction() as c:
        assert not one(c, "SELECT * FROM news_watches")
    assert ledger.snapshot() == budget
