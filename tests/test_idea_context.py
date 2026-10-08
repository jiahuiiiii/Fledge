"""Private relevance uses only its pinned shared sample's saved parent. Mocked AI."""

from copy import deepcopy
from uuid import uuid4
import json
import pytest
from thesis import service, review_digest
from thesis.models import SaveIdea
from thesis.db import transaction, one
from thesis.providers import ledger
from thesis.research import sentiment as S, idea_alerts as A, conversation as cv
from thesis.monitoring import news_watch
from test_conversation import setup, fetcher, unlock
from test_sentiment import provider as classifier
from test_idea_alerts import provider


def case(owner, context=True):
    iid, post, child, parent = setup(owner)
    saved = service.save_idea(
        owner,
        SaveIdea(
            instrument_id=iid,
            expected_revision=0,
            question="What do technical users think?",
            reasoning="I expect technical users to dislike Microsoft software.",
            status="draft",
            conditions=[],
        ),
    )
    if context:
        cv.collect(post["id"], fetcher=fetcher(child, parent, []))
    reading = S.generate(iid, transport=classifier())
    return iid, post, child, parent, saved, reading


def packet_for(owner, iid, reading):
    with transaction(owner) as c:
        return A.prepare(c, owner, iid, reading["id"])[0]


def record_for(owner, checked):
    with transaction(owner) as c:
        raw = one(c, "SELECT * FROM idea_alert_checks WHERE id=%s", (checked["id"],))
        return raw, A.present(c, owner, raw)


def test_private_input_pins_shared_parent_not_latest_and_keeps_attribution(owner):
    iid, post, child, parent, _, reading = case(owner)
    packet = packet_for(owner, iid, reading)
    wire = json.loads(A.request_for(packet)["input"][1]["content"])
    shared = next(s for s in packet["sources"] if s.get("conversation"))
    supplied = next(s for s in wire["sources"] if s.get("conversation"))
    assert len(wire["sources"]) == len(packet["sources"]) == len(reading["items"])
    assert supplied["conversation"]["passages"] == shared["conversation"]["passages"]
    assert not any(
        k in json.dumps(wire) for k in ('"sentiment"', '"counts"', '"author"')
    )
    assert (
        "context_passages"
        in A.request_for(packet)["text"]["format"]["schema"]["properties"]["items"][
            "items"
        ]["anyOf"][0]["required"]
    )
    unlock(post["id"])
    cv.collect(
        post["id"],
        fetcher=fetcher(
            child, parent | {"text": "A changed parent describes something else."}, []
        ),
    )
    assert packet_for(owner, iid, reading) == packet
    checked = A.generate(owner, iid, reading["id"], transport=provider())
    raw, record = record_for(owner, checked)
    item = next(i for i in record["items"] if i.get("conversation"))
    assert record["parent_contexts"] == 1 and not record["earlier_method"]
    assert item["conversation"]["body"] == parent["text"]
    assert item["conversation"]["result_id"] == shared["conversation"]["result_id"]
    assert all(q["quote"] in child["text"] for q in item["citations"])
    assert all(q["quote"] in parent["text"] for q in item["conversation"]["citations"])
    assert item["reasoning_quote"] == record["reasoning"]
    assert record["published"] and record["noteworthy_count"] == len(record["items"])
    before = ledger.snapshot()
    assert (
        A.generate(
            owner,
            iid,
            reading["id"],
            transport=lambda _: pytest.fail("Cached private check charged again"),
        )["id"]
        == checked["id"]
    )
    assert ledger.snapshot() == before
    other = str(uuid4())
    with transaction(other) as c:
        assert not A.list_for(c, other)
        assert not one(c, "SELECT * FROM model_calls WHERE id=%s", (raw["call_id"],))


def test_later_parent_cannot_be_added_to_old_sample_or_old_check(owner, monkeypatch):
    iid, post, child, parent, _, reading = case(owner, context=False)
    with monkeypatch.context() as m:
        m.setattr(A, "PROMPT", "thesis-watch-relevance-6")
        checked = A.generate(owner, iid, reading["id"], transport=provider())
    original, _ = record_for(owner, checked)
    cv.collect(post["id"], fetcher=fetcher(child, parent, []))
    packet = packet_for(owner, iid, reading)
    assert not any(s.get("conversation") for s in packet["sources"])
    raw, visible = record_for(owner, checked)
    assert raw == original and visible["items"] == original["result"]["items"]
    assert visible["earlier_method"] and visible["parent_contexts"] == 0
    assert "earlier method" in A.download(owner, checked["id"])[1]


