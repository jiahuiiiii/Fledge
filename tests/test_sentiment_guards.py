"""Deterministic regression cases, not a live model accuracy evaluation."""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import json
import pytest
from psycopg.types.json import Jsonb
from thesis.db import transaction, one
from thesis.research import sentiment as S, sentiment_guards as G
from thesis.providers import ledger
from test_market import prepare
from test_sentiment import add_social, feed, provider

COMPANY = dict(symbol="AVGO", name="Broadcom Inc.")
AT = datetime(2026, 10, 8, 21, tzinfo=timezone.utc)


def snapshot(**changes):
    value = dict(id=str(uuid4()), symbol="AVGO", retrieved_at=AT-timedelta(minutes=10),
                 series=dict(symbol="AVGO", currency="USD", interval="1d",
                             exchange_timezone="America/New_York", basis="Authored USD OHLC fixture.",
                             bars=[dict(date="2026-10-08", close="360.14", provisional=False)]))
    value.update(changes)
    return value


def source(text, ref=True):
    value = dict(id="source-1", channel="social", platform="reddit", title="Reddit comment",
                 published_at=AT.isoformat(), passages=[dict(id="p1", quote=text)])
    if ref:
        value["price_reference"] = G.reference(snapshot(), value, COMPANY)
    return value


def item(**changes):
    return S.Item.model_validate(dict(id="item_1", relevance="relevant", sentiment="positive",
         statement="opinion", topic="valuation", passages=["p1"], previous_passages=[],
         context_passages=[], basis="expressed_evaluation") | changes)


def claim(text="$340", direction=None, kind="price_target"):
    return dict(passage_id="p1", amount_text=text, kind=kind, direction_text=direction)


@pytest.mark.parametrize("text,rule", [
    ("AVGO to $340", "bare_price_target"), ("$AVGO $340", "bare_price_target"),
    ("Broadcom price target: $340", "bare_price_target"),
    ("AVGO", "bare_ticker_or_number"), ("340", "bare_ticker_or_number"),
    ("Will AVGO fall?", "question_only"), ("Should I buy AVGO?", "question_only"),
])
def test_weak_direction_is_downgraded_even_without_model_price_extraction(text, rule):
    value = G.apply(item(), source(text), COMPANY)
    assert value["sentiment"] == value["basis"] == "unclear"
    assert value["guard"]["rule"] == rule and value["guard"]["model_sentiment"] == "positive"


@pytest.mark.parametrize('tone', ['positive','negative','mixed','neutral'])
def test_bare_target_cannot_become_a_direction_or_a_neutral_fact(tone):
    basis='descriptive' if tone=='neutral' else 'expressed_evaluation'
    assert G.apply(item(sentiment=tone,basis=basis),source('AVGO to $340'),COMPANY)['sentiment']=='unclear'


@pytest.mark.parametrize("text", ["I love Broadcom.", "I am buying the dip in AVGO.",
    "I now respect Broadcom, although I used to dislike it.", "AVGO looks undervalued.",
    "Broadcom is a great business.", "I hate Broadcom's product."])
def test_clear_evaluation_controls_are_not_downgraded(text):
    assert not G.apply(item(), source(text), COMPANY)["guard"]["applied"]


@pytest.mark.parametrize("text", ["Broadcom has a top credit rating; relax.",
    "Stock price been tanking for months now.", "Both readings are worse than the one I originally saw."])
def test_no_general_word_list_replaces_semantic_reading(text):
    assert not G.apply(item(), source(text), COMPANY)["guard"]["applied"]


def test_question_beside_separate_stance_is_not_flattened():
    s = source("I love Broadcom.")
    s["passages"].append(dict(id="p2", quote="Should I buy more?"))
    assert not G.apply(item(passages=["p1", "p2"]), s, COMPANY)["guard"]["applied"]


def test_actual_340_case_has_exact_arithmetic_but_stays_unclear():
    value = G.apply(item(price_claims=[claim()]), source("AVGO to $340"), COMPANY)
    price = value["price_comparisons"][0]
    assert value["sentiment"] == "unclear" and price["relation"] == "below"
    from decimal import Decimal
    assert Decimal(price["difference_percent"]) == (Decimal(340)-Decimal("360.14"))/Decimal("360.14")*100
    assert price["reference"]["date"] == "2026-10-08"
    assert price["author_direction"] == "not_stated"


def test_sentence_punctuation_does_not_change_a_supported_target():
    value=G.apply(item(price_claims=[claim()]), source('AVGO to $340.'), COMPANY)
    assert value['price_comparisons'][0]['status']=='compared'
    assert G.number('$1,234.56') == G.Decimal('1234.56')


