"""A skipped repeat exposes dated prior results, never invented availability."""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
from uuid import uuid4
from psycopg.types.json import Jsonb
from thesis.config import OWNER
from thesis.db import transaction,one
from thesis.research import loading
from test_market import prepare


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
