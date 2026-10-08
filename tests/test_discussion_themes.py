"""Shared theme reading: exact samples, scope, history, withdrawal and cost boundaries."""

import json
from copy import deepcopy
from uuid import uuid4
from datetime import datetime, timezone, timedelta
import pytest
import psycopg
from psycopg.types.json import Jsonb
from thesis import service
from thesis.db import transaction, one
from thesis.providers import ledger
from thesis.research import discussion_themes as D, sentiment, hackernews
from thesis.research.sec.service import add_company
from test_market import prepare, commit, news
from test_sentiment import provider, add_social, feed
from test_hackernews import item, transport
from test_model_budget import response as base_response


def setup(owner):
    with transaction(admin=True) as c:
        c.execute("UPDATE social_feeds SET enabled=true")
    iid = prepare(owner)
    commit(
        iid,
        [
            news(
                id=809,
                headline="Microsoft software demand",
                summary="Microsoft management expects software demand to grow. The report does not establish realised sales.",
                url="https://example.test/software",
            )
        ],
    )
    add_social(
        iid,
        feed(
            title="Microsoft software value",
            body="I like Microsoft's software features. I still find the price too high.",
        ),
    )
    hackernews.refresh(
        iid,
        fetcher=transport(
            {"1": item("1", "Microsoft software frustrates me because it crashes.")}
        ),
    )
    analysis = sentiment.generate(iid, transport=provider())
    return iid, analysis["id"]


def response(body, change=None):
    p = json.loads(body["input"][1]["content"])
    if body["text"]["format"]["name"] == "discussion_theme_evidence_check":
        return check_response(body)
    themes = []
    for scope in D.SCOPES:
        source = next((s for s in p["sources"] if s["scope"] == scope), None)
        if not source:
            continue
        passage = next(p for p in source["passages"] if p["id"] != "p0")
        main = dict(
            claims=[
                dict(
                    item_id=source["label"],
                    text="This selected text describes the author's assessment of Microsoft software.",
                    passages=[passage["id"]],
                    context_passages=(
                        [source["conversation"]["passages"][0]["id"]]
                        if source.get("conversation")
                        else []
                    ),
                )
            ]
        )
        different = None
        if scope == "reddit":
            other = source["passages"][-1]
            different = dict(
                claims=[
                    dict(
                        item_id=source["label"],
                        text="The same author also questions the price.",
                        passages=[other["id"]],
                        context_passages=[],
                    )
                ]
            )
        themes.append(
            dict(
                scope=scope,
                title="Microsoft software discussion",
                reading=main,
                differing_view=different,
                unknown="These selected texts do not establish demand across all users.",
            )
        )
    result = dict(
        themes=themes, gaps=["Selected source texts do not establish market consensus."]
    )
    if change:
        change(result, p)
    return base_response() | dict(
        model=body["model"],
        id="resp_" + str(uuid4()),
        output=[
            dict(
                type="message",
                content=[dict(type="output_text", text=json.dumps(result))],
            )
        ],
    )


def check_response(body, change=None):
    p = json.loads(body["input"][1]["content"])
    result = {
        kind: [
            dict(
                item_id=i["item_id"],
                verdict="supported",
                reason="Authored mock acceptance, not semantic evidence.",
            )
            for i in p[kind]
        ]
        for kind in ("themes", "gaps")
    }
    if change:
        change(result, p)
    return base_response() | dict(
        model=body["model"],
        id="resp_" + str(uuid4()),
        output=[
            dict(
                type="message",
                content=[dict(type="output_text", text=json.dumps(result))],
            )
        ],
    )


def packet_for(iid, aid):
    with transaction() as c:
        return D.prepare(c, iid, aid)


