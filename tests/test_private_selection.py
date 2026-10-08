"""Original-sample private matching, with no provider requests."""

from copy import deepcopy
import hashlib
import json
import pytest
from thesis.db import transaction, one
from thesis import review_digest
from thesis.providers import ledger
from thesis.research import idea_alerts as A, sentiment as S
from thesis.monitoring import news_watch
from test_idea_alerts import setup, provider, newer
from test_sentiment import provider as classifier


def source(n, channel="news", **changes):
    return dict(
        id=str(n),
        content_hash=str(n),
        channel=channel,
        title="Microsoft source",
        text="Original available source text.",
        **changes
    )


def analysis(sources, relevance="unrelated"):
    return dict(
        packet=dict(sources=sources),
        result=dict(
            items=[dict(source_id=s["id"], relevance=relevance) for s in sources],
            coverage_links=[],
        ),
    )


@pytest.mark.parametrize("label", ["relevant", "unrelated", "unclear"])
def test_shared_classification_does_not_gate_private_sources(label):
    a = analysis([source(1), source(2, "social", platform="reddit")], label)
    selected = A.select_sources(a)
    assert selected["sources"] == a["packet"]["sources"]
    assert (
        selected["eligible_source_count"] == 2
        and selected["unusable_source_count"] == 0
    )
    # No shared classifications in this stage's selected packet.
    assert "relevance" not in json.dumps(selected)


def test_original_text_required_but_meaningful_headline_is_allowed():
    sources = [
        source(1, "social", platform="hackernews"),
        source(2),
        source(3, "social", platform="reddit"),
        source(4),
    ]
    sources[0].update(title="Hacker News comment", text="A cut-off...")
    sources[1].update(title="Microsoft announces a product", text="A cut-off...")
    sources[2].update(title="What happened at Microsoft?", text="")
    sources[3].update(title="A cut-off...", text="Another...")
    selected = A.select_sources(analysis(sources))
    assert {s["id"] for s in selected["sources"]} == {"2", "3"}
    assert (
        selected["eligible_source_count"],
        selected["sample_source_count"],
        selected["unusable_source_count"],
    ) == (2, 4, 2)
    # Removing ellipsis alone isn't enough: HN's generic title cannot become evidence.
    sources[0]["text"] = ""
    assert "1" not in {s["id"] for s in A.select_sources(analysis(sources))["sources"]}


def test_same_bounds_channel_balance_and_exact_seen_keys():
    sources = [source(n) for n in range(20)] + [
        source(n, "social", platform="reddit") for n in range(20, 40)
    ]
    sources.insert(1, deepcopy(sources[0]) | {"id": "duplicate"})
    selected = A.select_sources(
        analysis(sources), {("news", "content:2"), ("social", "content:21")}
    )
    assert len(selected["sources"]) == 16 and selected["pending_source_count"] == 22
    assert [s["channel"] for s in selected["sources"]] == ["news", "social"] * 8
    assert len({(s["channel"], s["content_hash"]) for s in selected["sources"]}) == 16
    assert not {"2", "21", "duplicate"} & {s["id"] for s in selected["sources"]}


def test_legacy_request_identity_preserved_new_selection_cannot_mislabel_cached_output(
    owner,
):
    iid, _, reading = setup(owner)
    with transaction(owner) as c:
        packet, _ = A.prepare(c, owner, iid, reading["id"])
    old = {
        k: v
        for k, v in packet.items()
        if k not in ("selection_policy", "unusable_source_count")
    }
    expected = (
        "private-idea-alert:"
        + owner
        + ":"
        + hashlib.sha256(
            (A.PROMPT + ledger.canonical(A.request_for(old))).encode()
        ).hexdigest()
    )
    assert A.identity(owner, old) == expected
    assert A.request_for(packet) == A.request_for(old)
    assert A.identity(owner, packet) != expected


@pytest.mark.parametrize("label", ["unrelated", "unclear"])
def test_production_prepare_includes_originals_even_when_entire_shared_result_excludes_them(
    owner, monkeypatch, label
):
    iid, _, _ = setup(owner, True)

    def relabel(items):
        for i in items:
            i.update(relevance=label, sentiment="unclear", basis="unclear")
        return items

    # Separate immutable shared result; never mutate an existing analysis.
    with monkeypatch.context() as m:
        m.setattr(S, "PROMPT", "authored-selection-control-" + label)
        reading = S.generate(iid, transport=classifier(mutate=relabel))
    assert all(i["relevance"] == label for i in reading["items"])
    result = A.generate(owner, iid, reading["id"], transport=provider("context"))
    with transaction(owner) as c:
        record = A.list_for(c, owner)[0]
    assert record["checked_source_count"] == 2 and not record["published"]
    assert "relevance labels did not filter" in record["selection_summary"]
    assert "relevance labels did not filter" in A.download(owner, result["id"])[1]


