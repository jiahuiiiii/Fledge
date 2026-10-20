"""Password recovery codes, password changes and HTTPS hosting settings."""
import re
import pytest
from fastapi.testclient import TestClient
from thesis import auth, password_auth, terms
from thesis import app as app_module
from thesis.app import app
from thesis.db import transaction, one

HEADERS = {'X-Thesis-Request': 'local-ui'}
CONSENT = {'accept_terms': True, 'terms_version': terms.VERSION}
CODE = re.compile(r'^[A-HJ-NP-Z2-9]{4}(-[A-HJ-NP-Z2-9]{4}){3}$')


@pytest.fixture
def password_mode(owner, monkeypatch):
    monkeypatch.setattr(auth, 'configuration', lambda: dict(mode='password'))
    with transaction(admin=True) as conn:
        conn.execute('TRUNCATE password_attempts')
    return owner


def test_sign_up_gives_a_code_that_is_stored_only_as_a_hash(password_mode):
    cookie, _, code = password_auth.register('mei', 'correct horse')
    assert CODE.match(code)
    account = password_auth.authenticate(cookie)
    assert password_auth.has_recovery(account)
    with transaction(admin=True) as conn:
        row = one(conn, 'SELECT recovery_hash FROM password_credentials WHERE account_id=%s', (account,))
    assert row['recovery_hash'] and code not in row['recovery_hash']
    assert code.replace('-', '') not in row['recovery_hash']


def test_reset_with_code_signs_out_everywhere_and_replaces_the_code(password_mode):
    old_cookie, _, code = password_auth.register('raj', 'old password')
    # Typed loosely: lower case, spaces instead of dashes.
    cookie, _, new_code = password_auth.reset_with_code('RAJ', code.lower().replace('-', ' '), 'new password')
    assert password_auth.authenticate(old_cookie) is None
    assert password_auth.authenticate(cookie)
    assert new_code != code and CODE.match(new_code)
    with pytest.raises(password_auth.PasswordFailure, match='incorrect'):
        password_auth.login('raj', 'old password')
    password_auth.login('raj', 'new password')
    # The used code no longer works.
    with pytest.raises(password_auth.PasswordFailure, match='recovery code is incorrect'):
        password_auth.reset_with_code('raj', code, 'another password')


def test_wrong_codes_fail_the_same_way_and_are_limited(password_mode):
    password_auth.register('amy', 'right password')
    with pytest.raises(password_auth.PasswordFailure, match='recovery code is incorrect'):
        password_auth.reset_with_code('nobody', 'AAAA-BBBB-CCCC-DDDD', 'new password')
    for _ in range(5):
        with pytest.raises(password_auth.PasswordFailure, match='recovery code is incorrect'):
            password_auth.reset_with_code('amy', 'AAAA-BBBB-CCCC-DDDD', 'new password')
    with pytest.raises(password_auth.PasswordFailure) as limited:
        password_auth.reset_with_code('amy', 'AAAA-BBBB-CCCC-DDDD', 'new password')
    assert limited.value.status == 429 and limited.value.retry_after > 0
    # The password is unchanged.
    with transaction(admin=True) as conn:
        conn.execute('TRUNCATE password_attempts')
    password_auth.login('amy', 'right password')


def test_reset_still_checks_the_new_password(password_mode):
    _, _, code = password_auth.register('lee', 'right password')
    with pytest.raises(password_auth.PasswordFailure, match='8 to 128'):
        password_auth.reset_with_code('lee', code, 'short')
    password_auth.login('lee', 'right password')


def test_change_password_and_new_code_need_the_current_password(password_mode):
    first, _, code = password_auth.register('kim', 'first password')
    other = password_auth.login('kim', 'first password')[0]
    account = password_auth.authenticate(first)
    with pytest.raises(password_auth.PasswordFailure) as wrong:
        password_auth.change_password(account, 'not it', 'second password')
    assert wrong.value.status == 403
    cookie, _ = password_auth.change_password(account, 'first password', 'second password')
    assert password_auth.authenticate(cookie) == account
    assert password_auth.authenticate(other) is None
    password_auth.login('kim', 'second password')
    with pytest.raises(password_auth.PasswordFailure):
        password_auth.replace_recovery_code(account, 'first password')
    new_code = password_auth.replace_recovery_code(account, 'second password')
    assert new_code != code
    with pytest.raises(password_auth.PasswordFailure, match='recovery code is incorrect'):
        password_auth.reset_with_code('kim', code, 'third password')
    password_auth.reset_with_code('kim', new_code, 'third password')


def test_server_reset_sets_a_temporary_password_and_drops_the_lost_code(password_mode):
    cookie, _, code = password_auth.register('zoe', 'forgotten pw')
    account = password_auth.authenticate(cookie)
    assert password_auth.admin_reset('ZOE', 'temporary pw') == 'zoe'
    assert password_auth.authenticate(cookie) is None
    assert not password_auth.has_recovery(account)
    password_auth.login('zoe', 'temporary pw')
    with pytest.raises(password_auth.PasswordFailure, match='recovery code is incorrect'):
        password_auth.reset_with_code('zoe', code, 'whatever pw')
    with pytest.raises(password_auth.PasswordFailure, match='No account'):
        password_auth.admin_reset('nobody', 'temporary pw')


