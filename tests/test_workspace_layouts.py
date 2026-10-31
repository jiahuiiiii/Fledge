"""Saved overview/home widget layouts: validation, reconcile and privacy."""
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb
from thesis import workspace_layouts as layouts
from thesis.app import app
from thesis.config import OWNER
from thesis.db import transaction, one

HEADERS = {'X-Thesis-Request': 'local-ui'}
HOME = [{'i': 'welcome', 'x': 0, 'y': 0, 'w': 12, 'h': 4},
        {'i': 'portfolio', 'x': 0, 'y': 4, 'w': 6, 'h': 8},
        {'i': 'companies', 'x': 6, 'y': 4, 'w': 6, 'h': 8}]


def account():
    value = str(uuid4())
    with transaction(admin=True) as conn:
        conn.execute('INSERT INTO accounts VALUES(%s,%s)', (value, 'Second test account'))
    return value


def test_unsaved_page_reads_empty(owner):
    assert layouts.read(owner, 'home') == {'lg': None, 'md': None, 'sm': None, 'hidden': [], 'saved': False}


@pytest.mark.parametrize('page,body', [
    ('settings', {'lg': HOME}),
    ('home', {'lg': [dict(HOME[0], i='chart')]}),
    ('home', {'lg': [HOME[0], HOME[0]]}),
    ('home', {'lg': [dict(HOME[0], x=6, w=12)]}),
    ('home', {'lg': [dict(HOME[0], w=0)]}),
    ('home', {'lg': [dict(HOME[0], h=500)]}),
    ('home', {'lg': [dict(HOME[0], y=-1)]}),
    ('home', {'lg': [dict(HOME[0], x='0')]}),
    ('home', {'sm': [dict(HOME[0], w=7)]}),
    ('home', {'xl': HOME}),
    ('home', {}),
    ('home', {'lg': HOME, 'hidden': ['chart']}),
    ('home', {'lg': HOME, 'hidden': ['portfolio', 'portfolio']}),
])
def test_bad_layouts_are_refused(owner, page, body):
    with pytest.raises(ValueError):
        layouts.save(owner, page, body)


def test_round_trip_hidden_and_reset(owner):
    saved = layouts.save(owner, 'home', {'lg': HOME, 'hidden': ['portfolio']})
    assert saved['lg'] == HOME and saved['md'] is None and saved['hidden'] == ['portfolio'] and saved['saved']
    # A later width keeps the same hidden widgets and the earlier width.
    sm = [dict(i, x=0, w=6) for i in HOME]
    again = layouts.save(owner, 'home', {'sm': sm, 'hidden': []})
    assert again['lg'] == HOME and again['sm'] == sm and again['hidden'] == []
    assert layouts.reset(owner, 'home')['saved'] is False


def test_reconcile_drops_retired_and_broken_items(owner):
    stored = [{'i': 'retired', 'x': 0, 'y': 0, 'w': 4, 'h': 4}, HOME[1], dict(HOME[2], w=40),
              dict(HOME[1], x=3), 'junk']
    with transaction(owner) as conn:
        conn.execute('INSERT INTO workspace_layouts(owner_id,page,breakpoint,layout,hidden) VALUES(%s,%s,%s,%s,%s)',
                     (owner, 'home', 'lg', Jsonb(stored), Jsonb(['retired', 'companies'])))
    read = layouts.read(owner, 'home')
    # Missing widgets are left for the browser to add at their registry default.
    assert read['lg'] == [HOME[1]] and read['hidden'] == ['companies'] and read['saved']


def test_layouts_are_private_to_each_account(owner):
    layouts.save(owner, 'overview', {'lg': [{'i': 'news', 'x': 0, 'y': 0, 'w': 6, 'h': 6}]})
    other = account()
    assert layouts.read(other, 'overview')['saved'] is False
    with transaction(other) as conn:
        assert one(conn, 'SELECT count(*) n FROM workspace_layouts')['n'] == 0


def test_layout_api(owner):
    client = TestClient(app)
    client.get('/api/v1/session')
    assert client.get('/api/v1/layouts/home').json()['result']['saved'] is False
    response = client.put('/api/v1/layouts/home', json={'lg': HOME, 'hidden': []}, headers=HEADERS)
    assert response.status_code == 200 and response.json()['result']['lg'] == HOME
    assert client.get('/api/v1/layouts/home').json()['result']['lg'] == HOME
    assert client.put('/api/v1/layouts/home', json={'lg': [dict(HOME[0], i='x')]}, headers=HEADERS).status_code == 422
    assert client.put('/api/v1/layouts/home', json={'lg': HOME, 'extra': 1}, headers=HEADERS).status_code == 422
    assert client.put('/api/v1/layouts/nope', json={'lg': HOME}, headers=HEADERS).status_code == 422
    assert client.delete('/api/v1/layouts/home', headers=HEADERS).json()['result']['saved'] is False
    with transaction(admin=True) as conn:
        assert one(conn, 'SELECT count(*) n FROM workspace_layouts WHERE owner_id=%s', (OWNER,))['n'] == 0
