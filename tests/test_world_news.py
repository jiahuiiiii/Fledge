"""World news: general headlines, theme tags, watchlist mentions and the AI check."""
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from thesis import watchlist
from thesis.app import app
from thesis.db import transaction, one
from thesis.providers.settings import MODEL
from thesis.research import market, world_news
from thesis.service import Conflict

HEADERS = {'X-Thesis-Request': 'local-ui'}
NOW = datetime.now(timezone.utc).replace(microsecond=0)


def item(n, headline, summary='', minutes_ago=30, url=None):
    return dict(id=n, category='general', datetime=int((NOW - timedelta(minutes=minutes_ago)).timestamp()),
                headline=headline, summary=summary, source='Reuters',
                url=url or f'https://example.com/world/{n}', related='', image='')


FEED = [
    item(1, 'Fed signals two rate cuts this year as inflation cools',
         'Powell said the Federal Reserve could lower interest rates soon.'),
    item(2, 'Oil jumps after missile strikes near Iran',
         'Brent crude rose 4% as the conflict raised supply fears.', minutes_ago=60),
    item(3, 'Apple moves more iPhone manufacturing to India',
         'Apple Inc. is shifting production away from China amid tariffs.', minutes_ago=90),
    item(4, 'Celebrity chef opens new restaurant', '', minutes_ago=120),
    item(5, 'Broken item', '', url='javascript:alert(1)'),
    item(6, 'Too old', '', minutes_ago=60 * 24 * 10),
]


def company(symbol, name, sector='Technology'):
    iid = str(uuid4())
    with transaction(admin=True) as conn:
        conn.execute('INSERT INTO instruments VALUES(%s,%s,%s)', (iid, symbol, name))
        conn.execute("""INSERT INTO instrument_state(instrument_id,cutoff,period,label,sector)
                        VALUES(%s,'2025-07-24T12:00:00Z','2025-Q2','Q2 baseline',%s)""", (iid, sector))
    return iid


@pytest.fixture
def finnhub(owner, monkeypatch):
    monkeypatch.setattr(market, 'key', lambda: 'test-key')
    monkeypatch.setattr(market, 'configured', lambda: True)
    with transaction(admin=True) as conn:
        conn.execute('TRUNCATE world_news_articles, world_news_checks')
        conn.execute('UPDATE world_news_state SET attempted_at=NULL,checked_at=NULL,error=NULL,rejected=0')
    calls = []

    def handler(request):
        calls.append(request)
        assert request.url.path == '/api/v1/news' and request.url.params['category'] == 'general'
        return httpx.Response(200, json=FEED)

    return httpx.MockTransport(handler), calls


def test_theme_tags_and_company_mentions():
    assert world_news.themes_for('Fed signals two rate cuts as inflation cools') == ['rates', 'economy']
    assert world_news.themes_for('Oil jumps after missile strikes near Iran') == ['geopolitics', 'energy']
    assert world_news.themes_for('New tariffs on chip imports') == ['trade']
    assert world_news.themes_for('Celebrity chef opens new restaurant') == []
    apple = dict(id='a', symbol='AAPL', name='Apple Inc.')
    onsemi = dict(id='o', symbol='ON', name='ON Semiconductor Corp')
    meta = dict(id='m', symbol='META', name='Meta Platforms, Inc.')
    companies = [apple, onsemi, meta]
    assert world_news.mentions('Apple moves iPhone manufacturing to India', companies) == ['a']
    assert world_news.mentions('$AAPL slips while Meta rises', companies) == ['a', 'm']
    # A capitalised ticker like ON is not matched inside ordinary lowercase words.
    assert world_news.mentions('Stocks move on rate news', companies) == []
    assert world_news.mentions('ON Semiconductor guides lower', companies) == ['o']


def test_refresh_stores_checked_headlines_once(finnhub):
    transport, calls = finnhub
    result = world_news.refresh(transport=transport, now=NOW)
    assert result['received'] == 4 and result['added'] == 4 and result['rejected'] == 2
    with pytest.raises(Conflict, match='ten minutes'):
        world_news.refresh(transport=transport, now=NOW + timedelta(minutes=5))
    assert len(calls) == 1
    again = world_news.refresh(transport=transport, now=NOW + timedelta(minutes=11))
    assert again['added'] == 0
    with transaction(admin=True) as conn:
        assert one(conn, 'SELECT count(*) n FROM world_news_articles')['n'] == 4
        tagged = one(conn, "SELECT themes FROM world_news_articles WHERE headline LIKE 'Oil%%'")
    assert tagged['themes'] == ['geopolitics', 'energy']