def test_cited_separate_scopes_cache_original_sample_and_private_state(owner):
    iid, aid = setup(owner)
    before = service.state(owner, iid)
    packet = packet_for(iid, aid)
    wire = json.loads(D.request_for(packet)["input"][1]["content"])
    assert set(wire) == {"company", "sources"}
    assert all("sentiment" not in s and "id" not in s for s in wire["sources"])
    first = D.generate(iid, aid, transport=response)
    assert (
        first["id"]
        == D.generate(iid, aid, transport=lambda _: pytest.fail("duplicate paid call"))[
            "id"
        ]
    )
    assert {t["scope"] for t in first["result"]["themes"]} == {"news", "reddit", "hackernews"}
    assert all(t["source_count"] == 1 for t in first["result"]["themes"])
    original = {s["id"]: s for s in packet["sources"]}
    for t in first["result"]["themes"]:
        for v in [t["reading"], t["differing_view"]]:
            for c in (v or {}).get("citations", []):
                assert (
                    c["quote"]
                    in (
                        original[c["source_id"]]["text"],
                        original[c["source_id"]]["title"],
                    )
                    or c["quote"] in original[c["source_id"]]["text"]
                )
    assert D.history(iid, aid)["current"]["id"] == first["id"]
    after = service.state(owner, iid)
    for key in ["versions", "news_watch", "updates", "research_action", "sentiment"]:
        assert before.get(key) == after.get(key)
    with transaction() as c:
        assert (
            one(
                c,
                "SELECT owner_id FROM model_calls WHERE id=(SELECT call_id FROM discussion_theme_reviews WHERE id=%s)",
                (first["id"],),
            )["owner_id"]
            is None
        )


@pytest.mark.parametrize(
    "fault",
    [
        "label",
        "passage",
        "scope",
        "duplicate",
        "title_only",
        "too_many",
        "same_title",
        "blank",
        "omitted",
    ],
)
def test_invalid_citation_or_theme_is_rejected(owner, fault):
    iid, aid = setup(owner)
    packet = packet_for(iid, aid)

    def change(r, p):
        theme = r["themes"][2]
        cite = theme["reading"]["claims"][0]
        if fault == "label":
            cite["item_id"] = "invented"
        elif fault == "passage":
            cite["passages"] = ["missing"]
        elif fault == "scope":
            theme["scope"] = "news"
        elif fault == "duplicate":
            cite["passages"].append(cite["passages"][0])
        elif fault == "title_only":
            cite["passages"] = ["p0"]
        elif fault == "too_many":
            for n in range(2):
                r["themes"].append(
                    deepcopy(theme) | dict(title="Extra theme number " + str(n))
                )
        elif fault == "same_title":
            r["themes"].append(deepcopy(theme))
        elif fault == "blank":
            theme["unknown"] = "       "
        elif fault == "omitted":
            cite["passages"] = ["p99"]

    if fault == "omitted":
        s = next(s for s in packet["sources"] if D.scope(s) == "hackernews")
        s["passages"].append(dict(id="p99", quote="Microsoft apparently…"))
    with pytest.raises(ValueError):
        D.render({"response_body": response(D.request_for(packet), change)}, packet)


def test_unclear_and_social_title_only_sources_are_excluded(owner):
    iid, aid = setup(owner)
    # An immutable alternate classifier result is an authored test fixture.
    with transaction() as c:
        base = one(c, "SELECT * FROM sentiment_analyses WHERE id=%s", (aid,))
        selected = base["packet"]["sources"]
        social_source = next(s for s in selected if D.scope(s) == "hackernews")
        social_source["text"] = ""
        social_source["passages"] = [dict(id="p0", quote=social_source["title"])]
        base["result"]["items"][0]["relevance"] = "unclear"
        new_id = uuid4()
        c.execute(
            "INSERT INTO sentiment_analyses(id,instrument_id,request_key,call_id,packet,result) VALUES(%s,%s,%s,%s,%s,%s)",
            (
                new_id,
                iid,
                str(new_id),
                base["call_id"],
                Jsonb(base["packet"]),
                Jsonb(base["result"]),
            ),
        )
    packet = packet_for(iid, str(new_id))
    assert social_source["id"] not in {s["id"] for s in packet["sources"]}
    assert packet["coverage"]["excluded"] >= 1


def test_wrong_company_analysis_and_history_membership_have_no_charge(owner):
    iid, aid = setup(owner)
    other = add_company("AAPL")["instrument_id"]
    before = ledger.snapshot()
    for action in [
        lambda: D.generate(other, aid, transport=response),
        lambda: D.history(other, aid),
        lambda: D.history(str(uuid4())),
    ]:
        with pytest.raises(service.Missing):
            action()
    assert ledger.snapshot() == before
    assert D.history(other)["items"] == []


def test_withdrawal_hides_current_history_export_and_blocks_new_call(owner):
    iid, aid = setup(owner)
    saved = D.generate(iid, aid, transport=response)
    with transaction(admin=True) as c:
        c.execute("UPDATE social_feeds SET enabled=false")
    before = ledger.snapshot()
    assert D.get(iid, saved["id"])["result"] is None
    assert D.history(iid, aid)["current"]["withheld"]
    assert D.history(iid)["items"][0]["sources"] == []
    _, html = D.download(iid, saved["id"])
    assert "withheld" in html and "software demand" not in html
    with pytest.raises(ValueError):
        D.generate(iid, aid, transport=response)
    assert ledger.snapshot() == before
    with transaction(admin=True) as c:
        c.execute("UPDATE social_feeds SET enabled=true")