def test_feed_update_never_becomes_verified_post_time_even_with_a_supplied_reference():
    s=source('AVGO to $340');s['timestamp_basis']='feed_updated'
    result=G.apply(item(price_claims=[claim()]),s,COMPANY)
    assert result['price_comparisons'][0]['status']=='unverified_post_time'
    assert 'difference_percent' not in result['price_comparisons'][0]


@pytest.mark.parametrize("text,direction,tone,expected", [
    ("AVGO will fall to $340", "fall", "negative", None),
    ("AVGO will rise to $400", "rise", "positive", None),
    ("AVGO will rise to $340", "rise", "positive", "price_direction_conflict"),
    ("AVGO will fall to $340", "fall", "positive", "price_label_conflict"),
    ("AVGO might fall to $340", "fall", "negative", "price_direction_unstated"),
    ("AVGO will not rise to $340", "rise", "positive", "price_direction_unstated"),
])
def test_price_only_direction_requires_compatible_explicit_context(text, direction, tone, expected):
    token = G.MONEY.search(text)[0]
    value = G.apply(item(sentiment=tone, price_claims=[claim(token, direction)]), source(text), COMPANY)
    assert value["guard"]["rule"] == expected


def test_directional_price_only_without_saved_close_stays_unclear_even_if_extraction_misses_it():
    value = G.apply(item(sentiment="negative"), source("AVGO will fall to $340", ref=False), COMPANY)
    assert value["guard"]["rule"] == "price_reference_unavailable"


@pytest.mark.parametrize("kind", ["option_strike", "historical_price", "other"])
def test_non_target_amounts_are_never_compared_as_price_targets(kind):
    value = G.apply(item(price_claims=[claim(kind=kind)]), source("AVGO to $340"), COMPANY)
    assert value["price_comparisons"][0]["status"] == "not_comparable_target"


@pytest.mark.parametrize("text", ["NVDA to $340, unlike AVGO.", "AVGO and NVDA to $340.", "AVGO revenue is $340bn.", "AVGO to C$340.", "AVGO to $340–$350.", "AVGO to $340 billion."])
def test_cross_company_non_usd_and_unsupported_units_are_not_arithmetic_inputs(text):
    value = G.apply(item(price_claims=[claim()]), source(text), COMPANY)
    assert value["price_comparisons"][0]["status"] == "not_comparable_target"


@pytest.mark.parametrize("change", [dict(amount_text="$341"), dict(passage_id="p2"), dict(direction_text="fall")])
def test_invented_price_extraction_is_rejected(change):
    with pytest.raises(ValueError):
        G.apply(item(price_claims=[claim() | change]), source("AVGO to $340"), COMPANY)


def test_reference_never_uses_future_capture_provisional_close_or_stale_price():
    s = source("AVGO to $340", ref=False)
    assert G.reference(snapshot(retrieved_at=AT+timedelta(seconds=1)), s, COMPANY)["status"] == "no_compatible_saved_price"
    snap = snapshot(); snap["series"]["bars"][0]["provisional"] = True
    assert G.reference(snap, s, COMPANY)["status"] == "no_completed_close"
    snap = snapshot(); snap["series"]["bars"][0]["date"] = "2026-09-20"
    assert G.reference(snap, s, COMPANY)["status"] == "saved_close_too_old"
    s["timestamp_basis"] = "feed_updated"
    assert G.reference(snapshot(), s, COMPANY)["status"] == "unverified_post_time"


@pytest.mark.parametrize("key,value", [("symbol","NVDA"),("currency","CAD"),("interval","1m"),("exchange_timezone","UTC")])
def test_reference_requires_same_company_currency_and_daily_exchange_basis(key,value):
    snap = snapshot(); snap["series"][key] = value
    assert G.reference(snap, source("AVGO to $340",ref=False), COMPANY)["status"] == "no_compatible_saved_price"


