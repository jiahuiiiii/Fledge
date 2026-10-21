"""Your list today: the whole-watchlist read and its optional, cited AI explanation."""
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from thesis import portfolio, watchlist
from thesis.app import app
from thesis.db import transaction, one
from thesis.providers.settings import MODEL
from thesis.research import world_news

HEADERS = {'X-Thesis-Request': 'local-ui'}
NOW = datetime.now(timezone.utc).replace(microsecond=0)


def company(symbol, name, sector, change=None, quoted=NOW):
    iid = str(uuid4())
    with transaction(admin=True) as conn:
        conn.execute('INSERT INTO instruments VALUES(%s,%s,%s)', (iid, symbol, name))
        conn.execute("""INSERT INTO instrument_state(instrument_id,cutoff,period,label,sector)
                        VALUES(%s,'2025-07-24T12:00:00Z','2025-Q2','Q2 baseline',%s)""", (iid, sector))
        if change is not None:
            conn.execute('INSERT INTO market_quotes VALUES(%s,%s,%s,%s)',
                         (uuid4(), iid, Jsonb(dict(price=100.0, change_percent=change,
                                                   quoted_at=quoted.isoformat())), quoted))
    return iid


NEWS = {
    'CRWV': dict(counts={'negative': 3, 'neutral': 1}, items=[
        dict(title='CoreWeave bonds yield near 15% as investors worry about AI debt',
             url='https://example.com/crwv1', publisher='CNBC', published_at=NOW.isoformat(), tone='negative')]),
    'NVDA': dict(counts={'positive': 1, 'negative': 1}, items=[
        dict(title='Nvidia slips with AI peers', url='https://example.com/nvda1', publisher='Reuters',
             published_at=NOW.isoformat(), tone='negative')]),
}


@pytest.fixture
def listed(owner, monkeypatch):
    with transaction(admin=True) as conn:
        conn.execute('TRUNCATE world_news_articles, world_news_checks, portfolio_reads')
    ids = dict(
        CRWV=company('CRWV', 'CoreWeave, Inc.', 'Not yet classified', -15.46),
        ORCL=company('ORCL', 'Oracle Corporation', 'Software', -8.83),
        NVDA=company('NVDA', 'NVIDIA Corp', 'Semiconductors', -3.16),
        AVGO=company('AVGO', 'Broadcom Inc.', 'Semiconductors', -3.10),
        MSFT=company('MSFT', 'Microsoft', 'Software', -1.80),
    )
    for iid in ids.values():
        watchlist.add(owner, iid)
    symbols = {v: k for k, v in ids.items()}
    monkeypatch.setattr(portfolio, 'news_for', lambda conn, iid: NEWS.get(symbols[iid], dict(counts={}, items=[])))
    return ids


def test_plain_read_counts_moves_sectors_and_tone(owner, listed):
    page = portfolio.build(owner, now=NOW)
    assert page['move'] == dict(mood='bad', text='All 5 down, −15.5% to −1.8%', up=0, down=5, flat=0)
    assert page['spread'] == dict(mood='none', text='2 sectors on file; 1 not on file', sectors=2)
    assert page['world']['text'] == 'Not checked against world news yet'
    assert page['news_tone'] == {'negative': 4, 'neutral': 1, 'positive': 1}
    labels = [g['label'] for g in page['groups']]
    # Groups are ordered by average move, biggest fall first; unknown sectors say so.
    assert labels == ['Sector not on file yet', 'Software', 'Semiconductors']
    assert page['groups'][1]['average'] == pytest.approx(-5.32, abs=0.01)
    assert page['explanation'] is None and page['prices_stale'] is False


