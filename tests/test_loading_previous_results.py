"""A skipped repeat exposes dated prior results, never invented availability."""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
from uuid import uuid4
from psycopg.types.json import Jsonb
from thesis.config import OWNER
from thesis.db import transaction,one
from thesis.research import loading
from test_market import prepare
from thesis.research.sec.service import add_company
import pytest


def journal(owner,iid,minutes,steps,days=7):
    clock=datetime.now(timezone.utc)-timedelta(minutes=minutes)
    content=[dict(key=key,label=loading.LABELS[key],status=status,message=message,
                  finished_at=(clock+timedelta(seconds=1)).isoformat()) for key,status,message in steps]
    with transaction(owner) as c:
        return one(c,'INSERT INTO research_loads(id,owner_id,instrument_id,lookback_days,steps,active,created_at) VALUES(%s,%s,%s,%s,%s,false,%s) RETURNING *',
                   (uuid4(),owner,iid,days,Jsonb(content),clock))


def test_skip_keeps_nearest_real_result_and_preserves_both_journals(owner):
    iid=prepare(owner)
    first=journal(owner,iid,5,[('hackernews','ready','28 comments verified.')])
    journal(owner,iid,3,[('hackernews','cached','Cooling down.')])
    latest=journal(owner,iid,1,[('hackernews','cached','Cooling down.')])
    visible=loading.latest(owner,iid)
    assert visible['steps'][0]['previous_check']==dict(status='ready',message='28 comments verified.',finished_at=first['steps'][0]['finished_at'],run_id=first['id'])
    assert visible['steps'][0]['message']=='Cooling down.'
    # Historical counts are not presented as currently permitted source counts.
    assert visible['saved_coverage']['hackernews']==0
    with transaction(owner,consistent=True) as c:
        for run in (first,latest):
            assert one(c,'SELECT steps FROM research_loads WHERE id=%s',(run['id'],))['steps']==run['steps']


def test_more_recent_failure_is_not_hidden_by_earlier_success(owner):
    iid=prepare(owner)
    journal(owner,iid,5,[('rss','ready','Two reports.')])
    failed=journal(owner,iid,3,[('rss','partial','One feed failed.')])
    journal(owner,iid,1,[('rss','cached','No checks made.')])
    prior=loading.latest(owner,iid)['steps'][0]['previous_check']
    assert prior['status']=='partial' and prior['run_id']==failed['id']


def test_history_is_fenced_to_owner_company_window_and_past(owner):
    iid=prepare(owner)
    journal(OWNER,iid,5,[('hackernews','ready','Other owner result.')])
    journal(owner,iid,4,[('hackernews','ready','Thirty-day result.')],days=30)
    current=journal(owner,iid,2,[('hackernews','cached','Skipped.')])
    journal(owner,iid,1,[('hackernews','ready','Later result.')])
    with transaction(owner,consistent=True) as c:
        copy=deepcopy(current)
        loading.add_previous_results(c,copy)
    assert 'previous_check' not in copy['steps'][0]


def test_current_failure_and_running_steps_do_not_borrow_previous_success(owner):
    iid=prepare(owner)
    journal(owner,iid,5,[('market','ready','Earlier success.'),('reddit','ready','Earlier success.')])
    current=journal(owner,iid,1,[('market','failed','Failed.'),('reddit','running','Working.')])
    with transaction(owner,consistent=True) as c:
        loading.add_previous_results(c,current)
    assert all('previous_check' not in s for s in current['steps'])


def test_optional_x_off_is_distinct_from_enabled_connection_failure(owner,monkeypatch):
    from thesis.providers import settings
    iid=prepare(owner)
    journal(owner,iid,1,[('x','blocked','Configure X.')])
    monkeypatch.setattr(settings,'settings',lambda:dict(THESIS_X_ENABLED='false'))
    assert loading.latest(owner,iid)['steps'][0]['optional_source_off'] is True
    monkeypatch.setattr(settings,'settings',lambda:dict(THESIS_X_ENABLED='true'))
    assert 'optional_source_off' not in loading.latest(owner,iid)['steps'][0]


def filing_check(iid, minutes, outcome):
    at = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    with transaction(admin=True) as conn:
        return one(conn, """INSERT INTO source_checks(id,stage,instrument_id,source_id,checked_at,outcome,error)
                   VALUES(%s,0,%s,'sec-companyfacts',%s,%s,%s) RETURNING *""",
                   (uuid4(), iid, at, outcome, None if outcome=='success' else 'SEC connection failed.'))


@pytest.mark.parametrize('outcome,status', [('success','ready'),('failed','failed'),('denied','failed')])
def test_cached_filings_use_newer_direct_or_watch_source_check(owner, outcome, status):
    iid = add_company('MSFT')['instrument_id']
    old = journal(owner,iid,5,[('filings','failed','Old loading failure.')])
    check = filing_check(iid,3,outcome)
    current = journal(owner,iid,1,[('filings','cached','Skipped recent request.')])
    visible = loading.latest(owner,iid)['steps'][0]
    assert visible['previous_check']['source_check_id'] == str(check['id'])
    assert visible['previous_check']['status'] == status
    assert visible['previous_check']['message'] == ('Filing data checked successfully.' if outcome=='success' else 'SEC connection failed.')
    with transaction(owner,consistent=True) as conn:
        for run in [old,current]:
            assert one(conn,'SELECT steps FROM research_loads WHERE id=%s',(run['id'],))['steps']==run['steps']


@pytest.mark.parametrize('case', ['later','older','other_company','withdrawn','current_failure'])
def test_source_checkpoint_does_not_override_wrong_period_scope_or_current_failure(owner, case):
    iid = add_company('MSFT')['instrument_id']
    old = journal(owner,iid,5,[('filings','failed','Old loading failure.')])
    other = add_company('AAPL')['instrument_id'] if case=='other_company' else iid
    filing_check(other, 0 if case=='later' else 8 if case=='older' else 3, 'success')
    current = journal(owner,iid,1,[('filings','failed' if case=='current_failure' else 'cached','Current result.')])
    if case=='withdrawn':
        with transaction(admin=True) as conn:
            conn.execute("UPDATE sources SET entitlement='fictional' WHERE id='sec-companyfacts'")
    visible = loading.latest(owner,iid)['steps'][0]
    if case=='current_failure':
        assert 'previous_check' not in visible
    else:
        assert visible['previous_check']['run_id'] == old['id']
