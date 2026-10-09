"""Controlled Supabase responses, real DB mappings/RLS, no email is sent."""
from datetime import datetime, timezone, timedelta
import json
from uuid import uuid4
import httpx
import pytest
from fastapi.testclient import TestClient
from thesis import auth, service
from thesis.app import app, session_token
from thesis.config import OWNER, INSTRUMENT
from thesis.db import transaction, one
from thesis.models import SaveIdea

CONFIG=dict(url='https://project.supabase.co',key='test-publishable',owner_email='owner@example.test',site='http://127.0.0.1:8841',redirect='http://127.0.0.1:8841/auth/callback')
HEADERS={'X-Thesis-Request':'local-ui'}


@pytest.fixture
def managed(owner,monkeypatch):
    monkeypatch.setattr(auth,'configuration',lambda:CONFIG)
    with transaction(admin=True) as conn:
        conn.execute('TRUNCATE auth_send_limits,auth_flows')
    return owner


def sign_in(email,*,subject=None,confirmed=True,anonymous=False,renewable=False):
    subject=subject or str(uuid4());seen=[]
    def respond(request):
        seen.append(request)
        if request.url.path.endswith('/otp'):return httpx.Response(200,json={})
        if request.url.path.endswith('/token'):return httpx.Response(200,json=dict(access_token='verified-access-token',expires_in=3600,user={'id':str(uuid4())},**({'refresh_token':'first-refresh-token'} if renewable else {})))
        if request.url.path.endswith('/user'):return httpx.Response(200,json=dict(id=subject,email=email,email_confirmed_at='2026-10-09T00:00:00Z' if confirmed else None,is_anonymous=anonymous))
        raise AssertionError(request.url.path)
    transport=httpx.MockTransport(respond)
    flow=auth.send_link(email,transport=transport)
    cookie,lifetime=auth.complete('one-time-code',flow,transport=transport)
    return cookie,subject,seen,transport


def test_pkce_and_verified_owner_preserve_research(managed):
    service.save_idea(OWNER,SaveIdea(expected_revision=0,question='Owner research question',reasoning='Original owner reasoning',status='draft',conditions=[]))
    cookie,subject,seen,transport=sign_in(CONFIG['owner_email'])
    assert auth.authenticate(cookie,transport=transport)==OWNER
    request=json.loads(seen[0].content)
    assert request['code_challenge_method']=='s256'
    assert request['create_user'] is True
    assert seen[0].url.params['redirect_to']==CONFIG['redirect']
    exchange=json.loads(seen[1].content)
    assert exchange['code_verifier'] and exchange['auth_code']=='one-time-code'
    assert auth.digest(cookie)!=cookie
    assert seen[2].headers['authorization']=='Bearer verified-access-token'
    with transaction(admin=True) as conn:
        assert str(one(conn,'SELECT account_id FROM auth_identities WHERE subject=%s',(subject,))['account_id'])==OWNER
        assert one(conn,'SELECT token_hash FROM auth_sessions')['token_hash']==auth.digest(cookie)
    assert service.state(OWNER)['versions'][0]['reasoning']=='Original owner reasoning'


@pytest.mark.parametrize('confirmed,anonymous',[(False,False),(True,True)])
def test_unconfirmed_and_anonymous_accounts_cannot_claim_owner(managed,confirmed,anonymous):
    with pytest.raises(auth.AuthFailure):sign_in(CONFIG['owner_email'],confirmed=confirmed,anonymous=anonymous)
    with transaction(admin=True) as conn:assert not one(conn,'SELECT 1 FROM auth_identities')


def test_owner_mapping_cannot_be_reclaimed_by_another_subject(managed):
    cookie,subject,_,_=sign_in(CONFIG['owner_email'])
    with transaction(admin=True) as conn:conn.execute('TRUNCATE auth_send_limits')
    with pytest.raises(auth.AuthFailure,match='already linked'):sign_in(CONFIG['owner_email'])
    assert auth.authenticate(cookie)==OWNER


