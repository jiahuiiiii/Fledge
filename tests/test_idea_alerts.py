"""Private watch behaviour with mocked models and disposable PostgreSQL."""

import json
from uuid import uuid4
from datetime import datetime, timezone, timedelta
import pytest
from thesis import service
from thesis.models import SaveIdea
from thesis.db import transaction, one, rows
from thesis.research import sentiment, idea_alerts
from thesis.monitoring import news_watch
from thesis.providers import ledger
from test_market import prepare, commit, news
from test_sentiment import provider as sentiment_provider, add_social
from test_model_budget import response


def provider(
    relation="challenges", mutate=None, side_effect=None, answer_anchor="reasoning"
):
    def call(body):
        packet = json.loads(body["input"][1]["content"])
        assert "sentiment" not in packet and "counts" not in packet
        items = [
            dict(
                id=s["label"],
                relation=relation,
                reasoning_segment_id=(
                    None
                    if relation == "unrelated"
                    else packet["reasoning_segments"][0]["id"]
                ),
                question_segment_id=None,
                explanation=(
                    "This authored report may be related, but it does not establish the saved outcome."
                    if relation == "possible_link"
                    else "The supplied report may challenge the specified expectation; the outcome remains uncertain."
                ),
                passages=[
                    (
                        next(p["id"] for p in s["passages"] if p["id"] != "p0")
                        if s.get("conversation")
                        else s["passages"][0]["id"]
                    )
                ],
                context_passages=(
                    [s["conversation"]["passages"][0]["id"]]
                    if s.get("conversation")
                    else []
                ),
            )
            for s in packet["sources"]
        ]
        for item in items:
            item["connection_basis"] = {
                "possible_link": "inferred_link",
                "context": "background",
                "unclear": "unclear",
                "unrelated": "unrelated",
            }.get(relation, "direct_evidence")
            item["missing_evidence"] = (
                "Evidence connecting the reported development to the saved outcome."
                if relation == "possible_link"
                else None
            )
            item["answer_kind"] = (
                "partial_answer" if relation == "answers" else "not_applicable"
            )
            item["answer_target"] = (
                packet[answer_anchor + "_segments"][0]["quote"]
                if relation == "answers"
                else None
            )
            source = next(s for s in packet["sources"] if s["label"] == item["id"])
            item["answer_excerpt"] = (
                next(
                    p["quote"]
                    for p in source["passages"]
                    if p["id"] == item["passages"][0]
                )
                if relation == "answers"
                else None
            )
        if mutate:
            items = mutate(items)
        if side_effect:
            side_effect()
        return response() | dict(
            model=body["model"],
            id="resp_" + str(uuid4()),
            output=[
                dict(
                    type="message",
                    content=[
                        dict(type="output_text", text=json.dumps(dict(items=items)))
                    ],
                )
            ],
        )

    return call


def setup(owner, social=False):
    iid = prepare(owner)
    if social:
        add_social(iid)
    saved = service.save_idea(
        owner,
        SaveIdea(
            instrument_id=iid,
            expected_revision=0,
            question="Will demand translate into margins?",
            reasoning="I expect revenue growth to turn into durable operating margins.",
            status="draft",
            conditions=[],
        ),
    )
    analysis = sentiment.generate(iid, transport=sentiment_provider("positive"))
    return iid, saved, analysis


def newer(iid):
    commit(
        iid,
        [
            news(
                id=9,
                url="https://example.test/new-change",
                headline="Microsoft announces additional demand",
                summary="Microsoft reports new demand, but says costs remain an important uncertainty.",
            )
        ],
    )
    return sentiment.generate(iid, transport=sentiment_provider("positive"))


