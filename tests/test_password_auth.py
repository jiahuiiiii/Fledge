"""Username/password sign-in for the test product."""
import pytest
from fastapi.testclient import TestClient
from thesis import auth, password_auth, profile, terms
from thesis.app import app
from thesis.config import OWNER
from thesis.db import transaction, one

HEADERS = {'X-Thesis-Request': 'local-ui'}
CONSENT = {'accept_terms': True, 'terms_version': terms.VERSION}


@pytest.fixture
def password_mode(owner, monkeypatch):
    monkeypatch.setattr(auth, 'configuration', lambda: dict(mode='password'))
    with transaction(admin=True) as conn:
        conn.execute('TRUNCATE password_attempts')
    return owner


def test_register_login_and_sessions(password_mode):
    cookie, lifetime, code = password_auth.register('Mei_88', 'correct horse')
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


def test_concurrent_wrong_passwords_respect_the_limit(password_mode):
    from concurrent.futures import ThreadPoolExecutor
    password_auth.register('burst', 'right password')
    for _ in range(4):
        with pytest.raises(password_auth.PasswordFailure, match='incorrect'):
            password_auth.login('burst', 'wrong password')

    def attempt(_):
        try:
            password_auth.login('burst', 'wrong password')
        except password_auth.PasswordFailure as failure:
            return failure.status
        return 200

    with ThreadPoolExecutor(6) as pool:
        statuses = sorted(pool.map(attempt, range(6)))
    # Only the fifth attempt is checked; the other five are turned away.
    assert statuses == [401, 429, 429, 429, 429, 429]
    with transaction(admin=True) as conn:
        assert one(conn, "SELECT failures FROM password_attempts WHERE key='user:burst'")['failures'] == 5


def test_sign_up_never_claims_the_owner_account(password_mode):
    # Even a username someone might configure for the owner gets a new account.
    cookie, *_ = password_auth.register('Ten', 'owner password')
    assert password_auth.authenticate(cookie) != OWNER
    with pytest.raises(password_auth.PasswordFailure, match='taken'):
        password_auth.provision_owner('ten', 'owner password')
    assert password_auth.provision_owner('Ten_Owner', 'owner password') == 'ten_owner'
    assert password_auth.authenticate(password_auth.login('ten_owner', 'owner password')[0]) == OWNER
    with pytest.raises(password_auth.PasswordFailure, match='already has a login'):
        password_auth.provision_owner('someone', 'owner password')
    client = TestClient(app)
    response = client.post('/api/v1/auth/register', json={'username': 'ten_owner2', 'password': 'owner password', **CONSENT}, headers=HEADERS)
    assert response.status_code == 200
    assert client.get('/api/v1/session').json()['result']['is_installation_owner'] is False


def test_api_sign_up_answers_and_sign_out(password_mode):
    client = TestClient(app)
    assert client.get('/api/v1/session').json()['result'] == {'mode': 'password', 'authenticated': False}
    assert client.get('/api/v1/home').status_code == 401
    no_consent = client.post('/api/v1/auth/register', json={'username': 'newbie', 'password': 'pass word 1'}, headers=HEADERS)
    assert no_consent.status_code == 422 and 'Terms of Use' in no_consent.text
    old_terms = client.post('/api/v1/auth/register', json={'username': 'newbie', 'password': 'pass word 1',
                                                             'accept_terms': True, 'terms_version': '2020-01-01'}, headers=HEADERS)
    assert old_terms.status_code == 422
    with transaction(admin=True) as conn:
        assert one(conn, "SELECT count(*) n FROM password_credentials WHERE username='newbie'")['n'] == 0
    created = client.post('/api/v1/auth/register', json={'username': 'newbie', 'password': 'pass word 1', **CONSENT}, headers=HEADERS)
    assert created.status_code == 200 and auth.COOKIE in created.cookies
    session = client.get('/api/v1/session').json()['result']
    assert session['authenticated'] and session['username'] == 'newbie' and session['mode'] == 'password'
    assert session['terms']['accepted'] and session['terms']['version'] == terms.VERSION
    body = dict(experience='new', interests=['technology'], horizon='long', goal='learn')
    assert client.put('/api/v1/profile', json=body, headers=HEADERS).status_code == 200
    assert profile.get(session['account_id'])['interests'] == ['technology']
    assert profile.get(OWNER) == {'completed': False}
    taken = client.post('/api/v1/auth/register', json={'username': 'newbie', 'password': 'pass word 1', **CONSENT}, headers=HEADERS)
    assert taken.status_code == 409
    assert client.post('/api/v1/auth/logout', headers={**HEADERS, 'X-Thesis-Account': session['account_id']}).status_code == 200
    assert client.get('/api/v1/home').status_code == 401
    wrong = client.post('/api/v1/auth/password-login', json={'username': 'newbie', 'password': 'nope nope'}, headers=HEADERS)
    assert wrong.status_code == 401
    assert client.post('/api/v1/auth/password-login', json={'username': 'newbie', 'password': 'pass word 1'}, headers=HEADERS).status_code == 200
    assert client.get('/api/v1/home').json()['result']['profile']['completed']


def test_existing_accounts_accept_terms_once(password_mode):
    cookie, *_ = password_auth.register('olduser', 'pass word 1')  # signed up before consent existed
    account = password_auth.authenticate(cookie)
    assert terms.status(account)['accepted'] is False
    client = TestClient(app)
    client.cookies.set(auth.COOKIE, cookie)
    assert client.get('/api/v1/session').json()['result']['terms']['accepted'] is False
    stale = client.post('/api/v1/terms/accept', json={'terms_version': '2020-01-01'}, headers=HEADERS)
    assert stale.status_code == 422
    accepted = client.post('/api/v1/terms/accept', json={'terms_version': terms.VERSION}, headers=HEADERS)
    assert accepted.status_code == 200 and accepted.json()['result']['accepted']
    assert client.post('/api/v1/terms/accept', json={'terms_version': terms.VERSION}, headers=HEADERS).status_code == 200
    assert client.get('/api/v1/session').json()['result']['terms']['accepted'] is True
    other, *_ = password_auth.register('someone_else', 'pass word 1')
    assert terms.status(password_auth.authenticate(other))['accepted'] is False  # consent is per account