def test_two_real_sessions_isolate_api_research_and_exports(managed):
    first,_,_,_=sign_in(CONFIG['owner_email'])
    other,_,_,_=sign_in('participant@example.test')
    a=TestClient(app);b=TestClient(app)
    a.cookies.set(auth.COOKIE,first);b.cookies.set(auth.COOKIE,other)
    owner_a=a.get('/api/v1/session').json()['result']['account_id']
    owner_b=b.get('/api/v1/session').json()['result']['account_id']
    assert owner_a==OWNER and owner_b!=OWNER
    for client,text in [(a,'Owner secret reasoning'),(b,'Participant secret reasoning')]:
        response=client.post('/api/v1/idea',headers=HEADERS,json=dict(expected_revision=0,question='My private research question',reasoning=text,status='draft',conditions=[]))
        assert response.status_code==200
    da=a.get('/api/v1/workspace').json()['result'];db=b.get('/api/v1/workspace').json()['result']
    assert da['versions'][0]['reasoning']=='Owner secret reasoning'
    assert db['versions'][0]['reasoning']=='Participant secret reasoning'
    assert 'Owner secret reasoning' not in json.dumps(db)
    assert 'Participant secret reasoning' not in json.dumps(da)
    assert 'Owner secret reasoning' not in b.get('/api/v1/research-review/export').text
    assert b.get('/api/v1/telegram').json()['result'].get('connected') is not True
    assert b.post('/api/v1/idea',headers=HEADERS,json=dict(question='Forged owner',status='draft',conditions=[],owner_id=OWNER)).status_code==422
    assert b.post('/api/v1/research-actions',json=dict(question='Question',action='unresolved')).status_code==403
    assert b.get('/api/v1/workspace',headers={'Origin':'https://evil.test'}).status_code==403
    assert b.post('/api/v1/auth/logout',headers=HEADERS).status_code==200
    assert b.get('/api/v1/workspace').status_code==401
    assert a.get('/api/v1/workspace').status_code==200
    with pytest.raises(auth.AuthFailure):auth.authenticate(other)


def test_old_local_cookie_and_forged_tokens_do_not_grant_access(managed):
    c=TestClient(app);c.cookies.set(auth.COOKIE,session_token())
    assert c.get('/api/v1/session').json()['result']['authenticated'] is False
    assert c.get('/api/v1/workspace').status_code==401
    with pytest.raises(auth.AuthFailure):auth.authenticate('attacker-token')


def test_expiry_revocation_and_provider_outage_fail_closed(managed):
    cookie,subject,seen,transport=sign_in('person@example.test')
    with transaction(admin=True) as conn:conn.execute('UPDATE auth_sessions SET verified_at=now()-interval \'2 minutes\'')
    reject=httpx.MockTransport(lambda _:httpx.Response(401,json={'error_code':'bad_jwt'}))
    with pytest.raises(auth.AuthFailure):auth.authenticate(cookie,transport=reject)
    outage=httpx.MockTransport(lambda _:httpx.Response(503,json={}))
    with pytest.raises(auth.AuthFailure):auth.authenticate(cookie,transport=outage)
    with transaction(admin=True) as conn:conn.execute('UPDATE auth_sessions SET expires_at=now()-interval \'1 second\'')
    with pytest.raises(auth.AuthFailure):auth.authenticate(cookie,transport=transport)


def test_flow_replay_wrong_browser_and_rate_limits(managed):
    transport=httpx.MockTransport(lambda _:httpx.Response(200,json={}))
    flow=auth.send_link('person@example.test',transport=transport)
    with pytest.raises(auth.AuthFailure):auth.send_link('person@example.test',transport=transport)
    with pytest.raises(auth.AuthFailure):auth.complete('code','other-browser',transport=transport)
    with transaction(admin=True) as conn:conn.execute('UPDATE auth_flows SET expires_at=now()-interval \'1 second\'')
    with pytest.raises(auth.AuthFailure):auth.complete('code',flow,transport=transport)
    with pytest.raises(auth.AuthFailure):auth.complete('code',flow,transport=transport)


