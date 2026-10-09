"""Complete-source selection fits the paid request before any dispatch."""

from copy import deepcopy
import json
import os
from pathlib import Path

import pytest

from thesis.db import one, transaction
from thesis.providers import ledger
from thesis.research import sentiment as S, sentiment_inputs
from thesis.research.sentiment_limits import fit
from test_market import prepare
from test_news_coverage import source
from test_sentiment import add_social, provider


def packet():
    sources = []
    for n in range(8):
        channel = "news" if n < 4 else "social"
        item = source(f"item_{n+1}", ("Complete passage. " * 35) + str(n), n, channel)
        if channel == "social":
            item["platform"] = "reddit" if n % 2 else "hackernews"
        sources.append(item)
    return dict(
        company={"name": "Microsoft", "symbol": "MSFT"},
        sources=sources,
        comparison_sources=[
            source(f"prior_{i}", "Earlier report. " * 70, i) for i in range(6)
        ],
        omitted_fragment_count=0,
    )


def size(value):
    return len(ledger.canonical(S.request_for(value)).encode())


def test_fitting_request_is_identical_and_keeps_the_same_paid_identity():
    p = packet()
    p['comparison_sources']=p['comparison_sources'][:3]
    assert size(p) <= ledger.MAX_REQUEST_BYTES
    before = deepcopy(p)
    assert fit(p, S.request_for) is p
    assert p == before
    assert S.model_identity(p) == S.model_identity(before)


def test_comparisons_drop_first_as_complete_ranked_prefix_without_mutation():
    p = packet()
    before = deepcopy(p)
    target = dict(p, comparison_sources=p["comparison_sources"][:3])
    q = fit(p, S.request_for, max_bytes=size(target))
    assert p == before and q["sources"] == p["sources"]
    assert q["comparison_sources"] == target["comparison_sources"]
    assert q["input_limits"]["omitted_comparisons"] == 3
    assert q["input_limits"]["omitted_sources"] == {}
    assert size(q) == size(target)
    assert fit(q, S.request_for, max_bytes=size(target)) is q


def test_full_originals_and_parents_stay_intact_when_originals_need_reduction():
    from thesis.research.citations import source_passages

    p = packet()
    child = p["sources"][4]
    # The wire parent shape is verified by the existing context tests.
    child["conversation"] = dict(
        parent_key="hn:10",
        parent_type="story",
        title="Microsoft product",
        body="",
        published_at="2026-10-01T00:00:00+00:00",
        checked_at="2026-10-01T01:00:00+00:00",
        same_author=False,
        passages=source_passages("Microsoft product", "")[0],
    )
    target = dict(p, comparison_sources=[], sources=p["sources"][:6])
    q = fit(p, S.request_for, max_bytes=size(target))
    assert not q["comparison_sources"] and len(q["sources"]) < len(p["sources"])
    assert size(q) <= size(target)
    assert {v["channel"] for v in q["sources"]} == {"news", "social"}
    for selected in q["sources"]:
        assert selected == next(v for v in p["sources"] if v["id"] == selected["id"])
    for platform in ("reddit", "hackernews"):
        assert any(v.get("platform") == platform for v in q["sources"])
    assert "not shortened" in q["input_limits"]["notice"]


def test_bytes_include_unicode_schema_and_publisher_metadata():
    p = packet()
    for s in p["sources"]:
        s["publisher"] = "例" * 180
    n = size(dict(p, comparison_sources=[]))
    q = fit(p, S.request_for, max_bytes=n)
    assert size(q) == n
    assert q["sources"] == p["sources"] and not q["comparison_sources"]


def test_no_complete_source_can_fit_yields_empty_preview_not_invalid_request():
    p = packet()
    q = fit(p, S.request_for, max_bytes=1)
    assert not q["sources"] and not q["comparison_sources"]
    assert q["input_limits"]["request_bytes"] is None
    assert sum(q["input_limits"]["omitted_sources"].values()) == 8
    assert fit(q, S.request_for, max_bytes=1) is q


def test_empty_preview_does_not_construct_model_schema():
    p = dict(sources=[])
    assert fit(p, lambda _: pytest.fail("empty model request")) is p


def test_preflight_preview_generation_history_and_access_share_limits(
    owner, monkeypatch
):
    from thesis.research import sentiment_history

    iid = prepare(owner)
    add_social(iid)
    with transaction() as c:
        original = S.prepare(c, iid)
    monkeypatch.setattr(ledger, "MAX_REQUEST_BYTES", size(original) - 1)
    before = ledger.snapshot()
    with transaction() as c:
        p = S.prepare(c, iid)
        visible = sentiment_inputs.current(c, iid)
    assert len(p["sources"]) == 2
    from thesis.research.sentiment_batching import plan
    assert sum(len(part['sources']) for part in plan(p)) == 2
    assert visible["selection"] == p["selection"]
    assert [s["id"] for s in visible["sources"]] == [s["id"] for s in p["sources"]]
    assert ledger.snapshot() == before
    result = S.generate(iid, transport=provider())
    assert result["coverage"]["selection"] == p["selection"]
    assert (
        sentiment_history.history(iid)["items"][0]["coverage"]["selection"]
        == p["selection"]
    )
    settled = ledger.snapshot()
    assert (
        S.generate(iid, transport=lambda _: pytest.fail("repeated paid call"))["id"]
        == result["id"]
    )
    assert ledger.snapshot() == settled
    # Access withdrawal must not expose the new coverage metadata.
    with transaction() as c:
        record = one(c, "SELECT * FROM sentiment_analyses WHERE id=%s", (result["id"],))
        monkeypatch.setattr(S, "permitted_ids", lambda *_: set())
        withdrawn = S.present(c, record)
        assert withdrawn["withheld"] and "coverage" not in withdrawn


