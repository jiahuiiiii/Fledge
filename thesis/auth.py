"""Supabase PKCE email sign-in and opaque, server-verified local sessions.

No password, service-role key, unverified JWT claim or client-supplied owner ID
is used. Tokens/verifiers stay in server-only tables in the private local DB.
Renewable sessions last at most seven days; provider identity is checked every minute.
"""
import base64
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
import hashlib
import math
import os
import re
import secrets
from urllib.parse import urlsplit
from uuid import UUID, uuid4
import httpx
from .config import DATA, OWNER
from .db import transaction, one, rows
from .providers.settings import settings

account_context = ContextVar('thesis_authenticated_account', default=None)
COOKIE = 'thesis_session'
FLOW_COOKIE = 'thesis_login_flow'


class AuthFailure(Exception):
    def __init__(self, message='Sign in again to access your research.', status=401, retry_after=None):
        self.status = status
        self.retry_after = retry_after
        super().__init__(message)


def current_owner():
    account = account_context.get()
    if not account:
        raise AuthFailure()
    return account


def configuration():
    # Explicit offline fixtures must never contact the owner's auth project.
    if os.environ.get('THESIS_TEST_OFFLINE') == 'true' and DATA.is_relative_to('/private/tmp'):
        return None
    values = settings()
    if values.get('THESIS_AUTH_ENABLED') == 'false':
        return None
    url = values.get('SUPABASE_URL', '').rstrip('/')
    key = values.get('SUPABASE_PUBLISHABLE_KEY') or values.get('SUPABASE_ANON_KEY', '')
    email = values.get('THESIS_OWNER_EMAIL', '').strip().casefold()
    if not any((url, key, email)):
        return None
    parts = urlsplit(url)
    if (parts.scheme != 'https' or not parts.hostname or not re.fullmatch(r'[a-z0-9-]+\.supabase\.co', parts.hostname)
            or parts.path or parts.query or parts.fragment or parts.username or parts.port or not key or not valid_email(email)):
        raise AuthFailure('Managed login settings are incomplete. Check the project URL, publishable key and owner email.', 503)
    base = values.get('THESIS_AUTH_SITE_URL', 'http://127.0.0.1:8841').rstrip('/')
    site = urlsplit(base)
    if site.scheme != 'http' or site.hostname not in ('127.0.0.1', 'localhost') or site.path or site.query or site.fragment or site.username:
        raise AuthFailure('The sign-in return address must be the configured local app URL.', 503)
    return dict(url=url, key=key, owner_email=email, site=base, redirect=base+'/auth/callback')


