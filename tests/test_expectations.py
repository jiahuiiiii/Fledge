"""Expectation history, exact evidence and shared/private boundaries; mocked AI."""

import json
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb
from thesis import service
from thesis.db import transaction, one, rows
from thesis.providers import ledger
from thesis.research import expectations as E
from thesis.research.sec.service import add_company
from test_market import prepare, commit, news

TEXT = "Microsoft management expects about $175 billion of capital spending in calendar 2026. The outlook remains conditional on demand."


def setup(owner):
    iid = prepare(owner)
    commit(
        iid,
        [
            news(
                id=801,
                headline="Microsoft spending outlook",
                summary=TEXT,
                url="https://example.test/outlook",
            )
        ],
    )
    return iid


def response(body, change=None):
    packet = json.loads(body["input"][1]["content"])
    source = next(
        s for s in packet["sources"] if s["title"] == "Microsoft spending outlook"
    )
    passage = next(p for p in source["passages"] if "management expects" in p["quote"])
    result = dict(
        items=[
            dict(
                source_id=source["id"],
                category="management_outlook",
                summary="The report attributes conditional capital-spending expectations to Microsoft management.",
                passages=[passage["id"]],
                attribution_quote="Microsoft management",
                value_quote="about $175 billion of capital spending",
                horizon_quote="calendar 2026",
                change="not_stated",
                change_quote=None,
            )
        ],
        gaps=["The original company statement is not in this sample."],
    )
    if change:
        change(result, packet)
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


def test_shared_cached_reading_does_not_include_private_reasoning_or_change_watches(
    owner,
):
    iid = setup(owner)
    before = service.state(owner, iid)
    result = E.generate(iid, transport=response)
    repeat = E.generate(
        iid, transport=lambda _: pytest.fail("unchanged extraction charged twice")
    )
    assert result["id"] == repeat["id"]
    assert result["result"]["items"][0]["horizon_quote"] == "calendar 2026"
    with transaction() as c:
        row = one(c, "SELECT * FROM expectation_reviews WHERE id=%s", (result["id"],))
        assert set(row["packet"]) == {
            "instrument_id",
            "company",
            "cutoff",
            "sources",
            "coverage",
        }
        call = one(c, "SELECT owner_id FROM model_calls WHERE id=%s", (row["call_id"],))
        assert call["owner_id"] is None
    after = service.state(owner, iid)
    for field in ["versions", "news_watch", "updates", "research_action"]:
        assert before.get(field) == after.get(field)
    assert E.history(iid)["latest"]["id"] == result["id"]
    assert E.history(iid)["sample_changed"] is False
    assert E.get(iid, result["id"]) == result


@pytest.mark.parametrize(
    "field,value",
    [
        ("attribution_quote", "Apple management"),
        ("value_quote", "$999 billion"),
        ("horizon_quote", "fiscal 2027"),
        ("change_quote", "raised its forecast"),
        ("passages", ["invented"]),
        ("source_id", "invented"),
        ("value_quote", ""),
        ("value_quote", "about $175 … spending"),
    ],
)
def test_fabricated_wording_or_wrong_source_is_rejected(owner, field, value):
    iid = setup(owner)
    with transaction() as c:
        packet = E.prepare(c, iid)
    raw = response(
        E.request_for(packet), lambda r, p: r["items"][0].update({field: value})
    )
    with pytest.raises(ValueError):
        E.render({"response_body": raw}, packet)


def test_explicit_revision_requires_quote_and_unknown_fields_remain_unknown(owner):
    iid = setup(owner)
    with transaction() as c:
        packet = E.prepare(c, iid)
    raw = response(
        E.request_for(packet), lambda r, p: r["items"][0].update(change="raised")
    )
    with pytest.raises(ValueError):
        E.render({"response_body": raw}, packet)
    raw = response(
        E.request_for(packet),
        lambda r, p: r["items"][0].update(value_quote=None, horizon_quote=None),
    )
    item = E.render({"response_body": raw}, packet)["items"][0]
    assert item["value_quote"] is None and item["horizon_quote"] is None


def test_no_qualifying_expectations_is_not_no_risk_or_absent_everywhere(owner):
    iid = setup(owner)
    result = E.generate(
        iid,
        transport=lambda b: response(
            b,
            lambda r, p: r.update(
                items=[],
                gaps=["No attributed outlook is established by these passages."],
            ),
        ),
    )
    assert not result["result"]["items"]
    assert result["result"]["gaps"]
    assert "sample" in result["result"]["limitation"]


def test_empty_pool_has_no_charge_and_unknown_company_rejected(owner):
    iid = add_company("AAPL")["instrument_id"]
    before = ledger.snapshot()
    assert E.history(iid)["latest"] is None
    with pytest.raises(ValueError):
        E.generate(iid, transport=lambda _: pytest.fail("empty source call"))
    with pytest.raises(service.Missing):
        E.history(str(uuid4()))
    assert ledger.snapshot() == before


