"""Exact citation, immutable reuse, source permissions and private-state controls."""
import json
from uuid import uuid4
from copy import deepcopy
import pytest
from thesis.db import transaction,one
from thesis.providers import ledger
from thesis.research import business as B
from thesis.research.sec import disclosures
from thesis.research.sec.service import add_company
from thesis import service
from test_disclosures import HTML,metadata,reset_attempt
from test_model_budget import clean_model_ledger


@pytest.fixture(autouse=True)
def business_source(owner,clean_model_ledger):
    with transaction(admin=True) as conn:
        conn.execute("INSERT INTO sources VALUES('sec-disclosures','SEC originals','sec-public') ON CONFLICT DO NOTHING")


def setup():
    iid=add_company('MSFT')['instrument_id'];disclosures.refresh(iid,submissions=metadata(),fetcher=lambda _:HTML)
    return iid


def response(body,change=None):
    packet=json.loads(body['input'][1]['content']);source=packet['sources'][0];p=next(p for p in source['passages'] if 'subscription software' in p['quote'])
    result=dict(findings=[dict(category='revenue_model',kind='company_statement',text='The company says it sells subscription software to business customers.',citations=[dict(source_id=source['id'],passage_id=p['id'])])],gaps=['Competition is not established by the selected passages.'],questions=['How dependent is revenue on its largest customers?'])
    if change:change(result,packet)
    return dict(id='resp_'+str(uuid4()),model=body['model'],service_tier='default',status='completed',usage=dict(input_tokens=100,output_tokens=100),output=[dict(type='message',content=[dict(type='output_text',text=json.dumps(result))])])


def test_explicit_cached_shared_brief_has_original_evidence_without_private_input(owner):
    iid=setup();before=service.state(owner,iid)
    result=B.generate(iid,transport=response,owner=owner)
    repeat=B.generate(iid,transport=lambda _:pytest.fail('Duplicate paid request'),owner=owner)
    assert result['id']==repeat['id']
    assert 'subscription software' in result['result']['findings'][0]['citations'][0]['quote']
    with transaction() as conn:
        saved=one(conn,'SELECT * FROM business_briefs WHERE id=%s',(result['id'],))
        assert not {'reasoning','owner_id','versions'} & set(saved['packet'])
    after=service.state(owner,iid)
    for key in ('versions','news_watch','research_action','updates'):assert before.get(key)==after.get(key)
    assert B.history(iid)['current']['id']==result['id']
    assert B.history(iid)['sample_changed'] is False
    name,html=B.download(iid,result['id']);assert 'https://www.sec.gov/Archives/' in html and 'subscription software' in html


@pytest.mark.parametrize('field,value',[('source_id',str(uuid4())),('passage_id','invented')])
def test_cross_source_and_invented_citations_cannot_publish(owner,field,value):
    iid=setup()
    def change(result,_):result['findings'][0]['citations'][0][field]=value
    with pytest.raises(ValueError,match='evidence'):B.generate(iid,transport=lambda body:response(body,change),owner=owner)
    assert B.history(iid)['latest'] is None


def test_invented_figures_and_source_withdrawal_are_visible(owner):
    iid=setup()
    def change(result,_):result['findings'][0]['text']='The company earns 999 billion dollars.'
    record=B.generate(iid,transport=lambda body:response(body,change),owner=owner)
    assert record['result']['findings']==[] and len(record['result']['withheld_findings'])==1
    assert '999' not in json.dumps(record['result'])
    # Same request already settled: parsing failure must not cause another call.
    assert B.generate(iid,transport=lambda _:pytest.fail('Automatic paid retry'),owner=owner)['id']==record['id']


def test_revoked_access_withholds_history_and_export(owner):
    iid=setup();record=B.generate(iid,transport=response,owner=owner)
    with transaction(admin=True) as conn:conn.execute("UPDATE sources SET entitlement='fictional' WHERE id='sec-disclosures'")
    saved=B.history(iid)['latest'];assert saved['withheld'] and not saved['sources'] and saved['result'] is None
    assert 'subscription software' not in B.download(iid,record['id'])[1]


def test_selection_change_and_restored_original_reuse_historical_brief(owner):
    iid=setup();first=B.generate(iid,transport=response,owner=owner)
    reset_attempt(iid);disclosures.refresh(iid,submissions=metadata(),fetcher=lambda _:HTML.replace(b'business customers',b'enterprise customers'))
    assert B.history(iid)['sample_changed']
    reset_attempt(iid);disclosures.refresh(iid,submissions=metadata(),fetcher=lambda _:HTML)
    assert B.generate(iid,transport=lambda _:pytest.fail('Restored original was charged'),owner=owner)['id']==first['id']


def test_unknown_call_blocks_paid_retry_and_permission_change_blocks_publication(owner):
    iid=setup()
    def fail(_):raise TimeoutError('controlled timeout')
    with pytest.raises(Exception):B.generate(iid,transport=fail,owner=owner)
    with pytest.raises(Exception):B.generate(iid,transport=lambda _:pytest.fail('Retried unknown'),owner=owner)
    assert B.history(iid)['latest'] is None
