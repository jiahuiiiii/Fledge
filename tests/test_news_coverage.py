"""News grouping faults and watch delivery; all model responses are mocked."""

from copy import deepcopy
from datetime import datetime, timezone, timedelta
import json
import pytest
from thesis.research import coverage, sentiment, idea_alerts
from thesis.research.citations import source_passages
from thesis.monitoring import news_watch
from thesis.db import transaction, one
from test_model_budget import response
from test_market import prepare, commit, news
from test_sentiment import provider
from test_idea_alerts import setup


def source(label, body, minute=0, channel="news"):
    return dict(
        id=label,
        label=label,
        title="Microsoft development",
        text=body,
        passages=source_passages("Microsoft development", body)[0],
        content_hash=label,
        channel=channel,
        publisher="Authored wire",
        published_at=f"2026-10-01T12:{minute:02}:00+00:00",
        available_at=f"2026-10-01T12:{minute:02}:00+00:00",
        url="https://example.test/" + label,
    )


def relation(item="item_2", prior="item_1", kind="repeats"):
    return dict(
        item_id=item,
        reference_id=prior,
        relation=kind,
        explanation="Both reports describe the same announced executive departure.",
        item_passages=["p1"],
        reference_passages=["p1"],
    )


def analyse(sources, links, comparisons=None, tones=None):
    packet = dict(
        company={"symbol": "MSFT", "name": "Microsoft"},
        sources=sources,
        comparison_sources=comparisons or [],
        cutoff="2026-10-02T00:00:00+00:00",
    )
    items = [
        dict(
            id=s["label"],
            relevance="relevant",
            sentiment=(tones or {}).get(s["id"], "negative"),
            statement="reported_development",
            topic="management",
            basis=(
                "descriptive"
                if (tones or {}).get(s["id"], "negative") == "neutral"
                else (
                    "unclear"
                    if (tones or {}).get(s["id"], "negative") == "unclear"
                    else "expressed_evaluation"
                )
            ),
            previous_passages=[],
            passages=["p1"],
        )
        for s in sources
    ]
    call = dict(
        response_body=response()
        | dict(
            output=[
                dict(
                    type="message",
                    content=[
                        dict(
                            type="output_text",
                            text=json.dumps(dict(items=items, coverage_links=links)),
                        )
                    ],
                )
            ]
        )
    )
    return dict(packet=packet, result=sentiment.render(call, packet))


def pair():
    return [
        source("item_1", "Microsoft says its research chief will leave.", 0),
        source("item_2", "The research chief plans to depart Microsoft.", 1),
    ]


def test_paraphrased_coverage_counts_once_but_retains_each_label_quote():
    a = analyse(pair(), [relation()])
    assert a["result"]["summary"]["news"]["counted_groups"] == 1
    assert len(a["result"]["items"]) == 2
    link = a["result"]["coverage_links"][0]
    assert link["repeat_suppression_allowed"]
    assert link["reference_citations"][0]["quote"] == pair()[0]["text"]
    assert link["citations"][0]["source_id"] == "item_2"


@pytest.mark.parametrize(
    "fault", ["self", "cycle", "foreign", "social", "duplicate", "quote", "unrelated"]
)
def test_invalid_links_publish_no_rendered_group(fault):
    sources = pair()
    links = [relation()]
    if fault == "self":
        links[0]["reference_id"] = "item_2"
    if fault == "cycle":
        links.append(relation("item_1", "item_2"))
    if fault == "foreign":
        links[0]["reference_id"] = "invented"
    if fault == "social":
        sources[0]["channel"] = "social"
    if fault == "duplicate":
        links.append(deepcopy(links[0]))
    if fault == "quote":
        links[0]["reference_passages"] = ["p999"]
    if fault == "unrelated":
        # Direct structural validator with a mismatched relevance claim.
        items = [
            dict(
                source_id=s["id"],
                relevance="unrelated",
                statement="reported_development",
            )
            for s in sources
        ]
        with pytest.raises(ValueError):
            coverage.render([coverage.Link(**links[0])], dict(sources=sources), items)
        return
    with pytest.raises(ValueError):
        analyse(sources, links)


def test_conflicting_framing_is_mixed_not_two_votes_and_never_repeat_suppressed():
    a = analyse(pair(), [relation(kind="contradicts")], tones={"item_1": "positive"})
    assert a["result"]["summary"]["news"]["counts"]["mixed"] == 1
    assert not a["result"]["coverage_links"][0]["repeat_suppression_allowed"]
    assert coverage.keys(a, pair()[1]) == {"content:item_2"}