def test_actual_source_withdrawal_hides_result_sources_history_and_export(owner):
    iid = setup(owner)
    result = E.generate(iid, transport=response)
    with transaction(admin=True) as c:
        c.execute("UPDATE sources SET entitlement='fictional' WHERE id='finnhub-news'")
    row = E.get(iid, result["id"])
    assert row["withheld"] and row["result"] is None and row["sources"] == []
    assert E.history(iid)["latest"]["withheld"]
    _, html = E.download(iid, result["id"])
    assert "withheld" in html and "$175" not in html


def test_immutable_history_and_source_role_cannot_read_generated_research(owner):
    iid = setup(owner)
    result = E.generate(iid, transport=response)
    with pytest.raises(psycopg.Error):
        with transaction() as c:
            c.execute(
                "UPDATE expectation_reviews SET result='{}'::jsonb WHERE id=%s",
                (result["id"],),
            )
    with pytest.raises(psycopg.Error):
        with transaction(source=True) as c:
            c.execute("SELECT * FROM expectation_reviews")


def test_changed_sources_create_new_history_without_rewriting_old(owner):
    iid = setup(owner)
    first = E.generate(iid, transport=response)
    commit(
        iid,
        [
            news(
                id=802,
                headline="Microsoft revised outlook",
                summary="Microsoft management withdrew its outlook after demand changed.",
                url="https://example.test/revision",
            )
        ],
    )
    assert E.history(iid)["sample_changed"]
    second = E.generate(iid, transport=response)
    assert first["id"] != second["id"]
    assert E.get(iid, first["id"]) == first
    assert len(E.history(iid)["items"]) == 2


def test_pagination_latest_cutoff_and_wrong_company_cursor(owner):
    iid = setup(owner)
    first = E.generate(iid, transport=response)
    with transaction() as c:
        original = one(
            c, "SELECT * FROM expectation_reviews WHERE id=%s", (first["id"],)
        )
        for n in range(21):
            packet = deepcopy(original["packet"])
            packet["cutoff"] = (
                datetime.fromisoformat(packet["cutoff"]) - timedelta(days=n + 1)
            ).isoformat()
            c.execute(
                "INSERT INTO expectation_reviews VALUES(%s,%s,%s,%s,%s,%s,now())",
                (
                    uuid4(),
                    iid,
                    "authored-history-" + str(n),
                    original["call_id"],
                    Jsonb(packet),
                    Jsonb(original["result"]),
                ),
            )
    h = E.history(iid)
    assert (
        h["latest"]["id"] == first["id"] and len(h["items"]) == 20 and h["next_cursor"]
    )
    older = E.history(iid, h["next_cursor"])
    assert len(older["items"]) == 2 and not older["next_cursor"]
    assert not {r["id"] for r in h["items"]} & {r["id"] for r in older["items"]}
    other = add_company("AAPL")["instrument_id"]
    with pytest.raises(service.Missing):
        E.history(other, h["next_cursor"])
    with pytest.raises(service.Missing):
        E.get(other, first["id"])


def test_export_escapes_generated_prose_and_keeps_source_metadata(owner):
    iid = setup(owner)
    result = E.generate(
        iid,
        transport=lambda b: response(
            b,
            lambda r, p: r["items"][0].update(
                summary="<script>danger</script> is authored test prose."
            ),
        ),
    )
    _, html = E.download(iid, result["id"])
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert (
        "calendar 2026" in html
        and "about $175 billion" in html
        and "https://example.test/outlook" in html
    )
    assert "default-src 'none'" in html


def test_gap_source_references_render_with_original_titles(owner):
    iid = setup(owner)
    result = E.generate(
        iid,
        transport=lambda body: response(
            body,
            lambda r, p: r.update(
                gaps=["No confirmed outcome in " + r["items"][0]["source_id"] + "."]
            ),
        ),
    )
    assert result["result"]["gaps"] == [
        "No confirmed outcome in “Microsoft spending outlook”."
    ]


def test_current_sample_can_reuse_older_reading_without_claiming_latest_cutoff(
    owner, monkeypatch
):
    iid = setup(owner)
    with transaction() as c:
        initial_packet = E.prepare(c, iid)
    first = E.generate(iid, transport=response)
    commit(
        iid,
        [
            news(
                id=908,
                headline="Microsoft newer report",
                summary="Microsoft has not issued a replacement outlook.",
                url="https://example.test/newer",
            )
        ],
    )
    second = E.generate(iid, transport=response)
    monkeypatch.setattr(E, "prepare", lambda *a, **k: initial_packet)
    history = E.history(iid)
    assert history["latest"]["id"] == second["id"]
    assert history["current_reading"]["id"] == first["id"]
    assert (
        E.generate(
            iid, transport=lambda _: pytest.fail("cached older reading charged")
        )["id"]
        == first["id"]
    )


def test_api_requires_local_session_and_mutation_header_and_reads_are_free(
    owner, monkeypatch
):
    from thesis.app import app

    iid = setup(owner)
    E.generate(iid, transport=response)
    monkeypatch.setattr(
        E, "generate", lambda *a, **k: pytest.fail("read invoked generation")
    )
    with TestClient(app) as c:
        assert c.get(f"/api/v1/companies/{iid}/expectations").status_code == 401
        c.get("/api/v1/session")
        assert c.post(f"/api/v1/companies/{iid}/expectations").status_code == 403
        assert c.get(f"/api/v1/companies/{iid}/expectations").status_code == 200