def test_move_wording_for_mixed_quiet_and_missing_prices(owner):
    def c(change):
        return dict(id=str(uuid4()), sector='', quote=None if change is None else dict(change_percent=change))
    assert portfolio.move_line([c(2.0), c(-1.0), c(0.1)])['text'] == '1 up, 1 down, 1 flat (−1.0% to +2.0%)'
    assert portfolio.move_line([c(0.2), c(-0.3)])['text'] == 'A quiet day: all 2 within ±0.5%'
    assert portfolio.move_line([c(1.0), c(None)])['text'] == 'All 1 up, +1.0%; 1 without a price'
    assert portfolio.move_line([c(None)])['mood'] == 'none'
    assert portfolio.spread_line([dict(sector='Semiconductors')] * 4 + [dict(sector='Software')])['text'] == \
        'Mostly Semiconductors (4 of 5)'


def test_world_line_uses_the_accounts_own_check(owner, listed, monkeypatch):
    aid = uuid4()
    with transaction(admin=True) as conn:
        conn.execute("""INSERT INTO world_news_articles(id,url,headline,summary,publisher,category,provider_id,
                          published_at,retrieved_at,themes) VALUES(%s,%s,%s,%s,%s,'general','1',%s,%s,%s)""",
                     (aid, 'https://example.com/cpi', 'US inflation rises to 3.7%, raising rate-hike fears',
                      'Consumer prices rose faster than expected.', 'Reuters', NOW - timedelta(hours=2), NOW,
                      ['economy', 'rates']))
    links = [dict(article_id=str(aid), company_id=listed[s], symbol=s, effect='could_hurt',
                  reason='Higher rates make borrowing cost more.', quote='rate-hike fears')
             for s in ('CRWV', 'ORCL', 'NVDA', 'AVGO')]
    monkeypatch.setattr(portfolio, 'world_for', lambda conn, owner_, now: (
        world_news.recent(conn, now), [dict(l, headline='US inflation rises to 3.7%', url='https://example.com/cpi',
                                            publisher='Reuters') for l in links], True))
    page = portfolio.build(owner, now=NOW)
    assert page['world']['mood'] == 'bad' and page['world']['text'] == '1 event could hurt 4 of 5'
    assert len(page['world']['events'][0]['companies']) == 4


def fake_model(result):
    calls = []

    def transport(body):
        calls.append(body)
        return dict(id='resp_' + str(len(calls)), model=MODEL, status='completed', service_tier='default',
                    usage=dict(input_tokens=1500, output_tokens=300),
                    output=[dict(type='message', content=[dict(type='output_text', text=json.dumps(result))])])
    return transport, calls


def test_explanation_keeps_only_cited_grounded_parts_and_reuses_answers(owner, listed):
    good = dict(
        headline='Your whole list fell as worries about AI borrowing spread.',
        drivers=[
            dict(text='CoreWeave’s bonds were priced like a risky borrower, and the sell-off spread.',
                 source_ids=['n1_1']),
            dict(text='Invented source.', source_ids=['n9_9']),
            dict(text='You should sell the stock now.', source_ids=['n1_1']),
        ],
        groups=[
            dict(label='Borrowing-heavy AI cloud', company_ids=['c1', 'c2'],
                 note='They rely most on debt, so they fell the most.'),
            dict(label='Chipmakers', company_ids=['c3', 'c4', 'c1'], note='They fell less.'),
            dict(label='Bargain hunters', company_ids=['c5'], note='This is an opportunity.'),
        ],
        takeaway='These five look spread out but share one risk: the cost of borrowing to build AI.',
    )
    model, calls = fake_model(good)
    page = portfolio.explain(owner, transport=model, now=NOW)
    e = page['explanation']
    assert e['headline'].startswith('Your whole list fell')
    assert [d['text'][:9] for d in e['drivers']] == ['CoreWeave']
    assert e['drivers'][0]['sources'][0]['url'] == 'https://example.com/crwv1'
    assert [g['label'] for g in e['groups']] == ['Borrowing-heavy AI cloud', 'Chipmakers']
    # A company already placed is not repeated in a later group.
    assert e['groups'][1]['company_ids'] == [listed['NVDA'], listed['AVGO']]
    assert e['dropped'] == 3
    body = calls[0]
    assert body['model'] == MODEL and body['text']['format']['name'] == 'portfolio_read'
    assert 'Never recommend' in body['input'][0]['content']
    sent = json.loads(body['input'][1]['content'])
    assert [c['symbol'] for c in sent['companies']] == ['CRWV', 'ORCL', 'NVDA', 'AVGO', 'MSFT']
    # Same list and material: the saved answer is reused, nothing is paid twice.
    portfolio.explain(owner, transport=model, now=NOW)
    assert len(calls) == 1
    # Another account cannot see it, and a changed list hides the old explanation.
    other = str(uuid4())
    with transaction(admin=True) as conn:
        conn.execute('INSERT INTO accounts VALUES(%s,%s)', (other, 'Other'))
    with transaction(other) as conn:
        assert one(conn, 'SELECT count(*) n FROM portfolio_reads')['n'] == 0
    watchlist.remove(owner, listed['MSFT'])
    assert portfolio.build(owner, now=NOW)['explanation'] is None