def test_explicit_private_check_quotes_reasoning_and_sources_and_caches(owner):
    iid, saved, analysis = setup(owner, True)
    checked = idea_alerts.generate(
        owner, iid, analysis["id"], saved["version_id"], transport=provider()
    )
    before = ledger.snapshot()
    repeated = idea_alerts.generate(
        owner,
        iid,
        analysis["id"],
        saved["version_id"],
        transport=lambda _: pytest.fail("repeat paid call"),
    )
    assert checked["id"] == repeated["id"] and ledger.snapshot() == before
    with transaction(owner) as c:
        record = idea_alerts.list_for(c, owner)[0]
        assert (
            record["published"]
            and record["delivery_mode"] == "manual"
            and not record["historical_revision"]
        )
        assert len(record["items"]) == 2 and {
            i["channel"] for i in record["items"]
        } == {"news", "social"}
        for item in record["items"]:
            assert item["reasoning_quote"] == record["reasoning"]
            source = next(s for s in record["sources"] if s["id"] == item["source_id"])
            for cit in item["citations"]:
                assert cit["quote"] in source["title"] + "\n" + source["body"]
        raw = one(c, "SELECT * FROM idea_alert_checks WHERE id=%s", (checked["id"],))
        call = one(c, "SELECT * FROM model_calls WHERE id=%s", (raw["call_id"],))
        assert str(call["owner_id"]) == owner
    with transaction(str(uuid4())) as c:
        assert not idea_alerts.list_for(c, str(uuid4()))
        assert not one(c, "SELECT * FROM model_calls WHERE id=%s", (raw["call_id"],))


@pytest.mark.parametrize("relation", ["context", "unclear", "unrelated"])
def test_nonmaterial_connections_stay_in_history_without_alerts(owner, relation):
    iid, saved, analysis = setup(owner)
    idea_alerts.generate(
        owner, iid, analysis["id"], saved["version_id"], transport=provider(relation)
    )
    with transaction(owner) as c:
        result = idea_alerts.list_for(c, owner)[0]
        assert not result["published"] and result["noteworthy_count"] == 0


def test_research_question_can_receive_specific_risk_without_claimed_stance(owner):
    iid, saved, analysis = setup(owner)
    service.save_idea(
        owner,
        SaveIdea(
            instrument_id=iid,
            expected_revision=1,
            question="Is there evidence of paid demand?",
            reasoning="I want evidence of paying customers before deciding whether growth is supported.",
            status="draft",
            conditions=[],
        ),
    )
    result = idea_alerts.generate(
        owner, iid, analysis["id"], transport=provider("risk")
    )
    with transaction(owner) as c:
        record = idea_alerts.list_for(c, owner)[0]
        assert record["published"] and record["noteworthy_count"] == 1
        assert record["items"][0]["relation"] == "risk"
        assert "before deciding" in record["items"][0]["reasoning_quote"]
    _, html = idea_alerts.download(owner, result["id"])
    assert "risk" in html and "before deciding" in html


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "duplicate",
        "foreign_passage",
        "foreign_reasoning",
        "missing_reasoning",
        "unrelated_reasoning",
    ],
)
def test_malformed_relevance_response_publishes_nothing(owner, fault):
    iid, saved, analysis = setup(owner, True)

    def mutate(items):
        if fault == "missing":
            return items[:-1]
        if fault == "duplicate":
            return [items[0], items[0]]
        if fault == "foreign_passage":
            items[0]["passages"] = ["invented"]
        if fault == "foreign_reasoning":
            items[0]["reasoning_segment_id"] = "r99"
        if fault == "missing_reasoning":
            items[0]["reasoning_segment_id"] = None
        if fault == "unrelated_reasoning":
            items[0]["relation"] = "unrelated"
        return items

    with pytest.raises(ValueError):
        idea_alerts.generate(
            owner,
            iid,
            analysis["id"],
            saved["version_id"],
            transport=provider(mutate=mutate),
        )
    with transaction(owner) as c:
        assert not rows(c, "SELECT * FROM idea_alert_checks") and not rows(
            c, "SELECT * FROM idea_alert_publications"
        )


def test_watch_scope_requires_reasoning_and_preserves_preferences(owner):
    iid = prepare(owner)
    with pytest.raises(ValueError):
        news_watch.configure(owner, iid, True, match_idea=True)
    with transaction(owner) as c:
        assert not one(c, "SELECT * FROM news_watches")
    saved = service.save_idea(
        owner,
        SaveIdea(
            instrument_id=iid,
            expected_revision=0,
            question="Can margins hold?",
            reasoning="I expect margins to remain durable.",
            status="draft",
            conditions=[],
        ),
    )
    analysis = sentiment.generate(iid, transport=sentiment_provider())
    news_watch.configure(owner, iid, True, match_idea=True)
    news_watch.configure(owner, iid, True, 240)
    with transaction(owner) as c:
        w = one(c, "SELECT * FROM news_watches")
        assert w["match_idea"] and w["interval_minutes"] == 240
        assert one(c, "SELECT * FROM idea_watch_state")["status"] == "baseline"
    assert (
        idea_alerts.generate(
            owner,
            iid,
            analysis["id"],
            automatic=True,
            transport=lambda _: pytest.fail("existing baseline"),
        )["status"]
        == "no_new_sources"
    )