def test_unfittable_generation_stops_before_paid_reservation(owner, monkeypatch):
    iid = prepare(owner)
    monkeypatch.setattr(ledger, "MAX_REQUEST_BYTES", 1)
    before = ledger.snapshot()
    with transaction() as c:
        preview = sentiment_inputs.current(c, iid)
    assert preview["status"] == "no_saved_reading" and preview["sources"]
    with pytest.raises(ValueError, match="No batch was sent"):
        S.generate(iid, transport=lambda _: pytest.fail("paid request"))
    assert ledger.snapshot() == before


def test_actual_alphabet_packet_fits_without_losing_any_selected_original():
    corpus = os.environ.get("THESIS_INPUT_LIMIT_CORPUS")
    if not corpus:
        pytest.skip("Optional retained company-relevance corpus")
    frozen = json.loads((Path(corpus) / "frozen.json").read_text())
    p = frozen["cases"]["GOOGL"]["unfitted_packet"]
    assert size(p) > ledger.MAX_REQUEST_BYTES
    q = fit(p, S.request_for)
    assert q["sources"] == p["sources"]
    assert len(q["sources"]) == 16 and len(q["comparison_sources"]) == 3
    assert size(q) == 63197
    ledger.estimate(S.request_for(q))


def test_alert_and_export_retain_limits_but_withdraw_them_with_evidence(
    owner, monkeypatch
):
    from uuid import uuid4
    from psycopg.types.json import Jsonb
    from thesis.monitoring import news_watch
    from thesis import review_digest

    iid = prepare(owner)
    add_social(iid)
    earlier = S.generate(iid, transport=provider())
    with transaction() as c:
        p = S.prepare(c, iid)
    # Historical limited packets and their notices remain readable/exportable.
    limited = fit(p, S.request_for, max_bytes=size(p) - 1)
    monkeypatch.setattr(S, "prepare", lambda *_a, **_k: limited)
    current = S.generate(iid, transport=provider())
    assert current["id"] != earlier["id"]
    expected = current["coverage"]["input_limits"]
    with transaction(owner) as c:
        c.execute(
            "INSERT INTO research_alerts VALUES(%s,%s,%s,'sentiment',%s,%s,NULL,%s,now())",
            (
                uuid4(),
                owner,
                iid,
                current["id"],
                earlier["id"],
                Jsonb(
                    dict(reason="Authored limit display check.", items=current["items"])
                ),
            ),
        )
        shown = news_watch.list_alerts(c, owner)[0]
    assert shown["source_limits"] == dict(previous=None, current=expected)
    before = ledger.snapshot()
    assert expected["notice"] in review_digest.download(owner)[1]
    monkeypatch.setattr(S, "permitted_ids", lambda *_: set())
    with transaction(owner) as c:
        withdrawn = news_watch.list_alerts(c, owner)[0]
    assert withdrawn["withheld"] and not withdrawn["source_limits"]
    assert expected["notice"] not in review_digest.download(owner)[1]
    assert ledger.snapshot() == before


def test_link_schema_uses_timestamp_and_storage_id_not_label_order():
    p = packet()
    p["sources"] = [
        source("item_1", "Current report", 1),
        source("item_2", "Same-time report", 1),
    ]
    p["sources"][0]["id"] = "z-storage-id"
    p["sources"][1]["id"] = "a-storage-id"
    p["comparison_sources"] = []
    links = S.request_for(p)["text"]["format"]["schema"]["properties"]["coverage_links"]
    branches = links["items"]["anyOf"]
    assert len(branches) == 1
    assert branches[0]["properties"]["item_id"]["enum"] == ["item_1"]
    assert branches[0]["properties"]["reference_id"]["enum"] == ["item_2"]
    p["sources"] = p["sources"][:1]
    assert (
        S.request_for(p)["text"]["format"]["schema"]["properties"]["coverage_links"][
            "maxItems"
        ]
        == 0
    )


def test_retained_rejected_apple_link_is_impossible_in_new_request_schema():
    corpus = os.environ.get("THESIS_INPUT_LIMIT_CORPUS")
    if not corpus:
        pytest.skip("Optional retained company-relevance corpus")
    path = Path(corpus)
    case = json.loads((path / "frozen.json").read_text())["cases"]["AAPL"]
    call = json.loads((path / "AAPL-call.json").read_text())
    raw = json.loads(
        next(
            c["text"]
            for o in call["response_body"]["output"]
            if o["type"] == "message"
            for c in o["content"]
            if c["type"] == "output_text"
        )
    )
    rejected = raw["coverage_links"][0]
    assert (rejected["item_id"], rejected["reference_id"]) == ("item_4", "item_3")
    schema = S.request_for(case["packet"])["text"]["format"]["schema"]
    branches = schema["properties"]["coverage_links"]["items"]["anyOf"]
    allowed = {
        (i, ref)
        for branch in branches
        for i in branch["properties"]["item_id"]["enum"]
        for ref in branch["properties"]["reference_id"]["enum"]
    }
    assert ("item_4", "item_3") not in allowed
    assert ("item_3", "item_4") in allowed
    with pytest.raises(ValueError, match="earlier report"):
        S.render(call, case["packet"])