def test_history_pagination_preserves_selected_analysis_and_record_integrity(owner):
    iid, aid = setup(owner)
    saved = D.generate(iid, aid, transport=response)
    with transaction() as c:
        row = one(
            c, "SELECT * FROM discussion_theme_reviews WHERE id=%s", (saved["id"],)
        )
        for n in range(21):
            c.execute(
                "INSERT INTO discussion_theme_reviews VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    uuid4(),
                    iid,
                    aid,
                    "authored-page-" + str(n),
                    row["call_id"],
                    Jsonb(row["packet"]),
                    Jsonb(row["result"]),
                    row["created_at"] - timedelta(minutes=n + 1),
                ),
            )
    first = D.history(iid, aid)
    second = D.history(iid, aid, first["next_cursor"])
    assert len(first["items"]) == 20 and len(second["items"]) == 2
    assert not {r["id"] for r in first["items"]} & {r["id"] for r in second["items"]}
    assert second["current"]["id"] == saved["id"] and second["next_cursor"] is None
    other = add_company("AAPL")["instrument_id"]
    for action in [
        lambda: D.history(other, before=first["next_cursor"]),
        lambda: D.get(other, saved["id"]),
    ]:
        with pytest.raises(service.Missing):
            action()
    for query, source in [
        ("DELETE FROM discussion_theme_reviews", False),
        ("UPDATE discussion_theme_reviews SET result='{}'", False),
        ("SELECT * FROM discussion_theme_reviews", True),
    ]:
        with pytest.raises(psycopg.Error):
            with transaction(source=source) as c:
                c.execute(query)


def test_changed_analysis_uses_new_record_without_overwriting_old(owner):
    iid, aid = setup(owner)
    first = D.generate(iid, aid, transport=response)
    commit(
        iid,
        [
            news(
                id=810,
                headline="Microsoft later software report",
                summary="Microsoft users report a changed product experience.",
                url="https://example.test/later",
            )
        ],
    )
    new = sentiment.generate(iid, transport=provider())
    assert new["id"] != aid and D.history(iid, new["id"])["current"] is None
    second = D.generate(iid, new["id"], transport=response)
    assert first["id"] != second["id"] and D.get(iid, first["id"]) == first


@pytest.mark.parametrize(
    "fault", ["incomplete", "missing_gap", "long_gap", "empty_gap"]
)
def test_failed_model_reading_never_publishes_or_retries(owner, fault):
    iid, aid = setup(owner)
    calls = []

    def bad(b):
        calls.append(1)
        r = response(
            b,
            lambda r, p: r.update(
                themes=[],
                gaps=(
                    []
                    if fault == "missing_gap"
                    else (
                        [" " * 5]
                        if fault == "empty_gap"
                        else (
                            ["x" * 241] if fault == "long_gap" else ["No usable theme."]
                        )
                    )
                ),
            ),
        )
        if fault == "incomplete":
            r["status"] = "incomplete"
        return r

    with pytest.raises(ValueError):
        D.generate(iid, aid, transport=bad)
    assert len(calls) == 1 and D.history(iid, aid)["current"] is None


def test_empty_reading_and_inert_export(owner):
    iid, aid = setup(owner)
    saved = D.generate(
        iid,
        aid,
        transport=lambda b: response(
            b,
            lambda r, p: r.update(
                themes=[], gaps=["<script>test</script> is authored gap text."]
            ),
        ),
    )
    _, html = D.download(iid, saved["id"])
    assert (
        "<script>" not in html
        and "&lt;script&gt;" in html
        and "default-src 'none'" in html
    )
    assert saved["result"]["themes"] == []


def test_source_change_during_synthesis_prevents_second_paid_step(owner):
    iid, aid = setup(owner)

    def withdraw(b):
        with transaction(admin=True) as c:
            c.execute("UPDATE social_feeds SET enabled=false")
        return response(b)

    before = ledger.snapshot()["calls"]
    with pytest.raises(ValueError, match="Source access changed"):
        D.generate(iid, aid, transport=withdraw)
    assert ledger.snapshot()["calls"] == before + 1
    assert D.history(iid, aid)["current"] is None
    with transaction(admin=True) as c:
        c.execute("UPDATE social_feeds SET enabled=true")