def test_positive_company_news_can_challenge_reasoning_without_generic_alert(owner):
    iid, saved, analysis = setup(owner)
    news_watch.configure(owner, iid, True, match_idea=True)
    changed = newer(iid)
    assert news_watch.publish(owner, iid, changed["id"]) == 0
    checked = idea_alerts.generate(
        owner, iid, changed["id"], automatic=True, transport=provider("challenges")
    )
    with transaction(owner) as c:
        record = idea_alerts.list_for(c, owner)[0]
        assert (
            record["published"]
            and record["delivery_mode"] == "watch"
            and len(record["items"]) == 1
        )
        assert not news_watch.list_alerts(c, owner)
    before = ledger.snapshot()
    assert (
        idea_alerts.generate(
            owner,
            iid,
            changed["id"],
            automatic=True,
            transport=lambda _: pytest.fail("seen again"),
        )["status"]
        == "no_new_sources"
    )
    assert ledger.snapshot() == before


def test_new_reasoning_resets_future_baseline_without_reusing_old_verdict(owner):
    iid, saved, analysis = setup(owner)
    news_watch.configure(owner, iid, True, match_idea=True)
    service.save_idea(
        owner,
        SaveIdea(
            instrument_id=iid,
            expected_revision=1,
            question="Can another story matter?",
            reasoning="I now want evidence of enterprise adoption.",
            status="draft",
            conditions=[],
        ),
    )
    assert (
        idea_alerts.generate(
            owner,
            iid,
            analysis["id"],
            automatic=True,
            transport=lambda _: pytest.fail("new belief silently checked"),
        )["status"]
        == "baseline"
    )
    with pytest.raises(service.Conflict):
        idea_alerts.generate(
            owner,
            iid,
            analysis["id"],
            saved["version_id"],
            transport=lambda _: pytest.fail("stale input"),
        )


def test_edit_during_model_call_retains_old_check_without_current_alert(owner):
    iid, saved, analysis = setup(owner)

    def edit():
        service.save_idea(
            owner,
            SaveIdea(
                instrument_id=iid,
                expected_revision=1,
                question="A different question",
                reasoning="This edited reasoning is about adoption rather than margins.",
                status="draft",
                conditions=[],
            ),
        )

    result = idea_alerts.generate(
        owner,
        iid,
        analysis["id"],
        saved["version_id"],
        transport=provider(side_effect=edit),
    )
    assert result["status"] == "historical_only"
    with transaction(owner) as c:
        row = idea_alerts.list_for(c, owner)[0]
        assert (
            row["revision"] == 1 and row["historical_revision"] and not row["published"]
        )
        assert (
            "operating margins" in row["reasoning"]
            and "adoption" not in row["reasoning"]
        )


def test_disable_during_automatic_call_retains_result_but_never_delivers(owner):
    iid, saved, analysis = setup(owner)
    news_watch.configure(owner, iid, True, match_idea=True)
    changed = newer(iid)
    result = idea_alerts.generate(
        owner,
        iid,
        changed["id"],
        automatic=True,
        transport=provider(side_effect=lambda: news_watch.configure(owner, iid, False)),
    )
    assert result["status"] == "historical_only"
    with transaction(owner) as c:
        assert not idea_alerts.list_for(c, owner)[0]["published"]


def test_source_withdrawal_after_dispatch_withholds_all_source_interpretation(owner):
    iid, saved, analysis = setup(owner, True)

    def deny():
        with transaction(admin=True) as c:
            c.execute("UPDATE social_feeds SET enabled=false")

    try:
        result = idea_alerts.generate(
            owner,
            iid,
            analysis["id"],
            saved["version_id"],
            transport=provider(side_effect=deny),
        )
        assert result["status"] == "historical_only"
        with transaction(owner) as c:
            row = idea_alerts.list_for(c, owner)[0]
            assert (
                row["withheld"]
                and not row["items"]
                and not row["sources"]
                and row["noteworthy_count"] is None
            )
    finally:
        with transaction(admin=True) as c:
            c.execute("UPDATE social_feeds SET enabled=true")