def test_policy_change_and_reclassification_do_not_realert_watch_baseline(
    owner, monkeypatch
):
    iid, _, reading = setup(owner, True)
    news_watch.configure(owner, iid, True, match_idea=True)

    def relabel(items):
        for i in items:
            i.update(relevance="unrelated", sentiment="unclear", basis="unclear")
        return items

    with monkeypatch.context() as m:
        m.setattr(S, "PROMPT", "authored-new-shared-method")
        changed = S.generate(iid, transport=classifier(mutate=relabel))
    assert changed["id"] != reading["id"]
    before = ledger.snapshot()
    assert (
        A.generate(
            owner,
            iid,
            changed["id"],
            automatic=True,
            transport=lambda _: pytest.fail("Baseline reprocessed"),
        )["status"]
        == "no_new_sources"
    )
    assert ledger.snapshot() == before
    # Subsequent genuinely new source still receives one private check.
    fresh = newer(iid)
    result = A.generate(
        owner,
        iid,
        fresh["id"],
        automatic=True,
        transport=provider(
            "answers",
            answer_anchor="question",
            mutate=lambda items: [
                i | {"reasoning_segment_id": None, "question_segment_id": "q0"}
                for i in items
            ],
        ),
    )
    with transaction(owner) as c:
        record = A.list_for(c, owner)[0]
    assert (
        result["status"] == "checked"
        and record["published"]
        and record["checked_source_count"] == 1
    )


def test_legacy_record_and_export_retain_original_selection_meaning(owner, monkeypatch):
    iid, _, reading = setup(owner)
    original = A.prepare

    def legacy(*args, **kwargs):
        packet, status = original(*args, **kwargs)
        if packet:
            packet.pop("selection_policy")
            packet.pop("unusable_source_count")
        return packet, status

    with monkeypatch.context() as m:
        m.setattr(A, "prepare", legacy)
        result = A.generate(owner, iid, reading["id"], transport=provider())
    with transaction(owner) as c:
        before = one(c, "SELECT * FROM idea_alert_checks WHERE id=%s", (result["id"],))
        record = A.present(c, owner, before)
        after = one(c, "SELECT * FROM idea_alert_checks WHERE id=%s", (result["id"],))
    assert before == after
    assert record["selection_policy"] == A.LEGACY_SELECTION_POLICY
    assert (
        "company-related items" in record["selection_summary"]
        and "earlier selection" in record["selection_summary"]
    )
    assert "relevance labels did not filter" not in record["selection_summary"]
    assert "earlier selection" in A.download(owner, result["id"])[1]
    assert "earlier selection" in review_digest.download(owner, days=0)[1]


def test_new_shared_unrelated_source_can_create_one_private_watch_update(
    owner, monkeypatch
):
    iid, _, _ = setup(owner)
    news_watch.configure(owner, iid, True, match_idea=True)
    newer(iid)

    def relabel(items):
        return [
            i | {"relevance": "unrelated", "sentiment": "unclear", "basis": "unclear"}
            for i in items
        ]

    with monkeypatch.context() as m:
        m.setattr(S, "PROMPT", "authored-unrelated-new-source")
        changed = S.generate(iid, transport=classifier(mutate=relabel))
    checked = A.generate(
        owner, iid, changed["id"], automatic=True, transport=provider("risk")
    )
    with transaction(owner) as c:
        record = A.list_for(c, owner)[0]
    assert (
        checked["status"] == "checked"
        and record["published"]
        and record["delivery_mode"] == "watch"
    )
    assert record["checked_source_count"] == 1
    before = ledger.snapshot()
    assert (
        A.generate(
            owner,
            iid,
            changed["id"],
            automatic=True,
            transport=lambda _: pytest.fail("Duplicate delivery"),
        )["status"]
        == "no_new_sources"
    )
    assert ledger.snapshot() == before


def test_retained_actual_sample_recovers_question_evidence_without_hn_placeholder():
    import os
    from pathlib import Path

    path = os.environ.get("THESIS_PRIVATE_SELECTION_CORPUS")
    if not path:
        pytest.skip("Retained actual selection corpus not configured; no fetching")
    frozen = json.loads((Path(path) / "frozen.json").read_text())
    selected = A.select_sources(frozen["analysis"])
    recovered = set(s["id"] for s in selected["sources"]) - set(
        frozen["old_related_ids"]
    )
    assert recovered == {"bdeb3a26-c31c-526c-889f-ad184d432ce1"}
    assert (
        selected["sample_source_count"] == 16
        and selected["eligible_source_count"] == 15
        and selected["unusable_source_count"] == 1
    )
    comment = next(s for s in selected["sources"] if s["id"] in recovered)
    assert (
        "classified 570 review comments" in comment["text"]
        and "Only 14%" in comment["text"]
    )
    assert selected == {
        k: frozen["cases"]["MSFT-study-measures"]["packet"][k] for k in selected
    }
    # Current sampling must not turn the policy change into new watch evidence.
    seen = {
        (s["channel"], "content:" + s["content_hash"])
        for s in frozen["analysis"]["packet"]["sources"]
    }
    assert A.select_sources(frozen["analysis"], seen)["sources"] == []