def test_explanation_needs_a_list_with_prices(owner, monkeypatch):
    monkeypatch.setattr(portfolio, 'news_for', lambda conn, iid: dict(counts={}, items=[]))
    with pytest.raises(ValueError, match='two companies'):
        portfolio.explain(owner, transport=fake_model({})[0], now=NOW)
    for s in ('AAA', 'BBB'):
        watchlist.add(owner, company(s, s + ' Inc', 'Software'))
    with pytest.raises(ValueError, match='No share prices'):
        portfolio.explain(owner, transport=fake_model({})[0], now=NOW)


def test_advice_guard_allows_describing_a_sell_off():
    assert portfolio.clean('Investors sold AI stocks in a sharp sell-off.')
    for bad in ('Consider buying the dip.', 'This is a buying opportunity.', 'Shares will rebound.',
                'You should trim some.', 'Analysts set a price target of $90.'):
        assert portfolio.clean(bad) is None, bad


def test_portfolio_api(owner, listed):
    client = TestClient(app)
    client.get('/api/v1/session')
    for iid in listed.values():  # the signed-in account's own list
        client.post('/api/v1/watchlist', json={'instrument_id': iid}, headers=HEADERS)
    page = client.get('/api/v1/portfolio').json()['result']
    assert page['move']['down'] == 5 and len(page['companies']) == 5
    no_ai = client.post('/api/v1/portfolio/explain', headers=HEADERS)
    assert no_ai.status_code == 422


def test_unrated_news_is_not_called_no_news():
    listed = [dict(id='x', symbol='MSFT', name='Microsoft', sector='Software',
                   quote=dict(change_percent=-0.2), news=dict(counts={}, items=[], rated=False))]
    content, _ = portfolio.packet(listed, [], [])
    assert content['companies'][0]['news_rated'] is False
    assert 'news_rated is false' in portfolio.INSTRUCTIONS


def test_list_uses_the_newest_price_from_the_refreshed_chart(owner, monkeypatch):
    from tests.test_price_history import payload, setup
    from thesis.research import price_history as ph
    iid = setup(owner, monkeypatch)
    raw = payload()
    meta = raw['chart']['result'][0]['meta']
    closes = raw['chart']['result'][0]['indicators']['quote'][0]['close']
    now = datetime.now(timezone.utc)
    meta.update(regularMarketPrice='110', regularMarketTime=int(now.timestamp()) - 60)
    ph.refresh(iid, fetcher=lambda *_: raw)
    with transaction(owner) as conn:
        q = portfolio.quote_for(conn, iid)
    assert q['price'] == 110.0
    series = ph.normalize(raw, 'MSFT', *ph.window(now))
    finals = [b for b in series['bars'] if b['provisional'] is False and b['date'] < now.astimezone(ph.NY).date().isoformat()]
    previous = float(finals[-1]['close'])
    assert q['change_percent'] == round((110 - previous) / previous * 100, 2)