@pytest.mark.parametrize('relevance', ['unrelated', 'unclear'])
@pytest.mark.parametrize('which', [0, 1])
def test_matching_reports_with_unusable_company_relevance_stay_unlinked(relevance, which):
    sources = pair()
    items = [dict(source_id=s['id'], relevance='relevant', statement='reported_development')
             for s in sources]
    items[which]['relevance'] = relevance
    packet = dict(sources=sources)
    # Exact matching event/citations cannot override either company's relevance.
    with pytest.raises(ValueError, match='coverage group'):
        coverage.render([coverage.Link(**relation())], packet, items)
    assert coverage.render([], packet, items) == []


@pytest.mark.parametrize(
    "body",
    [
        "Microsoft says the chief will depart in 2027.",
        "Microsoft denied that the chief will depart.",
    ],
)
def test_numeric_and_negation_guard_retains_report_even_if_model_calls_it_repeat(body):
    sources = pair()
    sources[1] = source("item_2", body, 1)
    a = analyse(sources, [relation()])
    link = a["result"]["coverage_links"][0]
    assert (
        link["relation"] == "repeats"
        and not link["repeat_suppression_allowed"]
        and link["review_note"]
    )
    assert coverage.keys(a, sources[1]) == {"content:item_2"}


def test_comparison_only_news_does_not_add_sentiment_votes_and_seen_repeat_stays_quiet():
    earlier, new = pair()
    earlier["label"] = "prior_1"
    a = analyse([new], [relation(prior="prior_1")], [earlier])
    assert a["result"]["summary"]["news"]["selected"] == 1
    previous = analyse([earlier], [])
    assert not news_watch.changes(previous, a, {("news", "content:item_1")})
    # The same new source remains visible when this owner never saw its reference.
    other = analyse([source("other", "Microsoft opens an office.", 0)], [])
    assert len(news_watch.changes(other, a, set())) == 1


def test_decimal_suffix_does_not_turn_3_point_2_billion_into_a_new_number():
    sources = [
        source("item_1", "Microsoft could face $3.2 billion in claims.", 0),
        source("item_2", "Microsoft could face $3.2B in claims.", 1),
    ]
    result = analyse(sources, [relation()])
    assert result["result"]["coverage_links"][0]["repeat_suppression_allowed"]


def test_updates_contradictions_and_distinct_events_stay_eligible_after_seen_baseline():
    earlier, new = pair()
    previous = analyse([earlier], [])
    for links in [[relation(kind="adds_detail")], [relation(kind="contradicts")], []]:
        a = analyse([earlier, new], links)
        changes = news_watch.changes(previous, a, {("news", "content:item_1")})
        assert len(changes) == 1 and changes[0]["items"][0]["source_id"] == "item_2"


@pytest.mark.parametrize("field", ["summary_policy", "prompt_version", "model"])
def test_method_change_cannot_claim_a_sentiment_reversal(field):
    previous = analyse([pair()[0]], [])
    current = analyse([pair()[1]], [])
    previous["result"]["summary"]["news"]["tone"] = "positive leaning"
    current["result"]["summary"]["news"]["tone"] = "negative leaning"
    previous["result"][field] = "older-method"
    assert all(a["kind"] != "sentiment" for a in news_watch.changes(previous, current))


def test_changed_denial_headline_is_not_hidden_by_identical_long_body():
    body = "Microsoft and its counterparty are discussing the reported contract. " * 4
    older = source("item_1", body, 0)
    newer = source("item_2", body, 1)
    older["title"] = "Microsoft wins the contract"
    newer["title"] = "Microsoft denies winning the contract"
    for s in (older, newer):
        s["passages"] = source_passages(s["title"], s["text"])[0]
    previous = analyse([older], [])
    current = analyse([newer], [], [older])
    # Even without a model link, matching bodies cannot suppress a new headline.
    changes = news_watch.changes(
        previous, current, {("news", coverage.text_key(older))}
    )
    assert len(changes) == 1 and changes[0]["items"][0]["source_id"] == "item_2"


def test_legacy_body_only_seen_key_cannot_identify_an_unseen_reference_headline():
    body = "Microsoft and its counterparty are discussing the reported contract. " * 4
    prior = source("prior_1", body, 0)
    new = source("item_2", body, 1)
    previous = analyse([source("other", "Microsoft opened an office.", 0)], [])
    current = analyse([new], [relation(prior="prior_1")], [prior])
    # The old body-only key could belong to a different, contradictory headline.
    # Only exact report identity can establish that this reference was seen.
    changes = news_watch.changes(
        previous, current, {("news", coverage.text_key(prior))}
    )
    assert len(changes) == 1


