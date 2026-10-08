"""Question-specific research with mocked AI and actual restricted PostgreSQL roles."""

import json
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import psycopg
import pytest
from fastapi.testclient import TestClient
from thesis import service
from thesis.db import transaction, one, rows
from thesis.research import answers
from thesis.research.sec.service import add_company
from thesis.providers import ledger
from test_market import prepare, commit, news
from test_sentiment import add_social
from test_performance import financial_bundle
from test_sec_fundamentals import apply

QUESTION = "Does the supplied evidence confirm a Microsoft contract?"


def response(body, change=None):
    p = json.loads(body["input"][1]["content"])
    s = next(s for s in p["sources"] if s["channel"] == "news")
    cite = dict(source_id=s["id"], passage_id=s["passages"][0]["id"])
    result = dict(
        coverage="partial",
        answer="The supplied reporting does not confirm a contract.",
        answer_citations=[cite],
        answer_context_citations=[],
        evidence=[
            dict(
                kind="reported",
                text="The supplied report says Microsoft has not confirmed it.",
                citations=[cite],
                context_citations=[],
            )
        ],
        unknowns=["Whether a contract has been signed."],
        next_question="What company disclosure would establish a signed contract?",
    )
    if change:
        change(result, p)
    return dict(
        id="resp_" + str(uuid4()),
        model=body["model"],
        service_tier="default",
        status="completed",
        usage=dict(input_tokens=100, output_tokens=100),
        output=[
            dict(
                type="message",
                content=[dict(type="output_text", text=json.dumps(result))],
            )
        ],
    )


def ask(owner, iid, question=QUESTION, **kw):
    return answers.generate(
        owner, iid, answers.Ask(question=question, **kw), transport=response
    )


def test_without_idea_private_idempotent_history_and_no_monitoring_mutations(owner):
    iid = prepare(owner)
    add_social(iid)
    before = service.state(owner, iid)
    result = ask(owner, iid)
    again = answers.generate(
        owner,
        iid,
        answers.Ask(question=QUESTION),
        transport=lambda _: pytest.fail("paid duplicate"),
    )
    assert result["id"] == again["id"] and not result["withheld"]
    assert result["coverage"]["selected_social"] == 1
    with transaction(owner) as c:
        row = one(c, "SELECT * FROM research_answers WHERE id=%s", (result["id"],))
        call = one(c, "SELECT * FROM model_calls WHERE id=%s", (row["call_id"],))
        assert str(call["owner_id"]) == owner
    assert answers.history(owner, iid)["items"][0] == answers.get(owner, result["id"])
    after = service.state(owner, iid)
    for key in ["versions", "news_watch", "research_action", "updates"]:
        assert after.get(key) == before.get(key)
    assert not after["versions"]


def test_no_sources_saved_insufficient_without_model_call(owner):
    iid = add_company("AAPL")["instrument_id"]
    before = ledger.snapshot()
    result = answers.generate(
        owner,
        iid,
        answers.Ask(question="Is paid adoption reported?"),
        transport=lambda _: pytest.fail("empty sample charged"),
    )
    assert (
        result["result"]["answer"] == answers.INSUFFICIENT
        and result["result"]["model"] is None
    )
    assert ledger.snapshot() == before


def test_company_membership_and_parent_scope_checked_before_provider(owner):
    iid = prepare(owner)
    first = ask(owner, iid)
    other = str(uuid4())
    with transaction(admin=True) as c:
        c.execute("INSERT INTO accounts VALUES(%s,%s)", (other, "Other test"))
    for account, company in [
        (other, iid),
        (owner, add_company("AAPL")["instrument_id"]),
    ]:
        with pytest.raises(service.Missing):
            answers.generate(
                account,
                company,
                answers.Ask(
                    question="What evidence is missing?", parent_id=first["id"]
                ),
                transport=lambda _: pytest.fail(),
            )
    with pytest.raises(service.Missing):
        answers.get(other, first["id"])
    assert answers.history(other, iid)["items"] == []
    with pytest.raises(service.Missing):
        answers.history(other, iid, first["id"])
    other_answer = ask(other, iid)
    assert other_answer["id"] != first["id"]
    with transaction(other) as c:
        assert not rows(c, "SELECT * FROM research_answers WHERE id=%s", (first["id"],))


