"""Alert payload bounds: displayed sources kept, unused bodies dropped. No DB or network."""
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