def test_comparison_pool_is_bounded_cached_and_not_classified(owner):
    iid = prepare(owner)
    commit(
        iid,
        [
            news(
                id=200 + i,
                url=f"https://example.test/{i}",
                headline=f"Microsoft distinct development {i}",
                summary=f"Microsoft announced project {i}.",
            )
            for i in range(35)
        ],
    )
    with transaction() as c:
        packet = sentiment.prepare(c, iid)
    assert len(packet["sources"]) == 26 and not packet["comparison_sources"]
    from thesis.research.sentiment_batching import plan, MAX_COMPARISONS
    parts = plan(packet)
    assert sum(len(p['sources']) for p in parts) == 26
    for part in parts:
        wire = json.loads(sentiment.request_for(part)["input"][1]["content"])
        assert len(wire['sources']) <= 8 and len(wire['comparison_sources']) <= MAX_COMPARISONS
    first = sentiment.generate(iid, transport=provider())
    repeat = sentiment.generate(
        iid, transport=lambda _: pytest.fail("cached request dispatched")
    )
    assert (
        first["id"] == repeat["id"]
        and len(first["items"]) == 26
        and len(first["sources"]) == 26
    )


def test_withdrawn_comparison_source_withholds_group_and_private_check(
    owner, monkeypatch
):
    iid = prepare(owner)
    first = sentiment.generate(iid, transport=provider())
    with transaction() as c:
        record = one(c, "SELECT * FROM sentiment_analyses WHERE id=%s", (first["id"],))
        extra = deepcopy(record["packet"]["sources"][0])
        extra["id"] = "unavailable-reference"
        record["packet"]["comparison_sources"] = [extra]
        visible = sentiment.present(c, record)
    assert visible["withheld"] and visible["items"] == [] and visible["sources"] == []


def test_private_watch_skips_only_previously_seen_repeats(owner, monkeypatch):
    iid, saved, first = setup(owner)
    news_watch.configure(owner, iid, True, match_idea=True)
    with transaction(owner) as c:
        previous = one(
            c, "SELECT * FROM sentiment_analyses WHERE id=%s", (first["id"],)
        )
        old = previous["packet"]["sources"][0]
    newer = deepcopy(old)
    newer.update(
        id="new-report",
        label="item_2",
        content_hash="new-report",
        text="Microsoft repeats the contract report.",
        published_at=(datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat(),
    )
    fake = deepcopy(previous)
    fake["packet"]["sources"] = [newer]
    fake["packet"]["comparison_sources"] = [old]
    fake["result"]["items"] = [dict(source_id="new-report", relevance="relevant")]
    fake["result"]["coverage_links"] = [
        dict(
            source_id="new-report",
            reference_source_id=old["id"],
            repeat_suppression_allowed=True,
        )
    ]
    monkeypatch.setattr(idea_alerts, "latest_analysis", lambda *_: fake)
    monkeypatch.setattr(sentiment, "present", lambda *_: dict(withheld=False))
    with transaction(owner) as c:
        fake["result"]["coverage_links"][0]["repeat_suppression_allowed"] = False
        packet, status = idea_alerts.prepare(c, owner, iid, automatic=True)
        assert status is None and [s["id"] for s in packet["sources"]] == ["new-report"]
        fake["result"]["coverage_links"][0]["repeat_suppression_allowed"] = True
        packet, status = idea_alerts.prepare(c, owner, iid, automatic=True)
        assert packet is None and status == "no_new_sources"
        assert one(
            c,
            "SELECT content_key FROM idea_watch_seen WHERE owner_id=%s AND version_id=%s AND content_key='content:new-report'",
            (owner, saved["version_id"]),
        )


@pytest.mark.parametrize("automatic", [False, True])
@pytest.mark.parametrize("teaser_first", [False, True])
def test_private_check_retains_distinct_unseen_reports_within_a_repeat_group(
    owner, monkeypatch, automatic, teaser_first
):
    iid, saved, first = setup(owner)
    news_watch.configure(owner, iid, True, match_idea=True)
    with transaction(owner) as c:
        prior = one(c, "SELECT * FROM sentiment_analyses WHERE id=%s", (first["id"],))
    full = source(
        "full-report",
        "Microsoft authorised $150 billion of buybacks. The remaining authority is $235 billion.",
        0,
    )
    teaser = source("newer-teaser", "Microsoft $150 billion buyback roundup.", 1)
    fake = deepcopy(prior)
    fake["packet"]["sources"] = [teaser, full] if teaser_first else [full, teaser]
    fake["result"]["items"] = [
        dict(source_id=s["id"], relevance="relevant") for s in fake["packet"]["sources"]
    ]
    fake["result"]["coverage_links"] = [
        dict(
            source_id=teaser["id"],
            reference_source_id=full["id"],
            repeat_suppression_allowed=True,
        )
    ]
    monkeypatch.setattr(idea_alerts, "latest_analysis", lambda *_: fake)
    monkeypatch.setattr(sentiment, "present", lambda *_: dict(withheld=False))
    with transaction(owner) as c:
        packet, status = idea_alerts.prepare(c, owner, iid, automatic=automatic)
        assert status is None
        assert {s["id"] for s in packet["sources"]} == {"full-report", "newer-teaser"}
        assert any("remaining authority" in s["text"] for s in packet["sources"])