def test_review_is_private_idempotent_and_does_not_change_evidence(owner):
    iid, saved, analysis = setup(owner)
    result = idea_alerts.generate(
        owner, iid, analysis["id"], saved["version_id"], transport=provider()
    )
    assert idea_alerts.review(owner, result["id"], "reviewed") == idea_alerts.review(
        owner, result["id"], "reviewed"
    )
    with pytest.raises(service.Conflict):
        idea_alerts.review(owner, result["id"], "unresolved")
    with pytest.raises(service.Missing):
        idea_alerts.review(str(uuid4()), result["id"], "reviewed")
    with transaction(owner) as c:
        row = idea_alerts.list_for(c, owner)[0]
        assert row["noteworthy_count"] == 1 and row["review_action"] == "reviewed"
        with pytest.raises(Exception):
            c.execute(
                "UPDATE idea_alert_checks SET result='{}' WHERE id=%s", (result["id"],)
            )


def test_company_unread_count_tracks_only_published_unreviewed_checks(owner):
    iid, saved, analysis = setup(owner)

    def unread(account=owner):
        with transaction(account) as c:
            return next(
                r["unread"]
                for r in service.catalogue(c, account)
                if str(r["id"]) == iid
            )

    assert unread() == 0
    result = idea_alerts.generate(
        owner, iid, analysis["id"], saved["version_id"], transport=provider()
    )
    assert unread() == 1 and unread(str(uuid4())) == 0
    idea_alerts.review(owner, result["id"], "unresolved")
    assert unread() == 0
    changed = newer(iid)
    idea_alerts.generate(
        owner, iid, changed["id"], saved["version_id"], transport=provider("context")
    )
    assert unread() == 0


def test_scheduler_calls_private_matcher_only_for_explicit_scope(owner):
    iid, saved, analysis = setup(owner)
    now = datetime.now(timezone.utc)
    news_watch.configure(owner, iid, True, now=now)
    kwargs = dict(
        now=now + timedelta(minutes=61),
        market_refresh=lambda _: None,
        social_refresh=lambda: None,
        analyzer=lambda _: analysis,
    )
    news_watch.run_once(
        owner,
        **kwargs,
        idea_analyzer=lambda *a, **kw: pytest.fail("not opted into private analysis"),
    )
    news_watch.configure(owner, iid, True, now=now, match_idea=True)
    seen = []
    news_watch.run_once(
        owner, **kwargs, idea_analyzer=lambda *a, **kw: seen.append((a, kw))
    )
    assert len(seen) == 1 and seen[0][1]["automatic"] and seen[0][1]["claim_token"]


def test_export_is_private_inert_and_source_withdrawal_is_applied(owner):
    iid, saved, analysis = setup(owner, True)
    service.save_idea(
        owner,
        SaveIdea(
            instrument_id=iid,
            expected_revision=1,
            question="A private <script> question",
            reasoning='I expect margins to hold. <script>alert("never run")</script>',
            status="draft",
            conditions=[],
        ),
    )
    result = idea_alerts.generate(owner, iid, analysis["id"], transport=provider())
    budget = ledger.snapshot()
    name, html = idea_alerts.download(owner, result["id"])
    assert (
        name.endswith(".html") and "<script>" not in html and "&lt;script&gt;" in html
    )
    assert "Content-Security-Policy" in html and "Private research record" in html
    assert "The supplied report may challenge" in html
    assert ledger.snapshot() == budget
    with pytest.raises(service.Missing):
        idea_alerts.download(str(uuid4()), result["id"])
    with transaction(admin=True) as c:
        c.execute("UPDATE social_feeds SET enabled=false")
    try:
        _, hidden = idea_alerts.download(owner, result["id"])
        assert "interpretation" in hidden.lower() and "withheld" in hidden
        assert "The supplied report may challenge" not in hidden
    finally:
        with transaction(admin=True) as c:
            c.execute("UPDATE social_feeds SET enabled=true")