def test_failed_refresh_keeps_earlier_headlines(finnhub):
    transport, _ = finnhub
    world_news.refresh(transport=transport, now=NOW)
    failing = httpx.MockTransport(lambda request: httpx.Response(429))
    with pytest.raises(ValueError, match='rate-limited'):
        world_news.refresh(transport=failing, now=NOW + timedelta(minutes=11))
    with transaction(admin=True) as conn:
        assert one(conn, 'SELECT count(*) n FROM world_news_articles')['n'] == 4
        assert 'rate-limited' in one(conn, 'SELECT error FROM world_news_state')['error']


def test_view_marks_watchlist_mentions(owner, finnhub):
    transport, _ = finnhub
    world_news.refresh(transport=transport, now=NOW)
    aapl = company('AAPL', 'Apple Inc.')
    watchlist.add(owner, aapl)
    page = world_news.view(owner, now=NOW)
    assert page['configured'] and not page['stale'] and not page['can_refresh']
    assert [a['headline'][:5] for a in page['articles']] == ['Fed s', 'Oil j', 'Apple', 'Celeb']
    apple_story = page['articles'][2]
    assert apple_story['mentions'] == [aapl] and apple_story['themes'] == ['trade']
    assert page['companies'][0]['symbol'] == 'AAPL'
    assert page['ai']['available'] is False and page['check'] is None


def fake_model(links):
    calls = []

    def transport(body):
        calls.append(body)
        return dict(id='resp_' + str(len(calls)), model=MODEL, status='completed', service_tier='default',
                    usage=dict(input_tokens=900, output_tokens=200),
                    output=[dict(type='message', content=[dict(type='output_text', text=json.dumps(dict(links=links)))])])
    return transport, calls


def test_ai_check_keeps_only_quoted_links_and_reuses_answers(owner, finnhub):
    transport, _ = finnhub
    world_news.refresh(transport=transport, now=NOW)
    aapl = company('AAPL', 'Apple Inc.')
    nvda = company('NVDA', 'NVIDIA Corp')
    watchlist.add(owner, aapl)
    watchlist.add(owner, nvda)
    with pytest.raises(ValueError, match='watchlist'):
        world_news.check(str(uuid4()), transport=fake_model([])[0], now=NOW)
    model, calls = fake_model([
        dict(article_id='a1', company_id='c1', effect='could_help',
             reason='Lower interest rates can make growth companies look more valuable.',
             quote='two rate cuts this year'),
        dict(article_id='a3', company_id='c1', effect='mixed_or_unclear',
             reason='Moving production can cut tariff costs but adds setup costs.',
             quote='shifting production away from China'),
        dict(article_id='a2', company_id='c2', effect='could_hurt',
             reason='Invented quote should be dropped.', quote='Nvidia stock will crash'),
        dict(article_id='a9', company_id='c1', effect='could_hurt', reason='Unknown article.', quote='x'),
        dict(article_id='a1', company_id='c1', effect='could_help', reason='Repeat.', quote='rate cuts'),
    ])
    page = world_news.check(owner, transport=model, now=NOW)
    assert page['check']['dropped'] == 3 and set(page['check']['company_ids']) == {aapl, nvda}
    linked = {a['headline'][:5]: a['links'] for a in page['articles'] if a['links']}
    assert set(linked) == {'Fed s', 'Apple'}
    assert linked['Fed s'][0]['effect'] == 'could_help'
    body = calls[0]
    assert body['model'] == MODEL and body['text']['format']['name'] == 'world_news_links'
    assert 'Never recommend buying' in body['input'][0]['content']
    # Same headlines and watchlist: the saved answer is reused, nothing is paid twice.
    world_news.check(owner, transport=model, now=NOW)
    assert len(calls) == 1
    # Another account cannot see this account's check.
    other = str(uuid4())
    with transaction(admin=True) as conn:
        conn.execute('INSERT INTO accounts VALUES(%s,%s)', (other, 'Other'))
    assert world_news.view(other, now=NOW)['check'] is None
    with transaction(other) as conn:
        assert one(conn, 'SELECT count(*) n FROM world_news_checks')['n'] == 0


def test_world_news_api(owner, finnhub, monkeypatch):
    transport, _ = finnhub
    # Use the real clock: the API's cooldown check runs at the current time.
    world_news.refresh(transport=transport)
    client = TestClient(app)
    client.get('/api/v1/session')
    page = client.get('/api/v1/world-news').json()['result']
    assert len(page['articles']) == 4 and page['themes'][0]['id'] == 'rates'
    refused = client.post('/api/v1/world-news/refresh', headers=HEADERS)
    assert refused.status_code == 409
    no_ai = client.post('/api/v1/world-news/check', headers=HEADERS)
    assert no_ai.status_code == 422