def test_followup_uses_previous_question_not_previous_generated_answer(owner):
    iid = prepare(owner)
    first = ask(owner, iid)

    def check(body):
        p = json.loads(body["input"][1]["content"])
        assert p["previous_question"] == QUESTION
        assert first["result"]["answer"] not in body["input"][1]["content"]
        return response(body)

    second = answers.generate(
        owner,
        iid,
        answers.Ask(question="What is still unknown?", parent_id=first["id"]),
        transport=check,
    )
    assert (
        second["parent_id"] == first["id"]
        and second["question"] == "What is still unknown?"
    )
    assert answers.get(owner, first["id"]) == first


def test_query_retrieval_dates_bounds_and_explicit_social_choice(owner):
    iid = prepare(owner)
    add_social(iid)
    now = datetime.now(timezone.utc)
    commit(
        iid,
        [
            news(
                id=20 + i,
                url=f"https://example.test/{i}",
                headline=f'Microsoft {"Copilot adoption" if i==0 else "operating margins"} item {i}',
                summary=f"Report {i} on Microsoft.",
                datetime=int((now - timedelta(minutes=20 - i)).timestamp()),
            )
            for i in range(12)
        ],
    )
    now = datetime.now(timezone.utc)
    with transaction(owner) as c:
        p = answers.prepare(
            c,
            owner,
            iid,
            answers.Ask(question="Copilot adoption?", include_social=False),
            now,
        )
        q = answers.prepare(
            c,
            owner,
            iid,
            answers.Ask(question="Operating margins?", include_social=True),
            now,
        )
    assert len([s for s in p["sources"] if s["channel"] == "news"]) == 8
    assert next(s for s in p["sources"] if s["channel"] == "news")["title"].startswith(
        "Microsoft Copilot"
    )
    assert (
        "operating margins"
        in next(s for s in q["sources"] if s["channel"] == "news")["title"]
    )
    assert (
        p["coverage"]["selected_social"] == 0 and q["coverage"]["selected_social"] == 1
    )
    assert answers.identity(owner, p) != answers.identity(owner, q)
    assert all(datetime.fromisoformat(s["available_at"]) <= now for s in q["sources"])
    assert (
        len(ledger.canonical(answers.request_for(q)).encode())
        < ledger.MAX_REQUEST_BYTES
    )
    json.dumps(q)


def test_filing_periods_code_passages_and_historical_snapshot(owner):
    iid = prepare(owner)
    apply(iid, financial_bundle())
    first = ask(owner, iid)
    filing = next(
        s
        for s in first["sources"]
        if s["channel"] == "filing" and s["id"].endswith(":quarter")
    )
    passages = {p["id"]: p["quote"] for p in filing["passages"]}
    assert "2025-01-01 to 2025-09-30" in passages["m_operating_cash"]
    assert "2025-07-01 to 2025-09-30" in passages["m_revenue"]
    assert (
        "reported" in passages["m_operating_cash"]
        and "app-calculated" in passages["m_free_cash_flow"]
    )
    changed = financial_bundle()
    changed["companyfacts"]["facts"]["us-gaap"]["Assets"]["units"]["USD"][-1][
        "val"
    ] = 250
    apply(iid, changed)
    assert answers.get(owner, first["id"])["sources"] == first["sources"]
    current = ask(owner, iid)
    assert current["id"] != first["id"]
    with transaction(admin=True) as c:
        c.execute(
            "UPDATE sources SET entitlement='fictional' WHERE id='sec-companyfacts'"
        )
    withheld = answers.get(owner, first["id"])
    assert (
        withheld["withheld"] and not withheld["sources"] and withheld["result"] is None
    )
    assert "500 USD" not in answers.download(owner, first["id"])[1]


