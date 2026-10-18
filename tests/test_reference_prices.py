"""Price-only references, source clocks and owner mappings; mocked HTTP only."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
import psycopg
import pytest
from thesis.db import transaction, one, rows
from thesis.research import reference_prices as R, price_history as PH, market
from thesis.research.sec.service import add_company
from test_price_history import payload


@pytest.fixture
def refs(owner, monkeypatch):
    monkeypatch.setattr(market, 'configured', lambda: True)
    monkeypatch.setattr(PH, 'configured', lambda: True)
    with transaction(admin=True) as c:
        c.execute('TRUNCATE reference_refresh_state,reference_price_snapshots,move_trigger_claims,move_event_members')
        c.execute("INSERT INTO sources VALUES('finnhub-news','Authored market quotes','finnhub-pitch') ON CONFLICT DO NOTHING")
        c.execute("INSERT INTO sources VALUES('yahoo-price-history','Authored daily history','local-yahoo-history') ON CONFLICT DO NOTHING")
    return datetime.now(timezone.utc)


def raw(now, price=97, *, stamp=None):
    return dict(c=price,pc=100,t=int((stamp or now).timestamp()),o=100,l=95,h=105)


def etf():
    value=payload('QQQ')
    value['chart']['result'][0]['meta']['instrumentType']='ETF'
    return value


def test_separate_registry_has_no_company_filings_or_watch_side_effect(refs):
    with transaction(consistent=True) as c:
        assert [(r['symbol'],r['role']) for r in rows(c,'SELECT symbol,role FROM reference_instruments ORDER BY symbol')]==[
            ('QQQ','index'),('SOXX','sector'),('SPY','index')]
        assert not rows(c,"SELECT * FROM instruments WHERE symbol IN ('QQQ','SPY','SOXX')")
    result=R.refresh('QQQ',fetcher=lambda *a:raw(refs),now=refs)
    assert result['status']=='updated'
    with transaction(consistent=True) as c:
        assert R.latest(c,'QQQ')['payload']['previous_close']==100
        assert not rows(c,'SELECT * FROM company_sector_references')
        assert not rows(c,'SELECT * FROM news_watches')
        assert not rows(c,'SELECT * FROM telegram_settings')


def test_quote_cooldown_and_concurrent_lease_reuse_do_not_fetch_again(refs):
    calls=[]
    def fetch(*a):
        calls.append(a)
        assert R.refresh('QQQ',fetcher=lambda *a:pytest.fail('Concurrent fetch'),now=refs)['status']=='busy'
        return raw(refs)
    first=R.refresh('QQQ',fetcher=fetch,now=refs)
    second=R.refresh('QQQ',fetcher=lambda *a:pytest.fail('Cooldown fetch'),now=refs+timedelta(minutes=4))
    assert first['status']=='updated' and second['status']=='cached'
    assert second['snapshot_id']==first['snapshot_id'] and len(calls)==1


def test_failure_has_no_automatic_retry_preserves_snapshot_and_sanitizes_error(refs):
    first=R.refresh('QQQ',fetcher=lambda *a:raw(refs),now=refs)
    attempts=[]
    def failed(*a):
        attempts.append(True)
        raise ValueError('Authored private provider token must not appear')
    assert R.refresh('QQQ',fetcher=failed,now=refs+timedelta(minutes=6))['status']=='failed'
    assert R.refresh('QQQ',fetcher=failed,now=refs+timedelta(minutes=7))['status']=='cached'
    assert attempts==[True]
    with transaction(consistent=True) as c:
        assert str(R.latest(c,'QQQ')['id'])==first['snapshot_id']
        state=one(c,"SELECT * FROM reference_refresh_state WHERE symbol='QQQ'")
        assert state['error']==R.ERROR and state['lease_until'] is None


def test_older_quote_cannot_replace_latest_snapshot(refs):
    first=R.refresh('QQQ',fetcher=lambda *a:raw(refs),now=refs)
    assert R.refresh('QQQ',fetcher=lambda *a:raw(refs,stamp=refs-timedelta(minutes=1)),
                     now=refs+timedelta(minutes=6))['status']=='failed'
    with transaction(consistent=True) as c:assert str(R.latest(c,'QQQ')['id'])==first['snapshot_id']


def test_expired_or_replaced_claim_cannot_publish(refs):
    def fetch(*a):
        with transaction(admin=True) as c:
            c.execute("UPDATE reference_refresh_state SET attempt_id=%s,error='Replacement retained' WHERE symbol='QQQ'",(uuid4(),))
        return raw(refs)
    assert R.refresh('QQQ',fetcher=fetch,now=refs)['status']=='failed'
    with transaction(consistent=True) as c:
        assert not R.latest(c,'QQQ')
        assert one(c,"SELECT error FROM reference_refresh_state WHERE symbol='QQQ'")['error']=='Replacement retained'


def test_source_access_change_between_request_and_commit_blocks_publication(refs):
    def fetch(*a):
        with transaction(admin=True) as c:c.execute("UPDATE sources SET entitlement='fictional' WHERE id='finnhub-news'")
        return raw(refs)
    assert R.refresh('QQQ',fetcher=fetch,now=refs)['status']=='failed'
    with transaction(consistent=True) as c:assert not R.latest(c,'QQQ')


def test_unknown_source_reference_resource_and_clock_refused_before_fetch(refs,monkeypatch):
    fail=lambda *a:pytest.fail('Unavailable reference reached HTTP')
    for symbol,resource in [('AAPL','quote'),('QQQ','weekly')]:
        with pytest.raises(ValueError):R.refresh(symbol,resource,fetcher=fail,now=refs)
    with pytest.raises(ValueError):R.refresh('QQQ',fetcher=fail,now=refs.replace(tzinfo=None))
    monkeypatch.setattr(market,'configured',lambda:False)
    with pytest.raises(ValueError):R.refresh('QQQ',fetcher=fail,now=refs)


def test_etf_history_is_explicit_and_cannot_weaken_company_type_validation(refs):
    value=etf();start,end=PH.window(refs)
    with pytest.raises(ValueError):PH.normalize(value,'QQQ',start,end)
    with pytest.raises(ValueError):PH.normalize(value,'QQQ',start,end,instrument_type='FUTURE')
    assert PH.normalize(value,'QQQ',start,end,instrument_type='ETF')['symbol']=='QQQ'
    equity=deepcopy(value);equity['chart']['result'][0]['meta']['instrumentType']='EQUITY'
    with pytest.raises(ValueError):PH.normalize(equity,'QQQ',start,end,instrument_type='ETF')
    result=R.refresh('QQQ','history',fetcher=lambda *a:value,now=refs)
    assert result['status']=='updated'
    with transaction(consistent=True) as c:
        saved=R.latest(c,'QQQ','history')
        assert saved['payload']['basis']==PH.BASIS and saved['raw']==value
        assert saved['resource']=='history' and not R.latest(c,'QQQ','quote')


def test_history_cooldown_independent_of_quote_and_cannot_lose_retained_days(refs):
    value=etf()
    first=R.refresh('QQQ','history',fetcher=lambda *a:value,now=refs)
    assert R.refresh('QQQ',fetcher=lambda *a:raw(refs),now=refs)['status']=='updated'
    shortened=deepcopy(value);shortened['chart']['result'][0]['indicators']['quote'][0]['close'][1]=None
    assert R.refresh('QQQ','history',fetcher=lambda *a:shortened,now=refs+timedelta(hours=1))['status']=='failed'
    with transaction(consistent=True) as c:assert str(R.latest(c,'QQQ','history')['id'])==first['snapshot_id']


def test_source_withdrawal_withholds_existing_snapshot_and_immutable_storage(refs):
    first=R.refresh('QQQ',fetcher=lambda *a:raw(refs),now=refs)
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(admin=True) as c:c.execute('UPDATE reference_price_snapshots SET payload=%s WHERE id=%s',('{}',first['snapshot_id']))
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with transaction() as c:c.execute('DELETE FROM reference_price_snapshots')
    with transaction(admin=True) as c:c.execute("UPDATE sources SET entitlement='fictional' WHERE id='finnhub-news'")
    with transaction(consistent=True) as c:assert not R.latest(c,'QQQ')


def test_mapping_default_explicit_none_and_private_owner_override(refs,owner):
    iid=add_company('NVDA')['instrument_id']
    with transaction(owner,consistent=True) as c:
        assert R.sector(c,owner,iid)==dict(symbol='SOXX',origin='classification')
        assert not rows(c,'SELECT * FROM company_sector_references')
    assert R.set_sector(owner,iid,None)==dict(symbol=None,origin='owner')
    other=str(uuid4())
    with transaction(admin=True) as c:c.execute('INSERT INTO accounts VALUES(%s,%s)',(other,'Fictional other'))
    with transaction(other,consistent=True) as c:
        assert not rows(c,'SELECT * FROM company_sector_references')
        assert R.sector(c,other,iid)==dict(symbol='SOXX',origin='classification')
    assert R.set_sector(other,iid,'SOXX')['symbol']=='SOXX'
    with transaction(owner,consistent=True) as c:assert R.sector(c,owner,iid)['symbol'] is None
    with pytest.raises(ValueError):R.set_sector(owner,iid,'QQQ')
    with pytest.raises(ValueError):R.set_sector(owner,uuid4(),'SOXX')
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with transaction(other) as c:
            c.execute('INSERT INTO company_sector_references(owner_id,instrument_id,updated_at) VALUES(%s,%s,now())', (owner,iid))


def test_broad_technology_is_not_guessed_as_semiconductors(refs,owner):
    iid=add_company('MSFT')['instrument_id']
    with transaction(owner,consistent=True) as c:assert R.sector(c,owner,iid)==dict(symbol=None,origin='unknown')


def test_real_adapters_keep_shared_finnhub_clock_and_record_history_denial_once(refs,monkeypatch):
    calls=[];reservations=[]
    monkeypatch.setattr(market,'key',lambda:'authored-token')
    monkeypatch.setattr(market,'reserve_request',lambda:reservations.append(True))
    def handler(request):
        calls.append(request)
        assert request.url.path=='/api/v1/quote' and request.url.params['symbol']=='QQQ'
        return httpx.Response(200,json=raw(refs))
    assert R.refresh('QQQ',fetcher=lambda e,p:market.fetch(e,p,transport=httpx.MockTransport(handler)),now=refs)['status']=='updated'
    assert len(calls)==len(reservations)==1
    observations=[]
    from thesis.research import source_observations
    monkeypatch.setattr(source_observations,'record',lambda p,s:observations.append((p,s)))
    with transaction(admin=True) as c:c.execute("UPDATE price_history_clock SET next_at=now() WHERE singleton")
    def denied(request):
        assert request.url.host=='query1.finance.yahoo.com'
        return httpx.Response(429,json={})
    assert R.refresh('QQQ','history',fetcher=lambda s,a,b:PH.fetch(s,a,b,transport=httpx.MockTransport(denied)),now=refs)['status']=='failed'
    assert observations==[('yahoo_history',429)]