def test_auth_tables_are_server_only_and_workers_include_accounts(managed):
    import psycopg
    cookie,_,_,_=sign_in('person@example.test');account=auth.authenticate(cookie)
    assert account in auth.background_owners()
    for kwargs in ({},{'source':True}):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with transaction(**kwargs) as conn:conn.execute('SELECT * FROM auth_sessions')


def test_partial_config_never_falls_back_to_local(owner,monkeypatch):
    monkeypatch.delenv('THESIS_TEST_OFFLINE')
    monkeypatch.setattr(auth,'settings',lambda:{'SUPABASE_URL':'https://supabase.com/dashboard/project/project'})
    c=TestClient(app)
    assert c.get('/api/v1/session').status_code==503
    assert c.get('/api/v1/workspace').status_code==503


def test_operator_rollback_keeps_owner_data_and_is_loopback_only(owner,monkeypatch):
    monkeypatch.delenv('THESIS_TEST_OFFLINE')
    monkeypatch.setattr(auth,'settings',lambda:{'THESIS_AUTH_ENABLED':'false',**{key:'configured' for key in ('SUPABASE_URL','SUPABASE_PUBLISHABLE_KEY','THESIS_OWNER_EMAIL')}})
    service.save_idea(OWNER,SaveIdea(expected_revision=0,question='Preserve during rollback',reasoning='My existing work',status='draft',conditions=[]))
    c=TestClient(app);assert c.get('/api/v1/session').json()['result']['mode']=='local-pitch'
    assert c.get('/api/v1/workspace').json()['result']['versions'][0]['reasoning']=='My existing work'
    assert auth.background_owners()==[OWNER]
    assert c.get('/api/v1/session',headers={'Host':'public.example'}).status_code==400


def test_renewal_keeps_account_and_rotates_tokens_once_under_concurrent_requests(managed):
    from concurrent.futures import ThreadPoolExecutor
    cookie,subject,_,_=sign_in('renew@example.test',renewable=True)
    with transaction(admin=True) as conn:
        session=one(conn,'SELECT * FROM auth_sessions')
        absolute=session['expires_at']
        assert (absolute-session['verified_at']).total_seconds()==7*86400
        conn.execute("UPDATE auth_sessions SET access_expires_at=now()-interval '1 second'")
    seen=[]
    def respond(request):
        if request.url.path.endswith('/token'):
            assert request.url.params['grant_type']=='refresh_token'
            assert json.loads(request.content)['refresh_token']=='first-refresh-token'
            seen.append('renew')
            return httpx.Response(200,json=dict(access_token='new-verified-access',refresh_token='rotated-refresh-token',expires_in=3600))
        assert request.headers['authorization']=='Bearer new-verified-access'
        return httpx.Response(200,json=dict(id=subject,email='renew@example.test',email_confirmed_at='2026-10-09T00:00:00Z'))
    transport=httpx.MockTransport(respond)
    with ThreadPoolExecutor(max_workers=3) as pool:
        owners=list(pool.map(lambda _:auth.authenticate(cookie,transport=transport),range(3)))
    assert len(set(owners))==1 and seen==['renew']
    with transaction(admin=True) as conn:
        saved=one(conn,'SELECT * FROM auth_sessions')
        assert saved['expires_at']==absolute and saved['refresh_token']=='rotated-refresh-token'
        assert saved['access_token']=='new-verified-access' and saved['access_expires_at']>datetime.now(timezone.utc)
    auth.logout(cookie)
    with pytest.raises(auth.AuthFailure):auth.authenticate(cookie,transport=transport)