def valid_email(value):
    return isinstance(value, str) and len(value)<=254 and bool(re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+', value))


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def provider(config, method, path, *, body=None, bearer=None, params=None, transport=None):
    headers={'apikey':config['key'], 'Content-Type':'application/json'}
    if bearer: headers['Authorization']='Bearer '+bearer
    try:
        with httpx.Client(timeout=15, follow_redirects=False, transport=transport) as client:
            response=client.request(method,config['url']+'/auth/v1'+path,headers=headers,json=body,params=params)
        if response.status_code==429:
            retry=response.headers.get('retry-after','')
            seconds=int(retry) if retry.isdigit() and len(retry)<8 else None
            raise AuthFailure('Supabase has paused sign-in requests. Its email-delivery limit may be exhausted; wait for the provider limit to reset.',429,seconds)
        if not 200<=response.status_code<300:
            code = response.json().get('error_code', '') if response.headers.get('content-type','').startswith('application/json') else ''
            if code=='email_address_not_authorized':
                raise AuthFailure('Supabase email delivery currently allows only project-team addresses. Add a custom email service to admit other testers.',503)
            if response.status_code>=500:
                raise AuthFailure('Supabase is temporarily unavailable. Your session is kept; try again shortly.',503)
            raise AuthFailure('Supabase could not complete sign-in. Check the link or start sign-in again.',401 if path in ('/token','/user') else 503)
        if response.status_code==204:return {}
        if len(response.content)>256_000:raise AuthFailure('The sign-in response was invalid.',503)
        data=response.json()
        if not isinstance(data,dict):raise AuthFailure('The sign-in response was invalid.',503)
        return data
    except (httpx.HTTPError, ValueError):
        raise AuthFailure('Supabase could not be reached. Your research is saved; try sign-in again later.',503) from None


def verified_user(config, token, *, transport=None):
    user=provider(config,'GET','/user',bearer=token,transport=transport)
    try: subject=str(UUID(user['id']))
    except (KeyError,ValueError,TypeError):raise AuthFailure('The verified account identity was invalid.') from None
    email=user.get('email','').strip().casefold()
    if not valid_email(email) or not user.get('email_confirmed_at') or user.get('is_anonymous'):
        raise AuthFailure('Confirm your email with Supabase before accessing research.')
    return subject,email


def send_link(email, *, transport=None):
    config=configuration()
    if not config:raise AuthFailure('Managed login has not been configured.',503)
    email=email.strip().casefold()
    if not valid_email(email):raise AuthFailure('Enter a valid email address.',422)
    now=datetime.now(timezone.utc)
    # Shared and address-specific persistent limits also cover unsuccessful sends.
    with transaction(admin=True) as conn:
        for key,limit,seconds in [('global',10,3600),('email:'+digest(email),1,60)]:
            conn.execute('INSERT INTO auth_send_limits VALUES(%s,%s,0) ON CONFLICT DO NOTHING',(key,now))
            state=one(conn,'SELECT * FROM auth_send_limits WHERE key=%s FOR UPDATE',(key,))
            if now-state['window_start']>=timedelta(seconds=seconds):
                conn.execute('UPDATE auth_send_limits SET window_start=%s,requests=0 WHERE key=%s',(now,key));state['requests']=0
            if state['requests']>=limit:
                wait=max(1,math.ceil((state['window_start']+timedelta(seconds=seconds)-now).total_seconds()))
                message='A sign-in email was requested recently.' if key!='global' else 'This installation reached its hourly sign-in request limit.'
                raise AuthFailure(message+' The countdown shows when you can request another.',429,wait)
            conn.execute('UPDATE auth_send_limits SET requests=requests+1 WHERE key=%s',(key,))
    token=secrets.token_urlsafe(32); verifier=secrets.token_urlsafe(48)
    challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    provider(config,'POST','/otp',body=dict(email=email,create_user=True,code_challenge=challenge,code_challenge_method='s256'),params={'redirect_to':config['redirect']},transport=transport)
    with transaction(admin=True) as conn:
        conn.execute('DELETE FROM auth_flows WHERE expires_at<%s',(now,))
        conn.execute('INSERT INTO auth_flows VALUES(%s,%s,%s,%s,%s)',(digest(token),verifier,email,config['url'],now+timedelta(minutes=15)))
    return token


def token_pair(result):
    token=result.get('access_token')
    if not isinstance(token,str) or not 10<len(token)<16_000:raise AuthFailure('The sign-in response was invalid.',503)
    refresh=result.get('refresh_token')
    if refresh is not None and (not isinstance(refresh,str) or not 10<len(refresh)<16_000):raise AuthFailure('The session renewal response was invalid.',503)
    try: lifetime=min(3600,int(result['expires_in']))
    except (KeyError,ValueError,TypeError):raise AuthFailure('The session expiry was invalid.',503) from None
    if lifetime<30:raise AuthFailure('This sign-in session has expired.')
    return token,refresh,lifetime


def complete(code, flow_token, *, transport=None):
    config=configuration()
    if not config or not flow_token or not code or len(code)>2048:raise AuthFailure('Start sign-in in this browser, then open its newest email link.')
    now=datetime.now(timezone.utc)
    with transaction(admin=True) as conn:
        # A callback can consume a flow once, including failures.
        flow=one(conn,'DELETE FROM auth_flows WHERE token_hash=%s RETURNING *',(digest(flow_token),))
    if not flow or flow['expires_at']<now or flow['project_url']!=config['url']:
        raise AuthFailure('This sign-in link expired or was opened in another browser. Request a new link here.')
    result=provider(config,'POST','/token',params={'grant_type':'pkce'},body={'auth_code':code,'code_verifier':flow['verifier']},transport=transport)
    token,refresh,lifetime=token_pair(result)
    subject,email=verified_user(config,token,transport=transport)
    if email!=flow['email']:raise AuthFailure('This link belongs to a different sign-in request.')
    session_lifetime=7*86400 if refresh else lifetime
    cookie=secrets.token_urlsafe(32)
    with transaction(admin=True) as conn:
        # Serializes first-owner mapping and concurrent first sign-ins.
        conn.execute("SELECT pg_advisory_xact_lock(hashtext('thesis-auth-identity'))")
        identity=one(conn,'SELECT * FROM auth_identities WHERE project_url=%s AND subject=%s',(config['url'],subject))
        if identity:account=str(identity['account_id'])
        elif email==config['owner_email']:
            if one(conn,'SELECT 1 FROM auth_identities WHERE account_id=%s',(OWNER,)):
                raise AuthFailure('The existing owner account is already linked. Ask the installation owner to review the identity mapping.',409)
            account=OWNER
            conn.execute('INSERT INTO accounts VALUES(%s,%s) ON CONFLICT DO NOTHING',(OWNER,'Installation owner'))
        else:
            account=str(uuid4());conn.execute('INSERT INTO accounts VALUES(%s,%s)',(account,'Research account'))
        if not identity:
            conn.execute('INSERT INTO auth_identities(project_url,subject,account_id,verified_email) VALUES(%s,%s,%s,%s)',(config['url'],subject,account,email))
        conn.execute('DELETE FROM auth_sessions WHERE expires_at<%s',(now,))
        conn.execute('INSERT INTO auth_sessions(token_hash,project_url,subject,account_id,access_token,verified_at,expires_at,refresh_token,access_expires_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)',(digest(cookie),config['url'],subject,account,token,now,now+timedelta(seconds=session_lifetime),refresh,now+timedelta(seconds=lifetime)))
    return cookie,session_lifetime


def authenticate(cookie, *, transport=None):
    config=configuration()
    if not config: return None
    if not cookie or len(cookie)>256:raise AuthFailure()
    now=datetime.now(timezone.utc)
    with transaction(admin=True) as conn:
        session=one(conn,'SELECT * FROM auth_sessions WHERE token_hash=%s FOR UPDATE',(digest(cookie),))
        if not session or session['project_url']!=config['url'] or session['expires_at']<=now:raise AuthFailure()
        if session['access_expires_at']<=now+timedelta(seconds=60) and session['refresh_token']:
            result=provider(config,'POST','/token',params={'grant_type':'refresh_token'},body={'refresh_token':session['refresh_token']},transport=transport)
            token,refresh,lifetime=token_pair(result)
            if not refresh:raise AuthFailure('The session renewal response was incomplete. Try again shortly.',503)
            subject,email=verified_user(config,token,transport=transport)
            if subject!=str(session['subject']):raise AuthFailure('The renewed session belongs to a different account.')
            conn.execute('UPDATE auth_sessions SET access_token=%s,refresh_token=%s,access_expires_at=%s,verified_at=%s WHERE token_hash=%s',(token,refresh,now+timedelta(seconds=lifetime),now,digest(cookie)))
        elif session['access_expires_at']<=now:
            raise AuthFailure()
        elif now-session['verified_at']>=timedelta(seconds=60):
            subject,email=verified_user(config,session['access_token'],transport=transport)
            if subject!=str(session['subject']):raise AuthFailure()
            conn.execute('UPDATE auth_sessions SET verified_at=%s WHERE token_hash=%s',(now,digest(cookie)))
        return str(session['account_id'])


def logout(cookie):
    if not cookie:return
    with transaction(admin=True) as conn:
        conn.execute('DELETE FROM auth_sessions WHERE token_hash=%s',(digest(cookie),))


def background_owners():
    # Private workers retain explicit owner scopes; public evidence is shared.
    config=configuration()
    if not config:return [OWNER]
    with transaction(admin=True) as conn:
        # Historical QA accounts are retained but must not be enrolled merely
        # because account support is installed.
        owners=[str(r['id']) for r in rows(conn,'SELECT id FROM accounts WHERE id=%s OR id IN (SELECT account_id FROM auth_identities WHERE project_url=%s) ORDER BY id',(OWNER,config['url']))]
    return owners