def test_source_withdrawal_hides_history_get_and_export(owner):
    iid = prepare(owner)
    first = ask(owner, iid)
    with transaction(admin=True) as c:
        c.execute(
            "UPDATE sources SET entitlement='fictional' WHERE id LIKE 'finnhub%%'"
        )
    for item in [
        answers.get(owner, first["id"]),
        answers.history(owner, iid)["items"][0],
    ]:
        assert item["withheld"] and item["result"] is None and not item["sources"]
    html = answers.download(owner, first["id"])[1]
    assert "withheld" in html and first["result"]["answer"] not in html


@pytest.mark.parametrize(
    "mode",
    [
        "missing_source",
        "missing_passage",
        "duplicate",
        "empty_answer",
        "partial_no_gap",
        "invalid_insufficient",
        "social_fact",
        "identifier_in_prose",
    ],
)
def test_invalid_answer_rejected_without_paid_retry(owner, mode):
    iid = prepare(owner)
    add_social(iid)

    def mutate(r, p):
        if mode == "missing_source":
            r["answer_citations"][0]["source_id"] = "fake"
        elif mode == "missing_passage":
            r["answer_citations"][0]["passage_id"] = "fake"
        elif mode == "duplicate":
            r["answer_citations"] *= 2
        elif mode == "empty_answer":
            r["answer"] = "   "
        elif mode == "partial_no_gap":
            r["unknowns"] = []
        elif mode == "invalid_insufficient":
            r["coverage"] = "insufficient"
        elif mode == "identifier_in_prose":
            r["answer"] += " " + p["sources"][0]["id"]
        else:
            social = next(s for s in p["sources"] if s["channel"] == "social")
            r["evidence"][0]["citations"] = [
                dict(source_id=social["id"], passage_id="p0")
            ]

    with pytest.raises(ValueError):
        answers.generate(
            owner,
            iid,
            answers.Ask(question=QUESTION),
            transport=lambda b: response(b, mutate),
        )
    before = ledger.snapshot()
    with pytest.raises(ValueError):
        answers.generate(
            owner,
            iid,
            answers.Ask(question=QUESTION),
            transport=lambda _: pytest.fail("paid retry"),
        )
    assert ledger.snapshot() == before and answers.history(owner, iid)["items"] == []


def test_exact_passages_including_negation_are_resolved_by_code(owner):
    iid = prepare(owner)
    a = ask(owner, iid)
    for point in [dict(citations=a["result"]["answer_citations"])] + a["result"][
        "evidence"
    ]:
        for c in point["citations"]:
            s = next(s for s in a["sources"] if s["id"] == c["source_id"])
            assert (
                c["quote"] in s["title"] + "\n" + s["text"]
                and "not confirmed" in c["quote"]
            )


def test_late_completion_cannot_save_idea_or_hide_source_withdrawal(owner):
    iid = prepare(owner)

    def provider(b):
        with transaction(admin=True) as c:
            c.execute(
                "UPDATE sources SET entitlement='fictional' WHERE id LIKE 'finnhub%%'"
            )
        return response(b)

    a = answers.generate(owner, iid, answers.Ask(question=QUESTION), transport=provider)
    assert a["withheld"] and not service.state(owner, iid)["versions"]


def test_history_pages_immutable_records_and_export_escaping(owner):
    iid = add_company("AAPL")["instrument_id"]
    results = [
        ask(owner, iid, question=f"Question {i}: <script>alert(1)</script>?")
        for i in range(22)
    ]
    page = answers.history(owner, iid)
    older = answers.history(owner, iid, page["next_cursor"])
    assert (
        len(page["items"]) == 20
        and len(older["items"]) == 2
        and older["next_cursor"] is None
    )
    assert {r["id"] for r in page["items"] + older["items"]} == {
        r["id"] for r in results
    }
    name, html = answers.download(owner, results[0]["id"])
    assert (
        "<script>" not in html and "&lt;script&gt;" in html and name.endswith(".html")
    )
    with pytest.raises(psycopg.Error):
        with transaction(owner) as c:
            c.execute("DELETE FROM research_answers WHERE id=%s", (results[0]["id"],))


