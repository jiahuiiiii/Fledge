from copy import deepcopy
import pytest
from pydantic import ValidationError
from thesis.alert_quality import Case, score, request, review_html


def case(task="relevance"):
    return dict(
        id="frozen-test",
        task=task,
        packet={
            "sources": [{"id": "a", "label": "item_1"}, {"id": "b", "label": "item_2"}]
        },
        expected=[
            dict(
                source_id="a",
                allowed={"relation": ["supports"]},
                rationale="This exact source supports the stated assumption.",
            ),
            dict(
                source_id="b",
                allowed={"relation": ["context", "unrelated"]},
                rationale="This source cannot test the stated assumption.",
            ),
        ],
        description="Frozen authored development test.",
        request_sha256="0" * 64,
    )


def test_alert_false_positive_and_false_negative_are_not_label_accuracy():
    c = Case(**case())
    r = {
        "items": [
            dict(source_id="a", relation="context"),
            dict(source_id="b", relation="risk"),
        ]
    }
    s = score(c, r)
    assert s["matched"] == 0 and len(s["failures"]) == 2
    assert s["alert_confusion"] == dict(
        true_positive=0, false_positive=1, true_negative=0, false_negative=1
    )


def test_gate_can_miss_signal_even_when_relevance_model_is_correct():
    c = Case(**case())
    r = {
        "items": [
            dict(source_id="b", relation="unrelated"),
            dict(source_id="a", relation="supports"),
        ]
    }
    direct = score(c, r)
    gated = score(c, r, {"a": "unclear", "b": "unrelated"})
    assert direct["matched"] == gated["matched"] == 2
    assert direct["alert_confusion"]["true_positive"] == 1
    assert gated["alert_confusion"]["false_negative"] == 1


@pytest.mark.parametrize(
    "fault", ["missing", "duplicate", "unknown", "ambiguous", "invalid_field", "empty"]
)
def test_invalid_or_unscorable_expectations_are_rejected(fault):
    data = case()
    if fault == "missing":
        data["expected"].pop()
    if fault == "duplicate":
        data["expected"][1] = deepcopy(data["expected"][0])
    if fault == "unknown":
        data["expected"][0]["source_id"] = "invented"
    if fault == "ambiguous":
        data["expected"][0]["allowed"]["relation"] = ["supports", "context"]
    if fault == "invalid_field":
        data["expected"][0]["allowed"] = {"sentiment": ["positive"]}
    if fault == "empty":
        data["expected"][0]["allowed"] = {}
    with pytest.raises(ValidationError):
        Case(**data)


@pytest.mark.parametrize(
    "result",
    [
        [dict(source_id="a", relation="supports")],
        [dict(source_id="a", relation="supports")] * 2,
        [
            dict(source_id="a", relation="supports"),
            dict(source_id="x", relation="context"),
        ],
    ],
)
def test_missing_duplicate_or_foreign_results_cannot_score_as_pass(result):
    with pytest.raises(ValueError):
        score(Case(**case()), {"items": result})


def test_prompt_or_input_change_requires_separate_frozen_manifest(monkeypatch):
    from thesis.research import idea_alerts

    monkeypatch.setattr(idea_alerts, "request_for", lambda packet: {"new": "prompt"})
    with pytest.raises(ValueError, match="frozen request changed"):
        request(Case(**case()))


def test_sentiment_has_explicit_field_denominators_without_alert_metrics():
    data = case("sentiment")
    data["expected"][0]["allowed"] = {
        "relevance": ["relevant"],
        "sentiment": ["positive", "neutral"],
    }
    data["expected"][1]["allowed"] = {
        "relevance": ["unrelated"],
        "sentiment": ["unclear"],
    }
    s = score(
        Case(**data),
        {
            "items": [
                dict(source_id="a", relevance="relevant", sentiment="positive"),
                dict(source_id="b", relevance="unrelated", sentiment="unclear"),
            ]
        },
    )
    assert s["criteria"] == s["matched"] == 4 and s["alert_confusion"] is None


def test_review_packet_escapes_source_model_and_authored_text():
    c = case()
    c["packet"].update(
        question="<script>question</script>",
        reasoning="<script>private</script>",
        cutoff="2026-10-02T00:00:00Z",
    )
    for s in c["packet"]["sources"]:
        s.update(
            title="<img onerror=bad>",
            text="<script>untrusted</script>",
            publisher="Example",
            published_at="2026-10-01",
        )
    result = dict(
        prompt_version="test",
        items=[
            dict(
                source_id="a",
                relation="supports",
                explanation="<script>model</script>",
                reasoning_quote="<script>private</script>",
                citations=[{"quote": "<script>source</script>"}],
            ),
            dict(
                source_id="b",
                relation="unrelated",
                explanation="Unrelated source.",
                citations=[],
            ),
        ],
    )
    html = review_html(
        {"description": "<script>notes</script>", "cases": [c]}, {c["id"]: result}
    )
    assert "<script>" not in html and "<img " not in html
    assert "&lt;script&gt;model" in html and "default-src 'none'" in html
    assert "Frozen expected labels" in html and "not an accuracy rate" in html


def test_answers_count_as_expected_updates_without_becoming_support():
    data = case()
    data["expected"][0]["allowed"]["relation"] = ["answers"]
    c = Case(**data)
    result = {
        "items": [
            dict(source_id="a", relation="answers"),
            dict(source_id="b", relation="context"),
        ]
    }
    assert score(c, result)["alert_confusion"]["true_positive"] == 1
    result["items"][0]["relation"] = "supports"
    assert score(c, result)["matched"] == 1