def test_different_accounts_do_not_share_private_check_requests(owner):
    iid, saved, analysis = setup(owner)
    other = str(uuid4())
    with transaction(admin=True) as c:
        c.execute(
            "INSERT INTO accounts VALUES(%s,%s)", (other, "Other fictional account")
        )
    service.save_idea(
        other,
        SaveIdea(
            instrument_id=iid,
            expected_revision=0,
            question="Another private view",
            reasoning="I expect cash generation rather than revenue headlines.",
            status="draft",
            conditions=[],
        ),
    )
    a = idea_alerts.generate(owner, iid, analysis["id"], transport=provider())
    b = idea_alerts.generate(other, iid, analysis["id"], transport=provider("context"))
    assert a["id"] != b["id"]
    with transaction(owner) as c:
        assert len(idea_alerts.list_for(c, owner)) == 1
        assert not one(c, "SELECT * FROM idea_alert_checks WHERE id=%s", (b["id"],))


def test_older_analysis_finishing_after_new_evidence_is_history_only(owner):
    iid, saved, analysis = setup(owner)

    def cached_analysis_completes():
        # A cached shared response can finish while this private call is in flight;
        # do not attempt a second paid dispatch through the global ledger.
        from psycopg.types.json import Jsonb
        from copy import deepcopy

        with transaction() as c:
            old = one(
                c, "SELECT * FROM sentiment_analyses WHERE id=%s", (analysis["id"],)
            )
            packet = deepcopy(old["packet"])
            packet["cutoff"] = datetime.now(timezone.utc).isoformat()
            c.execute(
                "INSERT INTO sentiment_analyses VALUES(%s,%s,%s,%s,%s,%s,now())",
                (
                    uuid4(),
                    iid,
                    "cached-race-" + str(uuid4()),
                    old["call_id"],
                    Jsonb(packet),
                    Jsonb(old["result"]),
                ),
            )

    result = idea_alerts.generate(
        owner,
        iid,
        analysis["id"],
        transport=provider(side_effect=cached_analysis_completes),
    )
    assert result["status"] == "historical_only"
    with transaction(owner) as c:
        assert not idea_alerts.list_for(c, owner)[0]["published"]


def test_watch_new_sources_are_not_lost_after_context_only_result(owner):
    iid, saved, analysis = setup(owner)
    news_watch.configure(owner, iid, True, match_idea=True)
    changed = newer(iid)
    idea_alerts.generate(
        owner, iid, changed["id"], automatic=True, transport=provider("context")
    )
    with transaction(owner) as c:
        row = idea_alerts.list_for(c, owner)[0]
        assert row["noteworthy_count"] == 0 and not row["published"]
    assert (
        idea_alerts.generate(
            owner,
            iid,
            changed["id"],
            automatic=True,
            transport=lambda _: pytest.fail("repeat context-only source"),
        )["status"]
        == "no_new_sources"
    )


def test_full_selected_news_and_social_sample_is_covered(owner):
    from test_sentiment import feed, add_social

    iid, saved, _ = setup(owner)
    commit(
        iid,
        [
            news(
                id=100 + i,
                url=f"https://example.test/full-{i}",
                headline=f"Microsoft company report {i}",
                summary=f"Microsoft report number {i} discusses operating costs and demand in the current period.",
            )
            for i in range(8)
        ],
    )
    posts = [
        feed(
            title=f"Microsoft discussion {i}",
            key=f"full{i}",
            body=f"My Microsoft view number {i} is about the operating margin outlook.",
        )
        for i in range(8)
    ]
    combined = (
        posts[0].split(b"<entry>")[0]
        + b"".join(
            b"<entry>" + p.split(b"<entry>", 1)[1].split(b"</feed>")[0] for p in posts
        )
        + b"</feed>"
    )
    add_social(iid, combined)
    analysis = sentiment.generate(iid, transport=sentiment_provider("positive"))
    assert len(analysis["items"]) == 16
    checked = idea_alerts.generate(
        owner, iid, analysis["id"], transport=provider("context")
    )
    with transaction(owner) as c:
        record = idea_alerts.list_for(c, owner)[0]
        assert len(record["items"]) == 16 and record["pending_source_count"] == 0
        assert len([i for i in record["items"] if i["channel"] == "social"]) == 8