def test_api_session_csrf_validation_and_read_only_export(owner):
    from thesis.app import app
    from thesis.config import OWNER

    iid = add_company("AAPL")["instrument_id"]
    with TestClient(app) as client:
        assert client.get(f"/api/v1/companies/{iid}/questions").status_code == 401
        client.get("/api/v1/session")
        path = f"/api/v1/companies/{iid}/questions"
        assert client.post(path, json=dict(question=QUESTION)).status_code == 403
        headers = {"X-Thesis-Request": "local-ui"}
        assert (
            client.post(path, json=dict(question="  "), headers=headers).status_code
            == 422
        )
        assert (
            client.post(
                path,
                json=dict(question=QUESTION, include_social="false"),
                headers=headers,
            ).status_code
            == 422
        )
        r = client.post(path, json=dict(question=QUESTION), headers=headers)
        assert r.status_code == 200, r.text
        answer = r.json()["result"]
        assert client.get(path).json()["result"]["items"][0]["id"] == answer["id"]
        budget = ledger.snapshot()
        assert (
            client.get(f'/api/v1/research-answers/{answer["id"]}/export').status_code
            == 200
        )
        assert ledger.snapshot() == budget


def test_disabling_social_feed_withholds_consumed_opinion(owner):
    iid = prepare(owner)
    add_social(iid)
    a = ask(owner, iid)
    with transaction(admin=True) as c:
        previous = rows(c, "SELECT feed,enabled FROM social_feeds")
        c.execute("UPDATE social_feeds SET enabled=false")
    try:
        assert answers.get(owner, a["id"])["withheld"]
        newer = ask(owner, iid, include_social=False)
        assert not newer["withheld"] and newer["coverage"]["selected_social"] == 0
    finally:
        with transaction(admin=True) as c:
            for feed in previous:
                c.execute(
                    "UPDATE social_feeds SET enabled=%s WHERE feed=%s",
                    (feed["enabled"], feed["feed"]),
                )


def test_request_owner_and_parent_foreign_keys(owner):
    from psycopg.types.json import Jsonb

    iid = prepare(owner)
    first = ask(owner, iid)
    other = str(uuid4())
    with transaction(admin=True) as c:
        c.execute("INSERT INTO accounts VALUES(%s,%s)", (other, "Other FK account"))
    with transaction(owner) as c:
        row = one(c, "SELECT * FROM research_answers WHERE id=%s", (first["id"],))
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        with transaction(other) as c:
            c.execute(
                "INSERT INTO research_answers(id,owner_id,instrument_id,call_id,request_key,question,packet,result) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    uuid4(),
                    other,
                    iid,
                    row["call_id"],
                    "cross-owner-key",
                    QUESTION,
                    Jsonb(row["packet"]),
                    Jsonb(row["result"]),
                ),
            )
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        with transaction(other) as c:
            c.execute(
                "INSERT INTO research_answers(id,owner_id,instrument_id,parent_id,request_key,question,packet,result) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    uuid4(),
                    other,
                    iid,
                    first["id"],
                    "cross-parent-key",
                    QUESTION,
                    Jsonb(row["packet"]),
                    Jsonb(row["result"]),
                ),
            )


def test_provider_company_tag_without_target_mention_is_not_answer_evidence(owner):
    iid = prepare(owner)
    commit(
        iid,
        [
            news(
                id=99,
                headline="Oracle cloud cash flow growth",
                summary="Oracle cash flow detail.",
                url="https://example.test/oracle",
            )
        ],
    )
    with transaction(owner) as c:
        packet = answers.prepare(
            c, owner, iid, answers.Ask(question="How is cash flow growing?")
        )
    assert not any("Oracle" in s["title"] for s in packet["sources"])
    assert (
        packet["coverage"]["company_feed_news"] > packet["coverage"]["available_news"]
    )