def test_no_relevant_passages_make_no_paid_request(owner):
    iid = prepare(owner)
    a = sentiment.generate(
        iid,
        transport=provider(
            mutate=lambda items: [
                dict(i, relevance="unrelated", sentiment="unclear", basis="unclear")
                for i in items
            ]
        ),
    )
    before = ledger.snapshot()
    with pytest.raises(ValueError, match="no eligible"):
        D.generate(iid, a["id"], transport=lambda _: pytest.fail("empty request"))
    assert ledger.snapshot() == before


def test_theme_api_rejects_foreign_sample_and_export_and_reads_without_model(owner):
    from fastapi.testclient import TestClient
    from thesis.app import app

    iid, aid = setup(owner)
    saved = D.generate(iid, aid, transport=response)
    other = add_company("AAPL")["instrument_id"]
    client = TestClient(app, base_url="http://127.0.0.1")
    assert (
        client.get("/api/v1/companies/" + iid + "/discussion-themes").status_code == 401
    )
    client.get("/api/v1/session")
    before = ledger.snapshot()
    h = client.get(f"/api/v1/companies/{iid}/discussion-themes?analysis_id={aid}")
    assert h.status_code == 200 and h.json()["result"]["current"]["id"] == saved["id"]
    assert (
        client.get(
            f"/api/v1/companies/{other}/discussion-themes?analysis_id={aid}"
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/companies/{other}/discussion-themes/{saved['id']}/export"
        ).status_code
        == 404
    )
    export = client.get(
        f"/api/v1/companies/{iid}/discussion-themes/{saved['id']}/export"
    )
    assert (
        export.status_code == 200
        and "attachment;" in export.headers["content-disposition"]
    )
    assert ledger.snapshot() == before


def test_reddit_title_can_add_context_but_never_replace_body_evidence(owner):
    iid, aid = setup(owner)
    packet = packet_for(iid, aid)

    def extra_title(r, p):
        r["themes"][1]["reading"]["claims"][0]["passages"].insert(0, "p0")

    result = D.render(
        {"response_body": response(D.request_for(packet), extra_title)}, packet
    )
    assert len(result["themes"][1]["reading"]["citations"]) == 2

    def title_only(r, p):
        extra_title(r, p)
        r["themes"][1]["reading"]["claims"][0]["passages"] = ["p0"]

    with pytest.raises(ValueError, match="body evidence"):
        D.render({"response_body": response(D.request_for(packet), title_only)}, packet)
    wire = json.loads(D.request_for(packet)["input"][1]["content"])
    assert all(
        p["id"] != "p0"
        for s in wire["sources"]
        if s["scope"] == "hackernews"
        for p in s["passages"]
    )


def test_every_claim_keeps_its_own_source_and_quotes(owner):
    iid, aid = setup(owner)
    packet = packet_for(iid, aid)
    news_sources = [s for s in packet["sources"] if D.scope(s) == "news"]
    assert len(news_sources) >= 2

    def two(r, p):
        other = next(
            s
            for s in p["sources"]
            if s["scope"] == "news"
            and s["label"] != r["themes"][0]["reading"]["claims"][0]["item_id"]
        )
        r["themes"][0]["reading"]["claims"].append(
            dict(
                item_id=other["label"],
                text="A separate report gives an explicitly unconfirmed contract claim.",
                passages=[other["passages"][-1]["id"]],
            )
        )

    result = D.render({"response_body": response(D.request_for(packet), two)}, packet)
    view = result["themes"][0]["reading"]
    assert (
        len(view["claims"]) == 2 and len({c["source_id"] for c in view["claims"]}) == 2
    )
    for claim in view["claims"]:
        assert {q["source_id"] for q in claim["citations"]} == {claim["source_id"]}
    assert result["themes"][0]["source_count"] == 2


@pytest.mark.parametrize(
    "fault",
    ["duplicate_source", "blank_claim", "long_claim", "cross_scope", "old_wire"],
)
def test_unbounded_or_mixed_claims_are_rejected(owner, fault):
    iid, aid = setup(owner)
    packet = packet_for(iid, aid)

    def bad(r, p):
        view = r["themes"][0]["reading"]
        claim = view["claims"][0]
        if fault == "duplicate_source":
            view["claims"].append(dict(claim))
        elif fault == "blank_claim":
            claim["text"] = "     "
        elif fault == "long_claim":
            claim["text"] = "x" * 221
        elif fault == "cross_scope":
            claim["item_id"] = next(
                s["label"] for s in p["sources"] if s["scope"] == "reddit"
            )
        else:
            r["themes"][0]["reading"] = dict(
                text="Old provider wire must not be silently reinterpreted.",
                citations=[],
            )

    with pytest.raises(ValueError):
        D.render({"response_body": response(D.request_for(packet), bad)}, packet)


