"""Username/password sign-in for the test product."""
import pytest
from fastapi.testclient import TestClient
from thesis import auth, password_auth, profile
from thesis.app import app
from thesis.config import OWNER
from thesis.db import transaction, one

HEADERS = {'X-Thesis-Request': 'local-ui'}


@pytest.fixture
def password_mode(owner, monkeypatch):
    monkeypatch.setattr(auth, 'configuration', lambda: dict(mode='password', owner_username='ten'))
    with transaction(admin=True) as conn:
        conn.execute('TRUNCATE password_attempts')
    return owner


def test_register_login_and_sessions(password_mode):
    cookie, lifetime = password_auth.register('Mei_88', 'correct horse')
    account = password_auth.authenticate(cookie)
    assert account and account != OWNER and lifetime == 7 * 86400
    with transaction(admin=True) as conn:
        row = one(conn, 'SELECT username,password_hash FROM password_credentials WHERE account_id=%s', (account,))
    assert row['username'] == 'mei_88' and 'correct horse' not in row['password_hash']
    assert password_auth.authenticate(password_auth.login('MEI_88', 'correct horse')[0]) == account
    with pytest.raises(password_auth.PasswordFailure, match='taken'):
        password_auth.register('mei_88', 'another password')
    for name, secret in (('ab', 'long enough'), ('bad name!', 'long enough'), ('raj', 'short')):
        with pytest.raises(password_auth.PasswordFailure):
            password_auth.register(name, secret)
    password_auth.logout(cookie)
    assert password_auth.authenticate(cookie) is None


def test_wrong_passwords_are_limited(password_mode):
    password_auth.register('raj', 'right password')
    for _ in range(5):
        with pytest.raises(password_auth.PasswordFailure, match='incorrect'):
            password_auth.login('raj', 'wrong password')
    with pytest.raises(password_auth.PasswordFailure) as limited:
        password_auth.login('raj', 'right password')
    assert limited.value.status == 429 and limited.value.retry_after > 0
    with pytest.raises(password_auth.PasswordFailure, match='incorrect'):
        password_auth.login('nobody', 'whatever')


def test_owner_username_keeps_existing_research(password_mode):
    cookie, _ = password_auth.register('Ten', 'owner password', 'ten')
    assert password_auth.authenticate(cookie) == OWNER
    other, _ = password_auth.register('ten2', 'owner password', 'ten')
    assert password_auth.authenticate(other) != OWNER


def test_api_sign_up_answers_and_sign_out(password_mode):
    client = TestClient(app)
    assert client.get('/api/v1/session').json()['result'] == {'mode': 'password', 'authenticated': False}
    assert client.get('/api/v1/home').status_code == 401
    created = client.post('/api/v1/auth/register', json={'username': 'newbie', 'password': 'pass word 1'}, headers=HEADERS)
    assert created.status_code == 200 and auth.COOKIE in created.cookies
    session = client.get('/api/v1/session').json()['result']
    assert session['authenticated'] and session['username'] == 'newbie' and session['mode'] == 'password'
    body = dict(experience='new', interests=['technology'], horizon='long', goal='learn')
    assert client.put('/api/v1/profile', json=body, headers=HEADERS).status_code == 200
    assert profile.get(session['account_id'])['interests'] == ['technology']
    assert profile.get(OWNER) == {'completed': False}
    taken = client.post('/api/v1/auth/register', json={'username': 'newbie', 'password': 'pass word 1'}, headers=HEADERS)
    assert taken.status_code == 409
    assert client.post('/api/v1/auth/logout', headers={**HEADERS, 'X-Thesis-Account': session['account_id']}).status_code == 200
    assert client.get('/api/v1/home').status_code == 401
    wrong = client.post('/api/v1/auth/password-login', json={'username': 'newbie', 'password': 'nope nope'}, headers=HEADERS)
    assert wrong.status_code == 401
    assert client.post('/api/v1/auth/password-login', json={'username': 'newbie', 'password': 'pass word 1'}, headers=HEADERS).status_code == 200
    assert client.get('/api/v1/home').json()['result']['profile']['completed']
