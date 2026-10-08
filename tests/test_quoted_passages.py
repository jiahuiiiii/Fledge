import pytest
from thesis.research.citations import source_passages, model_source, exact_excerpt


def test_shortened_standalone_link_does_not_swallow_complete_opinion():
    text='I think the strategy is shortsighted. https://example.test/a-long...'
    passages, omitted=source_passages('Comment',text)
    assert passages == [dict(id='p0',quote='Comment'),dict(id='p1.1',quote='I think the strategy is shortsighted.')]
    assert omitted == 1
    assert exact_excerpt(passages[1]['quote'],text)==passages[1]['quote']


def test_inline_shortened_link_does_not_reconstruct_a_sentence():
    text='I think https://example.test/unfinished... proves this.'
    assert source_passages('Comment',text)==([dict(id='p0',quote='Comment')],1)
from thesis.research import idea_alerts, sentiment
from test_model_budget import response
import json


@pytest.mark.parametrize("closing", ['"', "”", "'", "’"])
def test_ellipsis_in_quote_does_not_swallow_following_complete_sentence(closing):
    body = f'The analyst said, "Demand could… it depends.{closing} The device will become available on October 23. Orders open on October 16.'
    passages, omitted = source_passages("Upcoming device", body)
    assert omitted == 1
    assert any(
        p["quote"] == "The device will become available on October 23."
        for p in passages
    )
    assert all("could…" not in p["quote"] for p in passages)
    assert len({p["id"] for p in passages}) == len(passages)
    for p in passages:
        assert exact_excerpt(p["quote"], "Upcoming device\n" + body) == p["quote"]
    assert any("." in p["id"] for p in passages)


def test_plain_source_ids_and_user_reasoning_segmentation_do_not_change():
    from thesis.research.citations import passage_segments

    body = "First complete sentence. Second complete sentence."
    assert source_passages("Title", body)[0] == [
        {"id": "p0", "quote": "Title"},
        {"id": "p1", "quote": "First complete sentence."},
        {"id": "p2", "quote": "Second complete sentence."},
    ]
    reasoning = 'I heard "good." I need proof… before deciding.'
    assert len(passage_segments(reasoning, prefix="r")) == 1


def test_both_ellipsis_sentences_stay_excluded_and_no_fragment_is_reconstructed():
    passages, omitted = source_passages(
        "Safe headline", 'An analyst said "Great… maybe." The plan… remains unfinished.'
    )
    assert omitted == 2 and passages == [{"id": "p0", "quote": "Safe headline"}]


def test_nonterminal_quote_does_not_create_new_source_sentence():
    p, _ = source_passages(
        "Title", 'The analyst called it "Great" Before changing her view.'
    )
    assert len(p) == 2 and p[1]["id"] == "p1"


def test_recovered_passage_flows_through_both_model_contracts():
    text = 'The analyst said "Buy it… it is amazing." The device will become available on October 23.'
    passages, omitted = source_passages("Device launch", text)
    s = dict(
        id="one",
        label="item_1",
        title="Device launch",
        text=text,
        passages=passages,
        channel="news",
        publisher="Example",
        published_at="2026-10-01T00:00:00Z",
        available_at="2026-10-01T00:00:00Z",
        content_hash="fixture",
        omitted_fragment_count=omitted,
    )
    date_passage = next(p for p in passages if p["quote"].startswith("The device"))
    packet = dict(
        sources=[s],
        company={"symbol": "AAPL", "name": "Apple"},
        version_id="authored",
        revision=1,
        question="Is it available?",
        reasoning="I expect the device to be available today.",
        reasoning_segments=[
            {"id": "r0", "quote": "I expect the device to be available today."}
        ],
        cutoff="2026-10-02T00:00:00Z",
    )
    for module in (sentiment, idea_alerts):
        wire = json.loads(module.request_for(packet)["input"][1]["content"])
        assert date_passage in wire["sources"][0]["passages"]
        assert "amazing" not in json.dumps(wire["sources"][0])
    call = {
        "response_body": response()
        | dict(
            status="completed",
            output=[
                dict(
                    type="message",
                    content=[
                        dict(
                            type="output_text",
                            text=json.dumps(
                                {
                                    "items": [
                                        dict(
                                            id="item_1",
                                            relation="challenges",
                                            connection_basis="direct_evidence",
                                            missing_evidence=None,
                                            answer_kind="not_applicable",
                                            answer_target=None,
                                            answer_excerpt=None,
                                            reasoning_segment_id="r0",
                                            question_segment_id=None,
                                            explanation="The report gives a future availability date, contrary to already available.",
                                            passages=[date_passage["id"]],
                                        )
                                    ]
                                }
                            ),
                        )
                    ],
                )
            ],
        )
    }
    result = idea_alerts.render(call, packet)
    assert result["items"][0]["citations"][0]["quote"] == date_passage["quote"]