@pytest.mark.parametrize('failure', ['unavailable', 'wrong_subject', 'missing_refresh', 'revoked'])
def test_failed_renewal_does_not_publish_tokens_or_extend_session(managed,failure):
    cookie,subject,_,_=sign_in('renew@example.test',renewable=True)
    with transaction(admin=True) as conn:
        conn.execute("UPDATE auth_sessions SET access_expires_at=now()-interval '1 second'")
        before=one(conn,'SELECT * FROM auth_sessions')
    def respond(request):
        if request.url.path.endswith('/token'):
            if failure=='unavailable':return httpx.Response(503,json={})
            if failure=='revoked':return httpx.Response(400,json={'error_code':'refresh_token_not_found'})
            return httpx.Response(200,json=dict(access_token='new-verified-access',expires_in=3600,**({} if failure=='missing_refresh' else {'refresh_token':'rotated-refresh-token'})))
        return httpx.Response(200,json=dict(id=str(uuid4()),email='renew@example.test',email_confirmed_at='2026-10-09T00:00:00Z'))
    with pytest.raises(auth.AuthFailure) as error:auth.authenticate(cookie,transport=httpx.MockTransport(respond))
    assert error.value.status==(503 if failure in ('unavailable','missing_refresh') else 401)
    with transaction(admin=True) as conn:assert one(conn,'SELECT * FROM auth_sessions')==before


def test_provider_outage_is_retryable_without_signout_and_absolute_expiry_is_enforced(managed):
    cookie,_,_,_=sign_in('renew@example.test',renewable=True)
    with transaction(admin=True) as conn:conn.execute("UPDATE auth_sessions SET verified_at=now()-interval '2 minutes'")
    with pytest.raises(auth.AuthFailure) as error:
        auth.authenticate(cookie,transport=httpx.MockTransport(lambda _:httpx.Response(503,json={})))
    assert error.value.status==503
    with transaction(admin=True) as conn:conn.execute("UPDATE auth_sessions SET expires_at=now()-interval '1 second'")
    with pytest.raises(auth.AuthFailure):auth.authenticate(cookie,transport=httpx.MockTransport(lambda _:pytest.fail('expired session must not refresh')))


def test_resend_countdown_and_provider_limit_do_not_claim_same_reset(managed,monkeypatch):
    transport=httpx.MockTransport(lambda _:httpx.Response(200,json={}))
    auth.send_link('person@example.test',transport=transport)
    with pytest.raises(auth.AuthFailure) as error:auth.send_link('person@example.test',transport=transport)
    assert 1<=error.value.retry_after<=60
    client=TestClient(app)
    response=client.post('/api/v1/auth/login',headers=HEADERS,json={'email':'person@example.test'})
    assert response.status_code==429 and 1<=int(response.headers['Retry-After'])<=60
    with pytest.raises(auth.AuthFailure) as error:
        auth.provider(CONFIG,'POST','/otp',transport=httpx.MockTransport(lambda _:httpx.Response(429,json={})))
    assert error.value.retry_after is None and 'Supabase' in str(error.value)


def test_stale_tab_cannot_write_or_logout_new_account_and_identity_is_visible(managed):
    first,_,_,_=sign_in(CONFIG['owner_email'])
    other,_,_,_=sign_in('other@example.test')
    client=TestClient(app);client.cookies.set(auth.COOKIE,other)
    session=client.get('/api/v1/session').json()['result']
    assert session['email']=='other@example.test' and session['account_id']!=OWNER
    headers={**HEADERS,'X-Thesis-Account':OWNER}
    for path,body in [('/api/v1/idea',dict(expected_revision=0,question='Should never be written',status='draft',conditions=[])),('/api/v1/auth/logout',{})]:
        response=client.post(path,headers=headers,json=body)
        assert response.status_code==409 and response.headers['X-Thesis-Account']==session['account_id']
    assert client.get('/api/v1/workspace').json()['result']['versions']==[]
    assert auth.authenticate(other)==session['account_id'] and auth.authenticate(first)==OWNER