def test_saved_historical_reference_is_read_only_pinned_and_never_model_context(owner):
    iid = prepare(owner)
    with transaction(admin=True) as conn:
        conn.execute("INSERT INTO sources VALUES('yahoo-price-history','Yahoo fixture','local-yahoo-history') ON CONFLICT DO NOTHING")
        for at, close in [(AT-timedelta(minutes=10), "360.14"), (AT+timedelta(minutes=1), "999")]:
            snap = snapshot(retrieved_at=at); snap["symbol"] = snap["series"]["symbol"] = "MSFT"
            snap["series"]["bars"][0]["close"] = close
            conn.execute("INSERT INTO price_history_snapshots VALUES(%s,%s,%s,%s,%s,%s,%s)", (snap["id"],iid,"MSFT",Jsonb({}),Jsonb(snap["series"]),"fixture",at))
    sources = [source("MSFT to $340",ref=False)]
    with transaction(consistent=True) as conn:
        G.attach(conn,iid,sources,dict(symbol="MSFT",name="Microsoft Corporation"))
    assert sources[0]["price_reference"]["close"] == "360.14"
    from test_sentiment_batching import packet
    p = packet(); p["sources"][0]["price_reference"] = sources[0]["price_reference"]
    sent = S.request_for(p)
    assert "snapshot_id" not in sent["input"][1]["content"] and "360.14" not in sent["input"][1]["content"]
    before, model_before = S.identity(p), S.model_identity(p)
    p["sources"][0]["price_reference"]["close"] = "360"
    assert S.identity(p) != before and S.model_identity(p) == model_before


def test_new_schema_requires_source_bound_extractions_and_news_has_none():
    from test_sentiment_batching import packet
    p=packet(); schema=S.request_for(p)["text"]["format"]["schema"]
    for source_, branch in zip(p["sources"], schema["properties"]["items"]["items"]["anyOf"]):
        assert "price_claims" in branch["required"]
        assert branch["properties"]["price_claims"]["items"]["properties"]["passage_id"]["enum"] == [p["id"] for p in source_["passages"]]
        if source_["channel"] == "news": assert branch["properties"]["price_claims"]["maxItems"] == 0


def test_price_withdrawal_withholds_derived_reading_without_changing_history(owner):
    from thesis.research import sentiment_batching
    iid=prepare(owner); add_social(iid)
    with transaction() as conn:
        p=S.prepare(conn,iid)
    p['sources'][-1]['price_reference']=dict(status='available',close='360',snapshot_id=str(uuid4()))
    record=dict(id=str(uuid4()),instrument_id=iid,packet=p,result=dict(items=[{'sentiment':'positive'}]),created_at=AT)
    with transaction(admin=True) as conn:
        conn.execute("DELETE FROM sources WHERE id='yahoo-price-history'")
    original=deepcopy(record)
    with transaction(consistent=True) as conn:
        assert S.present(conn,record)['withheld']
        with pytest.raises(ValueError,match='access changed'):
            sentiment_batching.check_access(conn,p)
    assert record==original


def test_generation_counts_checked_labels_and_preserves_raw_call_and_cache(owner):
    iid=prepare(owner); add_social(iid, feed(title="Microsoft to $340", body="MSFT to $340"))
    with transaction() as conn:
        packet = S.prepare(conn, iid)
    S.render({"response_body": provider("positive")(S.request_for(packet))}, packet)
    value=S.generate(iid,transport=provider("positive"))
    selected=next(i for i in value["items"] if i["channel"] == "social")
    assert selected["sentiment"] == "unclear" and selected["guard"]["model_sentiment"] == "positive"
    assert value["summary"]["social"]["counts"]["unclear"] == 1
    with transaction() as conn:
        row=one(conn,"SELECT * FROM sentiment_analyses WHERE id=%s", (value["id"],))
        raw=one(conn,"SELECT response_body FROM model_calls WHERE id=%s",(row["call_id"],))
    original = json.loads(S.response_text(raw))
    assert all(i["sentiment"] == "positive" for i in original["items"])
    before=ledger.snapshot()
    assert S.generate(iid,transport=lambda _: pytest.fail("cache must not dispatch"))["id"] == value["id"]
    assert before == ledger.snapshot()


def test_current_response_cannot_omit_the_extraction_field(owner):
    iid=prepare(owner)
    with transaction() as conn: p=S.prepare(conn,iid)
    def omit(items):
        items[0].pop('price_claims')
        return items
    with pytest.raises(ValueError,match='extraction list'):
        S.render({'response_body':provider(mutate=omit)(S.request_for(p))},p)


def test_minimum_and_strict_majority_and_unclear_count_are_explicit():
    def summary(labels):
        return S.summarize([dict(source_id=str(i),channel="social",relevance="relevant",sentiment=label) for i,label in enumerate(labels)])["social"]
    assert summary(["positive"]*4)["tone"] == "thin sample"
    value=summary(["positive"]*3+["negative"]*2+["unclear"]*2)
    assert value["tone"] == "positive leaning" and value["majority_groups"] == 3
    assert value["interpretable_groups"] == 5 and value["counts"]["unclear"] == 2
    assert summary(["positive"]*3+["negative"]*3)["tone"] == "mixed / balanced"