def test_api_recovery_flow(password_mode):
    client = TestClient(app)
    created = client.post('/api/v1/auth/register', json={'username': 'api_user', 'password': 'pass word 1', **CONSENT}, headers=HEADERS)
    assert created.status_code == 200
    code = created.json()['result']['recovery_code']
    assert CODE.match(code)
    session = client.get('/api/v1/session').json()['result']
    assert session['has_recovery_code'] is True
    account = {**HEADERS, 'X-Thesis-Account': session['account_id']}

    # Change password: wrong current password is refused without signing out.
    wrong = client.post('/api/v1/account/password', json={'current_password': 'nope', 'new_password': 'pass word 2'}, headers=account)
    assert wrong.status_code == 403
    assert client.get('/api/v1/home').status_code == 200
    changed = client.post('/api/v1/account/password', json={'current_password': 'pass word 1', 'new_password': 'pass word 2'}, headers=account)
    assert changed.status_code == 200 and auth.COOKIE in changed.cookies
    assert client.get('/api/v1/home').status_code == 200

    fresh = client.post('/api/v1/account/recovery-code', json={'current_password': 'pass word 2'}, headers=account)
    new_code = fresh.json()['result']['recovery_code']
    assert new_code != code

    # Forgot password, signed out, in a new browser.
    stranger = TestClient(app)
    bad = stranger.post('/api/v1/auth/password-reset', json={'username': 'api_user', 'recovery_code': code, 'password': 'pass word 3'}, headers=HEADERS)
    assert bad.status_code == 401
    good = stranger.post('/api/v1/auth/password-reset', json={'username': 'api_user', 'recovery_code': new_code, 'password': 'pass word 3'}, headers=HEADERS)
    assert good.status_code == 200
    assert CODE.match(good.json()['result']['recovery_code'])
    assert stranger.get('/api/v1/home').status_code == 200
    # The first browser was signed out by the reset.
    assert client.get('/api/v1/home').status_code == 401


def test_accounts_without_a_code_are_reported(password_mode):
    cookie, *_ = password_auth.register('older', 'pass word 1')
    account = password_auth.authenticate(cookie)
    with transaction(admin=True) as conn:
        conn.execute('UPDATE password_credentials SET recovery_hash=NULL WHERE account_id=%s', (account,))
    client = TestClient(app)
    client.cookies.set(auth.COOKIE, cookie)
    assert client.get('/api/v1/session').json()['result']['has_recovery_code'] is False
    with pytest.raises(password_auth.PasswordFailure, match='recovery code is incorrect'):
        password_auth.reset_with_code('older', 'AAAA-BBBB-CCCC-DDDD', 'new password')


def test_https_origin_and_secure_cookie(password_mode, monkeypatch):
    monkeypatch.setenv('THESIS_PUBLIC_ORIGIN', 'https://fledge.example.com/')
    assert app_module.public_origin() == 'https://fledge.example.com'
    assert 'fledge.example.com' in app_module.allowed_hosts()
    client = TestClient(app)
    origin = {**HEADERS, 'Origin': 'https://fledge.example.com'}
    created = client.post('/api/v1/auth/register', json={'username': 'web_user', 'password': 'pass word 1', **CONSENT}, headers=origin)
    assert created.status_code == 200
    cookie_header = created.headers['set-cookie'].lower()
    assert 'secure' in cookie_header and 'httponly' in cookie_header and 'samesite=strict' in cookie_header
    foreign = client.post('/api/v1/auth/password-login', json={'username': 'web_user', 'password': 'pass word 1'},
                          headers={**HEADERS, 'Origin': 'https://evil.example.com'})
    assert foreign.status_code == 403


def test_laptop_cookie_is_not_https_only(password_mode, monkeypatch):
    monkeypatch.delenv('THESIS_PUBLIC_ORIGIN', raising=False)
    assert app_module.public_origin() == ''
    created = TestClient(app).post('/api/v1/auth/register', json={'username': 'lap_user', 'password': 'pass word 1', **CONSENT}, headers=HEADERS)
    assert 'secure' not in created.headers['set-cookie'].lower()


def test_privacy_contact_is_public_and_validated(owner, monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv('THESIS_PRIVACY_CONTACT', 'dpo@fledge.example.com')
    assert client.get('/api/v1/legal').json()['result'] == {'privacy_contact': 'dpo@fledge.example.com'}
    for bad in ('', 'not an email', '<script>@x.y', 'a@b'):
        monkeypatch.setenv('THESIS_PRIVACY_CONTACT', bad)
        assert client.get('/api/v1/legal').json()['result'] == {'privacy_contact': ''}