def test_each_social_claim_requires_body_even_when_another_claim_has_it(owner):
    iid, aid = setup(owner)
    packet = packet_for(iid, aid)
    source = deepcopy(next(s for s in packet["sources"] if D.scope(s) == "reddit"))
    source["label"] = "item_extra"
    source["id"] = str(uuid4())
    packet["sources"].append(source)

    def bad(r, p):
        r["themes"][1]["reading"]["claims"].append(
            dict(
                item_id="item_extra",
                text="This claim relies on a title alone.",
                passages=["p0"],
            )
        )

    with pytest.raises(ValueError, match="body evidence"):
        D.render({"response_body": response(D.request_for(packet), bad)}, packet)


def legacy_fixture(iid, saved):
    """Append an explicitly authored old-format record; never change historical rows."""
    with transaction() as c:
        row = one(
            c, "SELECT * FROM discussion_theme_reviews WHERE id=%s", (saved["id"],)
        )
        old = deepcopy(row["result"])
        old.pop("format_version", None)
        old.pop("evidence_policy", None)
        old.pop("context_policy", None)
        old["prompt_version"] = "thesis-discussion-themes-3"
        for t in old["themes"]:
            for v in [t["reading"], t["differing_view"]]:
                if v:
                    v.pop("claims", None)
        key = str(uuid4())
        c.execute(
            "INSERT INTO discussion_theme_reviews VALUES(%s,%s,%s,%s,%s,%s,%s,now())",
            (
                key,
                iid,
                row["analysis_id"],
                "authored-legacy-" + key,
                row["call_id"],
                Jsonb(row["packet"]),
                Jsonb(old),
            ),
        )
    return key, old


def test_legacy_reading_remains_exact_and_exportable_with_method_warning(owner):
    iid, aid = setup(owner)
    saved = D.generate(iid, aid, transport=response)
    key, old = legacy_fixture(iid, saved)
    before = D.get(iid, key)
    assert before["result"] == old and before["earlier_method"]
    _, html = D.download(iid, key)
    assert "earlier interpretation method" in html and old["themes"][0]["reading"][
        "text"
    ] in __import__("html").unescape(html)
    repeat = D.generate(
        iid,
        aid,
        transport=lambda _: pytest.fail("cached current reading should not dispatch"),
    )
    assert repeat["id"] == saved["id"] and D.get(iid, key) == before
    _, current_html = D.download(iid, saved["id"])
    assert "Example Wire" in current_html and "price too high" in current_html


def test_distinct_claims_from_one_source_are_not_independent_sources(owner):
    iid, aid = setup(owner)
    packet = packet_for(iid, aid)

    def two(r, p):
        first = r["themes"][0]["reading"]["claims"][0]
        r["themes"][0]["reading"]["claims"].append(
            dict(
                first, text="A different short finding from this same authored report."
            )
        )

    r = D.render({"response_body": response(D.request_for(packet), two)}, packet)
    assert len(r["themes"][0]["reading"]["claims"]) == 2
    assert r["themes"][0]["source_count"] == 1


def test_title_context_is_exact_labelled_and_never_restores_omitted_fragments(owner):
    iid, aid = setup(owner)
    packet = packet_for(iid, aid)
    r = D.render({"response_body": response(D.request_for(packet))}, packet)
    sources = {s["id"]: s for s in packet["sources"]}
    for t in r["themes"]:
        c = t["reading"]["claims"][0]
        titles = [q for q in c["citations"] if q["role"] == "source_title"]
        if t["scope"] == "hackernews":
            assert titles == []
        else:
            assert (
                len(titles) == 1
                and titles[0]["quote"] == sources[c["source_id"]]["title"]
            )
    assert r["evidence_policy"] == D.EVIDENCE_POLICY
    for source in packet["sources"]:
        if D.scope(source) == "news":
            source["title"] = "Microsoft incomplete headline…"
    r = D.render({"response_body": response(D.request_for(packet))}, packet)
    assert all(
        q["role"] != "source_title"
        for t in r["themes"]
        if t["scope"] == "news"
        for c in t["reading"]["claims"]
        for q in c["citations"]
    )
