"""First-login answers, the tailored home page and the five-company watchlist."""
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from thesis import home, profile, watchlist
from thesis.app import app
from thesis.config import OWNER, INSTRUMENT
from thesis.db import transaction, one
from thesis.monitoring import news_watch

HEADERS = {'X-Thesis-Request': 'local-ui'}


def companies(n):
    ids = []
    with transaction(admin=True) as conn:
        for i in range(n):
            iid = str(uuid4())
            conn.execute('INSERT INTO instruments VALUES(%s,%s,%s)', (iid, f'ZZ{i}', f'Test company {i}'))
            ids.append(iid)
    return ids


def account():
    value = str(uuid4())
    with transaction(admin=True) as conn:
        conn.execute('INSERT INTO accounts VALUES(%s,%s)', (value, 'Second test account'))
    return value


def test_profile_defaults_validation_and_mode(owner):
    assert profile.get(owner) == {'completed': False}
    saved = profile.save(owner, 'new', ['technology', 'banks'], 'long', 'learn')
    assert saved['completed'] and saved['detail_mode'] == 'explain'
    assert profile.save(owner, 'active', [], 'short', 'monitor')['detail_mode'] == 'explain'
    assert profile.save(owner, 'stocks', ['healthcare'], 'medium', 'check', 'explain')['detail_mode'] == 'explain'
    assert profile.set_mode(owner, 'data')['detail_mode'] == 'data'
    for bad in (dict(experience='pro'), dict(interests=['crypto']), dict(interests=['banks', 'banks']),
                dict(interests=['banks', 'unsure']), dict(goal='trade'), dict(detail_mode='loud')):
        args = dict(experience='new', interests=[], horizon='long', goal='learn')
        args.update(bad)
        with pytest.raises(ValueError):
            profile.save(owner, **args)
    with pytest.raises(ValueError):
        profile.set_mode(account(), 'data')


def test_answers_and_watchlists_are_private_to_each_account(owner):
    other = account()
    iid, = companies(1)
    profile.save(owner, 'new', ['energy'], 'long', 'learn')
    watchlist.add(owner, iid)
    assert profile.get(other) == {'completed': False}
    assert watchlist.summary(other)['count'] == 0
    with transaction(other) as conn:
        assert one(conn, 'SELECT count(*) n FROM investor_profiles')['n'] == 0
        assert one(conn, 'SELECT count(*) n FROM watchlist_companies')['n'] == 0


def test_watchlist_holds_at_most_five(owner):
    ids = companies(6)
    for iid in ids[:5]:
        result = watchlist.add(owner, iid)
    assert result['count'] == 5 and result['full']
    assert watchlist.add(owner, ids[0])['count'] == 5  # adding again is harmless
    with pytest.raises(ValueError, match='up to 5'):
        watchlist.add(owner, ids[5])
    with pytest.raises(ValueError):
        watchlist.add(owner, str(uuid4()))
    assert watchlist.remove(owner, ids[0])['count'] == 4
    assert watchlist.add(owner, ids[5])['count'] == 5


def test_watches_follow_the_same_limit(owner, monkeypatch):
    monkeypatch.setattr(news_watch.sentiment.market_brief, 'company_for', lambda iid: True)
    ids = companies(6)
    for iid in ids[:5]:
        news_watch.configure(owner, iid, True)
    with pytest.raises(ValueError, match='up to 5'):
        news_watch.configure(owner, ids[5], True)
    news_watch.configure(owner, ids[0], True)  # an existing watch can be updated
    news_watch.configure(owner, ids[0], False)
    news_watch.configure(owner, ids[5], True)


def test_home_follows_answers_without_naming_companies(owner):
    page = home.build(owner)
    assert page['next_step']['action'] == 'onboarding' and page['interests'] == []
    profile.save(owner, 'stocks', ['technology', 'healthcare'], 'medium', 'check')
    page = home.build(owner)
    assert page['next_step']['action'] == 'add_company'
    assert page['starter_order'][0] == 'risks' and page['detail_mode'] == 'explain'
    assert [i['label'] for i in page['interests']] == ['Technology', 'Healthcare']
    iid, = companies(1)
    watchlist.add(owner, iid)
    page = home.build(owner)
    assert page['next_step']['action'] == 'save_reasoning'
    assert [c['id'] for c in page['watchlist']['companies']] == [iid]
    profile.save(owner, 'new', [], 'long', 'monitor')
    assert home.build(owner)['next_step']['action'] == 'watch'


def test_profile_watchlist_and_home_api(owner):
    client = TestClient(app)
    client.get('/api/v1/session')
    body = dict(experience='etf', interests=['banks'], horizon='long', goal='learn')
    response = client.put('/api/v1/profile', json=body, headers=HEADERS)
    assert response.status_code == 200 and response.json()['result']['detail_mode'] == 'explain'
    assert client.put('/api/v1/profile', json=dict(body, goal='trade'), headers=HEADERS).status_code == 422
    assert client.put('/api/v1/profile/detail-mode', json={'detail_mode': 'data'}, headers=HEADERS).json()['result']['detail_mode'] == 'data'
    ids = [INSTRUMENT] + companies(5)
    for iid in ids[:5]:
        assert client.post('/api/v1/watchlist', json={'instrument_id': iid}, headers=HEADERS).status_code == 200
    full = client.post('/api/v1/watchlist', json={'instrument_id': ids[5]}, headers=HEADERS)
    assert full.status_code == 422 and 'up to 5' in full.text
    assert client.delete(f'/api/v1/watchlist/{ids[1]}', headers=HEADERS).json()['result']['count'] == 4
    page = client.get('/api/v1/home').json()['result']
    assert page['profile']['experience'] == 'etf' and page['watchlist']['count'] == 4
    catalogue = client.get('/api/v1/workspace').json()['result']['catalogue']
    assert [c['watchlisted'] for c in catalogue if c['id'] == INSTRUMENT] == [True]
    assert not any(c['watchlisted'] for c in catalogue if c['id'] != INSTRUMENT)


def test_emptied_watchlist_stays_in_use(owner):
    """Removing the last company must not bring back every other company."""
    client = TestClient(app)
    client.get('/api/v1/session')
    assert client.get('/api/v1/workspace').json()['result']['watchlist_started'] is False
    assert watchlist.summary(owner)['started'] is False
    assert client.post('/api/v1/watchlist', json={'instrument_id': INSTRUMENT}, headers=HEADERS).status_code == 200
    emptied = client.delete(f'/api/v1/watchlist/{INSTRUMENT}', headers=HEADERS).json()['result']
    assert emptied['count'] == 0 and emptied['started'] is True
    result = client.get('/api/v1/workspace').json()['result']
    assert result['watchlist_started'] is True
    assert not any(c['watchlisted'] for c in result['catalogue'])
    assert client.get('/api/v1/home').json()['result']['watchlist']['started'] is True


def test_not_sure_what_to_look_at_gets_a_starting_point(owner):
    who = account()
    saved = profile.save(who, 'new', goal='explore')
    assert saved['goal'] == 'explore'
    page = home.build(who)
    assert page['headline'].startswith('Not sure where to start')
    assert page['next_step']['action'] == 'add_company'
    assert 'product you use' in page['next_step']['label']
