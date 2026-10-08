"""Source wording is selected, never authored by the sentiment classifier."""

import pytest
from thesis.db import transaction, one
from thesis.research import sentiment as S
from thesis.providers import ledger
from test_market import prepare
from test_sentiment import provider, add_social, feed
from test_sentiment_context import with_context


def test_new_request_has_source_specific_child_and_parent_evidence(owner):
    iid, _, _, _ = with_context(owner)
    with transaction() as c:
        packet = S.prepare(c, iid)
    schema = S.request_for(packet)["text"]["format"]["schema"]
    branches = schema["properties"]["items"]["items"]["anyOf"]
    assert len(branches) == len(packet["sources"])
    for source, branch in zip(packet["sources"], branches):
        p = branch["properties"]
        assert p["id"]["enum"] == [source["label"]]
        assert "explanation" not in p
        assert list(p).index("passages") < list(p).index("sentiment")
        passage_def = schema["$defs"][p["passages"]["items"]["$ref"].split("/")[-1]]
        expected = [
            q["id"]
            for q in source["passages"]
            if not source.get("conversation") or q["id"] != "p0"
        ]
        assert passage_def["enum"] == expected
        if source.get("conversation"):
            assert p["context_passages"]["items"]["enum"] == [
                q["id"] for q in source["conversation"]["passages"]
            ]
            assert p["context_passages"]["minItems"] == 1
        else:
            assert p["context_passages"]["maxItems"] == 0
        if source["channel"] == "news":
            assert p["previous_passages"]["maxItems"] == 0


def test_current_and_previous_quotes_are_exact_and_no_model_prose_is_accepted(owner):
    iid = prepare(owner)
    add_social(
        iid,
        feed(
            body="I used to dislike Microsoft. I now respect Microsoft, although I have not explained why."
        ),
    )

    def change(items):
        items[-1].update(
            sentiment="positive", passages=["p2"], previous_passages=["p1"]
        )
        return items

    result = S.generate(iid, transport=provider(mutate=change))
    item = result["items"][-1]
    assert (
        item["citations"][0]["quote"]
        == "I now respect Microsoft, although I have not explained why."
    )
    assert item["previous_citations"][0]["quote"] == "I used to dislike Microsoft."
    assert item["explanation"] == S.basis_description("expressed_evaluation")
    assert item["evidence_policy"] == S.EVIDENCE_POLICY
    before = ledger.snapshot()
    assert (
        S.generate(
            iid,
            transport=lambda _: pytest.fail("Same selected wording was charged again"),
        )["id"]
        == result["id"]
    )
    assert before == ledger.snapshot()


@pytest.mark.parametrize(
    "fault",
    [
        "prose",
        "missing_basis",
        "foreign_previous",
        "duplicate_previous",
        "news_previous",
        "description_positive",
        "outcome_neutral",
        "unclear_direction",
        "irrelevant_previous",
    ],
)
def test_invalid_basis_or_source_roles_publish_nothing(owner, fault):
    iid = prepare(owner)
    add_social(iid)

    def change(items):
        i = items[-1]
        if fault == "prose":
            i["explanation"] = "The poster sold because demand collapsed."
        elif fault == "missing_basis":
            i.pop("basis")
        elif fault == "foreign_previous":
            i["previous_passages"] = ["p999"]
        elif fault == "duplicate_previous":
            i["previous_passages"] = ["p1", "p1"]
        elif fault == "news_previous":
            items[0]["previous_passages"] = ["p1"]
        elif fault == "description_positive":
            i.update(basis="descriptive", sentiment="positive")
        elif fault == "outcome_neutral":
            i.update(basis="stated_outcome", sentiment="neutral")
        elif fault == "unclear_direction":
            i.update(basis="unclear", sentiment="negative")
        else:
            i.update(
                relevance="unrelated",
                sentiment="unclear",
                basis="unclear",
                previous_passages=["p1"],
            )
        return items

    with pytest.raises(ValueError):
        S.generate(iid, transport=provider(mutate=change))
    with transaction() as c:
        assert not one(
            c, "SELECT 1 FROM sentiment_analyses WHERE instrument_id=%s", (iid,)
        )


def test_one_quote_may_contain_both_explicit_earlier_and_current_view(owner):
    iid = prepare(owner)
    add_social(iid, feed(body="I used to dislike Microsoft, but now I respect it."))

    def change(items):
        items[-1].update(
            sentiment="positive", passages=["p1"], previous_passages=["p1"]
        )
        return items

    item = S.generate(iid, transport=provider(mutate=change))["items"][-1]
    assert item["citations"] == item["previous_citations"]


def test_earlier_wording_survives_alert_export_and_source_withdrawal(owner):
    from uuid import uuid4
    from psycopg.types.json import Jsonb
    from thesis import review_digest
    from thesis.monitoring import news_watch

    iid = prepare(owner)
    add_social(iid, feed(body="I used to admire Microsoft. I now dislike its outlook."))

    def change(items):
        items[-1].update(passages=["p2"], previous_passages=["p1"])
        return items

    reading = S.generate(iid, transport=provider(mutate=change))
    selected = reading["items"][-1]
    selected["previous_citations"][0]["quote"] += " <script>authored</script>"
    # Delivery fixture tests historical export/access independently of model quality.
    news_watch.configure(owner, iid, False)
    with transaction(owner) as c:
        c.execute(
            "INSERT INTO research_alerts VALUES(%s,%s,%s,'sentiment',%s,%s,NULL,%s,now())",
            (
                uuid4(),
                owner,
                iid,
                reading["id"],
                reading["id"],
                Jsonb(dict(reason="Authored delivery fixture.", items=[selected])),
            ),
        )
    before = ledger.snapshot()
    html = review_digest.download(owner)[1]
    assert "I now dislike its outlook." in html
    assert "Earlier view identified in the same post" in html
    assert "I used to admire Microsoft." in html
    assert "&lt;script&gt;authored&lt;/script&gt;" in html and "<script>" not in html
    with transaction(admin=True) as c:
        c.execute("UPDATE social_feeds SET enabled=false")
    try:
        html = review_digest.download(owner)[1]
        assert (
            "I used to admire Microsoft." not in html
            and "I now dislike its outlook." not in html
        )
        assert "source excerpts are withheld" in html.lower()
    finally:
        with transaction(admin=True) as c:
            c.execute("UPDATE social_feeds SET enabled=true")
    assert ledger.snapshot() == before