def test_context_only_reanalysis_is_not_new_private_watch_evidence(owner):
    iid, post, child, parent, _, reading = case(owner, context=False)
    news_watch.configure(owner, iid, True, match_idea=True)
    cv.collect(post["id"], fetcher=fetcher(child, parent, []))
    new = S.generate(iid, transport=classifier())
    assert new["id"] != reading["id"]
    before = ledger.snapshot()
    checked = A.generate(
        owner,
        iid,
        new["id"],
        automatic=True,
        transport=lambda _: pytest.fail("Parent alone triggered a private call"),
    )
    assert checked["status"] == "no_new_sources" and ledger.snapshot() == before
    with transaction(owner) as c:
        assert A.list_for(c, owner) == []


@pytest.mark.parametrize(
    "fault",
    ["missing", "unknown", "duplicate", "title_only", "foreign_item", "too_many"],
)
def test_parent_and_child_citation_faults_rejected(owner, fault):
    iid, _, _, _, _, reading = case(owner)
    packet = packet_for(owner, iid, reading)
    req = A.request_for(packet)
    wire = json.loads(req["input"][1]["content"])
    label = next(s["label"] for s in wire["sources"] if s.get("conversation"))

    def bad(items):
        item = next(i for i in items if i["id"] == label)
        if fault == "missing":
            item["context_passages"] = []
        elif fault == "unknown":
            item["context_passages"] = ["p999"]
        elif fault == "duplicate":
            item["context_passages"] *= 2
        elif fault == "title_only":
            item["passages"] = ["p0"]
        elif fault == "too_many":
            item["context_passages"] = ["p1", "p2", "p3"]
        else:
            next(i for i in items if i["id"] != label)["context_passages"] = ["p1"]
        return items

    with pytest.raises(ValueError):
        A.render({"response_body": provider(mutate=bad)(req)}, packet)
    with transaction(owner) as c:
        assert A.list_for(c, owner) == []


@pytest.mark.parametrize("during", [False, True])
def test_parent_withdrawal_blocks_or_withholds_private_check(owner, during):
    iid, _, _, _, _, reading = case(owner)

    def withdraw():
        with transaction(source=True) as c:
            c.execute("INSERT INTO hn_withdrawals VALUES('hn:99',now())")

    if not during:
        withdraw()
        before = ledger.snapshot()
        with pytest.raises(ValueError, match="source access changed"):
            A.generate(
                owner,
                iid,
                reading["id"],
                transport=lambda _: pytest.fail("Withdrawn input dispatched"),
            )
        assert ledger.snapshot() == before
    else:
        checked = A.generate(
            owner, iid, reading["id"], transport=provider(side_effect=withdraw)
        )
        _, visible = record_for(owner, checked)
        assert checked["status"] == "historical_only" and not visible["published"]
        assert visible["withheld"] and visible["items"] == visible["sources"] == []
        assert visible["parent_contexts"] is None
        html = A.download(owner, checked["id"])[1]
        assert "are withheld" in html and "Cited parent discussion" not in html


def test_private_and_periodic_exports_keep_context_and_withhold_after_removal(owner):
    iid, _, _, parent, _, reading = case(owner)
    checked = A.generate(owner, iid, reading["id"], transport=provider())
    for html in (
        A.download(owner, checked["id"])[1],
        review_digest.download(owner, days=7)[1],
    ):
        assert "Parent context used for this connection" in html
        assert "not a separate source connection" in html
        assert "https://news.ycombinator.com/item?id=99" in html
        assert "I think Microsoft software is excellent." in html
    with transaction(source=True) as c:
        c.execute("INSERT INTO hn_withdrawals VALUES('hn:99',now())")
    for html in (
        A.download(owner, checked["id"])[1],
        review_digest.download(owner, days=7)[1],
    ):
        assert (
            "are withheld" in html
            and "I think Microsoft software is excellent." not in html
        )


def test_parent_export_escapes_text_and_rejects_unsafe_links():
    from thesis.review_export import parent_context_html

    parent = dict(
        parent_type="story",
        title="<script>bad()</script>",
        citations=[dict(quote='<img src=x onerror="bad()">')],
        published_at="2026-10-01T00:00:00Z",
        checked_at="2026-10-02T00:00:00Z",
        limitation="<script>bad()</script>",
        url="javascript:bad()",
    )
    html = parent_context_html(parent, purpose="connection")
    assert "<script>" not in html and "<img " not in html and "<a " not in html
    assert "&lt;script&gt;" in html
