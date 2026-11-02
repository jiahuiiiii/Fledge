"""Company read on the wire: repeated texts sent once, and unchanged re-reads."""
from fastapi.testclient import TestClient
from thesis.workspace_payload import share_texts, revision, MIN_SHARED
from test_market import prepare, news, commit

LONG = "Microsoft reported results in which cloud revenue grew. " * 10


def test_repeated_texts_are_sent_once_and_single_ones_stay_inline():
    short = "brief"
    single = "only here " * 40
    result = dict(
        documents=[dict(id="a", body=LONG), dict(id="b", body=single), dict(id="c", body=short)],
        sentiment=dict(sources=[dict(id="a", body=LONG)], withheld=False),
        sentiment_inputs=dict(sources=[dict(id="a", body=LONG), dict(id="c", body=short)], as_of="t1"),
    )
    share_texts(result)
    ref = result["documents"][0]["body_ref"]
    assert result["source_texts"] == {ref: LONG}
    assert result["sentiment"]["sources"][0] == dict(id="a", body_ref=ref)
    assert result["sentiment_inputs"]["sources"][0] == dict(id="a", body_ref=ref)
    assert result["documents"][1]["body"] == single
    assert result["documents"][2]["body"] == short == result["sentiment_inputs"]["sources"][1]["body"]
    assert len(short) < MIN_SHARED


def test_no_repeats_leaves_the_answer_as_it_was():
    result = dict(documents=[dict(id="a", body=LONG)], sentiment=None, sentiment_inputs=None)
    share_texts(result)
    assert result == dict(documents=[dict(id="a", body=LONG)], sentiment=None, sentiment_inputs=None)


def test_revision_ignores_the_read_time_but_not_the_data():
    one = dict(documents=[dict(id="a")], sentiment_inputs=dict(as_of="t1", status="same"))
    two = dict(documents=[dict(id="a")], sentiment_inputs=dict(as_of="t2", status="same"))
    assert revision(one) == revision(two)
    assert one["sentiment_inputs"]["as_of"] == "t1"
    three = dict(documents=[dict(id="b")], sentiment_inputs=dict(as_of="t1", status="same"))
    assert revision(three) != revision(one)


def test_company_read_answers_unchanged_until_something_is_saved(owner):
    from thesis import app as app_module
    from thesis.config import OWNER

    iid = prepare(OWNER)
    client = TestClient(app_module.app)
    client.get("/api/v1/session")
    path = f"/api/v1/workspace?shared=1&include_financials=false&instrument_id={iid}"
    first = client.get(path).json()["result"]
    assert first["revision"] and first["documents"]
    again = client.get(path + f"&known={first['revision']}").json()["result"]
    assert again == {"unchanged": True, "revision": first["revision"]}
    # A wrong or old revision gets the whole company.
    assert client.get(path + "&known=stale").json()["result"]["revision"] == first["revision"]
    commit(iid, [news(id=77, headline="Microsoft signs a new cloud contract", url="https://example.test/77")])
    after = client.get(path + f"&known={first['revision']}").json()["result"]
    assert after.get("unchanged") is None and after["revision"] != first["revision"]
    assert any(d["title"] == "Microsoft signs a new cloud contract" for d in after["documents"])


def test_texts_are_shared_only_for_pages_that_ask(owner):
    """A page opened before this change cannot put shared texts back, so it
    keeps getting every text in place."""
    from thesis import app as app_module
    from thesis.config import OWNER

    iid = prepare(OWNER)
    commit(iid, [news(id=81, headline="Microsoft long report one", summary=LONG, url="https://example.test/81"),
                 news(id=82, headline="Microsoft long report two", summary=LONG + " More.", url="https://example.test/82")])
    client = TestClient(app_module.app)
    client.get("/api/v1/session")
    base = f"/api/v1/workspace?include_financials=false&instrument_id={iid}"
    plain = client.get(base).json()["result"]
    assert "source_texts" not in plain
    assert not any("body_ref" in d for d in plain["documents"])
    shared = client.get(base + "&shared=1").json()["result"]
    texts = shared.get("source_texts", {})
    assert texts and any("body_ref" in d for d in shared["documents"])
    for doc in shared["documents"]:
        assert ("body" in doc) != ("body_ref" in doc)
        if "body_ref" in doc:
            assert texts[doc["body_ref"]] == next(d["body"] for d in plain["documents"] if d["id"] == doc["id"])
