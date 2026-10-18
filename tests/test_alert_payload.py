"""Alert payload bounds and the on-request earlier sample. HTTP simulated, DB disposable."""
import pytest
from thesis.monitoring import news_watch as N


def source(identity):
    return dict(id=identity, title='Title ' + identity, body='Body ' + identity)


def test_cited_keeps_every_displayed_source_in_original_order():
    sources = [source(x) for x in ('a', 'b', 'c', 'd', 'e', 'f')]
    items = [dict(source_id='e', citations=[dict(source_id='e'), dict(source_id='b')]), dict(source_id='a', citations=None)]
    links = [dict(source_id='e', reference_source_id='c')]
    assert [s['id'] for s in N.cited(sources, items, links)] == ['a', 'b', 'c', 'e']
    assert N.cited(sources, []) == []


def test_each_reading_is_presented_once_and_unused_sources_are_dropped(monkeypatch):
    alerts = [dict(id='alert-2', instrument_id='i', symbol='EXA', name='Example', created_at=__import__('datetime').datetime(2026, 10, 18),
                   review_action=None, preview=False, current_id='r3', previous_id='r2',
                   payload=dict(items=[dict(source_id='s3', citations=[])], coverage_links=[])),
              dict(id='alert-1', instrument_id='i', symbol='EXA', name='Example', created_at=__import__('datetime').datetime(2026, 10, 17),
                   review_action=None, preview=False, current_id='r2', previous_id='r1',
                   payload=dict(items=[dict(source_id='s2', citations=[])], coverage_links=[]))]
    readings = {r: dict(id=r) for r in ('r1', 'r2', 'r3')}

    def fake_rows(conn, sql, params=()):
        return alerts if 'research_alerts' in sql else [readings[r] for r in params[0]]
    calls = []

    def present(conn, record):
        calls.append(record['id'])
        n = record['id'][1]
        return dict(withheld=False, coverage={}, sources=[source('s' + n), source('unused' + n)],
                    items=[dict(source_id='s' + n, citations=[])])
    monkeypatch.setattr(N, 'rows', fake_rows)
    monkeypatch.setattr(N.sentiment, 'present', present)
    result = N.list_alerts(None, 'owner')
    assert sorted(calls) == ['r1', 'r2', 'r3']  # r2 is shared by both alerts
    assert [s['id'] for s in result[0]['sources']] == ['s3']
    assert [s['id'] for s in result[0]['previous_sources']] == ['s2']
    assert result[0]['previous_items'] == [dict(source_id='s2', citations=[])]
    assert [s['id'] for s in result[1]['previous_sources']] == ['s1']


def published_alert(owner):
    """One real company alert: neutral baseline, then a new negative report."""
    from test_market import prepare, commit, news
    from test_sentiment import add_social, provider
    from thesis.research import sentiment
    iid = prepare(owner)
    add_social(iid)
    sentiment.generate(iid, transport=provider("neutral"))
    N.configure(owner, iid, True)
    commit(iid, [news(id=2, url="https://example.test/negative", headline="Microsoft reports weaker margins",
                      summary="Microsoft says operating margins decreased in the reported period.")])
    second = sentiment.generate(iid, transport=provider())
    assert N.publish(owner, iid, second["id"]) == 1
    return iid


def test_lists_omit_the_earlier_sample_and_the_request_returns_it_unchanged(owner):
    from thesis.db import transaction
    from thesis import service
    iid = published_alert(owner)
    with transaction(owner) as c:
        full = N.list_alerts(c, owner)[0]
        listed = N.list_alerts(c, owner, previous=False)[0]
    assert full["previous_items"] and full["previous_sources"]
    assert listed["previous_items"] is None and listed["previous_sources"] is None
    assert {k: v for k, v in listed.items() if not k.startswith("previous_")} == {
        k: v for k, v in full.items() if not k.startswith("previous_")}
    sample = N.previous_sample(owner, full["id"])
    assert sample == dict(id=full["id"], withheld=False, previous_items=full["previous_items"],
                          previous_sources=full["previous_sources"])
    workspace = service.state(owner, iid)["research_alerts"][0]
    assert workspace["previous_items"] is None and workspace["sources"] == full["sources"]


def test_earlier_sample_keeps_account_and_withdrawal_checks(owner):
    from uuid import uuid4
    from thesis.db import transaction
    from thesis import service
    published_alert(owner)
    with transaction(owner) as c:
        alert = N.list_alerts(c, owner)[0]
    with pytest.raises(service.Missing):
        N.previous_sample(str(uuid4()), alert["id"])
    with pytest.raises(service.Missing):
        N.previous_sample(owner, str(uuid4()))
    with transaction(admin=True) as c:
        c.execute("UPDATE social_feeds SET enabled=false")
    try:
        hidden = N.previous_sample(owner, alert["id"])
        assert hidden["withheld"] and hidden["previous_items"] == [] and hidden["previous_sources"] == []
    finally:
        with transaction(admin=True) as c:
            c.execute("UPDATE social_feeds SET enabled=true")


def test_earlier_sample_endpoint_needs_a_session_and_returns_the_same_sample(owner, monkeypatch):
    from uuid import uuid4
    from fastapi.testclient import TestClient
    from thesis.db import transaction
    import thesis.app as module
    monkeypatch.setattr(module, 'OWNER', owner)
    published_alert(owner)
    with transaction(owner) as c:
        alert = N.list_alerts(c, owner)[0]
    client = TestClient(module.app, base_url='http://127.0.0.1')
    url = '/api/v1/research-alerts/' + alert['id'] + '/previous-sample'
    assert client.get(url).status_code == 401
    client.get('/api/v1/session')
    headers = {'X-Thesis-Request': 'local-ui'}
    body = client.get(url, headers=headers).json()['result']
    assert body['previous_items'] == alert['previous_items'] and not body['withheld']
    assert len(body['previous_sources']) == len(alert['previous_sources'])
    assert client.get('/api/v1/research-alerts/' + str(uuid4()) + '/previous-sample', headers=headers).status_code == 404


def test_company_page_details_only_its_own_alerts(owner):
    from uuid import uuid4
    from thesis.db import transaction
    iid = published_alert(owner)
    with transaction(owner) as c:
        full = N.list_alerts(c, owner, previous=False)
        own = N.list_alerts(c, owner, previous=False, detail_instrument=iid)
        other = N.list_alerts(c, owner, previous=False, detail_instrument=str(uuid4()))
    assert own == full
    assert other == [dict(id=a["id"], instrument_id=a["instrument_id"], symbol=a["symbol"], name=a["name"],
                          created_at=a["created_at"], review_action=a["review_action"], preview=a["preview"],
                          status_only=True) for a in full]
    assert not any(k in other[0] for k in ("payload", "sources", "withheld"))
