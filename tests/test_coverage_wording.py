"""Comparison wording cannot copy unsupported model prose into new records."""

from copy import deepcopy
from pathlib import Path
import json
import os
import pytest
from thesis.db import transaction, one
from thesis.providers import ledger
from thesis.research import coverage, sentiment
from thesis.monitoring import news_watch
from thesis import review_digest
from test_news_coverage import analyse, pair, relation
from reporting_update_fixture import begin, acquire, classify


@pytest.mark.parametrize("kind", ["repeats", "adds_detail", "contradicts"])
def test_new_comparison_discards_free_prose_but_preserves_each_source(kind):
    link = relation(kind=kind)
    link["explanation"] = (
        "Both reports confirm InventedCounterparty paid $999 billion in SecretLocation."
    )
    raw = deepcopy(link)
    result = analyse(pair(), [link])
    output = result["result"]["coverage_links"][0]
    assert "InventedCounterparty" not in json.dumps(result["result"])
    assert "SecretLocation" not in output["explanation"]
    assert "$999" not in output["explanation"]
    assert output["explanation"].startswith("AI comparison:")
    assert output["explanation_policy"] == coverage.EXPLANATION_POLICY
    assert output["relation"] == kind
    assert output["repeat_suppression_allowed"] == (kind == "repeats")
    assert output["citations"][0]["quote"] == pair()[1]["text"]
    assert output["reference_citations"][0]["quote"] == pair()[0]["text"]
    assert link == raw


def test_saved_legacy_wording_stays_exact_and_new_policy_reuses_paid_response(
    owner, monkeypatch
):
    iid, _ = begin(owner)
    acquire(iid)
    initial = sentiment.generate(iid, transport=classify)
    assert news_watch.publish(owner, iid, initial["id"])
    acquire(iid, clarification=True)
    render = coverage.render

    def legacy_render(links, packet, items):
        result = render(links, packet, items)
        for value, supplied in zip(result, links):
            value["explanation"] = supplied.explanation
            value.pop("explanation_policy")
        return result

    with monkeypatch.context() as old:
        old.setattr(sentiment, "POLICY", "sentiment-coverage-5")
        old.setattr(coverage, "render", legacy_render)
        earlier = sentiment.generate(iid, transport=classify)
    with transaction() as c:
        original = one(
            c, "SELECT * FROM sentiment_analyses WHERE id=%s", (earlier["id"],)
        )
    assert original["result"]["coverage_links"]
    before = ledger.snapshot()
    current = sentiment.generate(
        iid, transport=lambda _: pytest.fail("Rendering change made a new paid request")
    )
    assert current["id"] != earlier["id"]
    assert (
        current["coverage_links"][0]["explanation_policy"]
        == coverage.EXPLANATION_POLICY
    )
    assert (
        current["coverage_links"][0]["explanation"]
        != earlier["coverage_links"][0]["explanation"]
    )
    with transaction() as c:
        kept = one(c, "SELECT * FROM sentiment_analyses WHERE id=%s", (earlier["id"],))
        new = one(c, "SELECT * FROM sentiment_analyses WHERE id=%s", (current["id"],))
        assert kept == original and kept["call_id"] == new["call_id"]
        shown = sentiment.present(c, kept)
        assert (
            shown["earlier_method"]
            and shown["coverage_links"] == earlier["coverage_links"]
        )
    assert ledger.snapshot() == before
    # Historical alert/export renders the original free prose with its distinct label.
    assert news_watch.publish(owner, iid, earlier["id"])
    _, html = review_digest.download(owner)
    assert (
        "Earlier AI-written summary. Check each report for the details it supports."
        in html
    )
    assert earlier["coverage_links"][0]["explanation"] in html
    assert "Microsoft denies that the service will close." in html
    assert "An unconfirmed report says Microsoft will close the service." in html
    assert ledger.snapshot() == before


def test_retained_real_comparisons_keep_relations_guards_and_quotes_without_free_prose():
    directory = os.environ.get("THESIS_COVERAGE_CORPUS")
    if not directory:
        pytest.skip("Optional saved real-source comparison corpus not supplied")
    root = Path(directory)
    frozen = json.loads((root / "frozen.json").read_text())
    links_checked = 0
    for name, case in frozen["cases"].items():
        original = json.loads((root / (name + "-result.json")).read_text())
        call = json.loads((root / (name + "-call.json")).read_text())
        text = next(
            p["text"]
            for msg in call["response_body"]["output"]
            if msg["type"] == "message"
            for p in msg["content"]
            if p["type"] == "output_text"
        )
        parsed = sentiment.Classification.model_validate_json(text)
        actual = coverage.render(
            parsed.coverage_links, case["packet"], original["items"]
        )
        assert len(actual) == len(original["coverage_links"])
        for old, new in zip(original["coverage_links"], actual):
            links_checked += 1
            assert {
                k: v
                for k, v in new.items()
                if k not in {"explanation", "explanation_policy"}
            } == {k: v for k, v in old.items() if k != "explanation"}
            assert new["explanation"] != old["explanation"]
            assert new["explanation_policy"] == coverage.EXPLANATION_POLICY
        assert coverage.group_keys(
            case["packet"]["sources"], actual
        ) == coverage.group_keys(case["packet"]["sources"], original["coverage_links"])
    assert links_checked == 7
