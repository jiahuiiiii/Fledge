"""Public statement inputs; mocked AI; disposable database only."""
from copy import deepcopy
from uuid import uuid4
import json
import pytest
from thesis.db import transaction,one
from thesis.research.sec import financial_recovery as R,filing_facts as F,disclosures
from thesis.research.sec.service import add_company
from test_model_budget import clean_model_ledger
from test_disclosures import disclosure_scope,metadata,reset_attempt
from test_sec_fundamentals import apply,bundle
from test_segment_revenue import filing,context,fact


def source():
    raw=filing(members=[],more_facts='<table><tr><td>Cost of revenue</td><td>'+fact('total','40',concept='custom:CostOfRevenue',id='custom-cost')+'</td></tr></table>')
    return raw


def setup(owner):
    iid=add_company('MSFT')['instrument_id'];apply(iid,bundle(annual=True))
    disclosures.refresh(iid,submissions=metadata(),fetcher=lambda _:source())
    with transaction(owner,consistent=True) as c:plan=R.present(c,iid)
    return iid,plan


def response(body):
    packet=json.loads(body['input'][1]['content'])
    return dict(id='resp_'+str(uuid4()),model=body['model'],service_tier='default',status='completed',usage=dict(input_tokens=100,output_tokens=100),
                output=[dict(type='message',content=[dict(type='output_text',text=json.dumps(dict(items=[dict(target='cost',operation='reported',inputs=['custom-cost'],explanation='The original statement labels this consolidated annual cost of revenue.')])) )])])


def test_optional_review_cache_revoke_and_owner_isolation(owner,clean_model_ledger,disclosure_scope):
    iid,p=setup(owner)
    assert p['can_run'] and p['maximum_cost_usd']>0 and 'cost' in [m['key'] for m in p['missing']]
    with transaction(owner) as c:assert one(c,'SELECT count(*) n FROM model_calls')['n']==0
    r=R.generate(owner,iid,p['document']['id'],p['plan_id'],transport=response)
    assert r['accepted']==[] and r['result']['items'][0]['value']=='40000000'
    assert R.generate(owner,iid,p['document']['id'],p['plan_id'],transport=lambda _:pytest.fail('duplicate call'))['id']==r['id']
    with transaction(admin=True) as c:
        other=str(uuid4());c.execute('INSERT INTO accounts VALUES(%s,%s)',(other,'Other owner'))
    with transaction(other) as c:assert one(c,'SELECT count(*) n FROM financial_recovery_readings')['n']==0
    with pytest.raises(ValueError,match='account'):R.review(other,iid,r['id'],['cost'],None)
    saved=R.review(owner,iid,r['id'],['cost'],None)
    with transaction(owner) as c:
        doc=one(c,'SELECT id,content_hash FROM disclosure_documents WHERE id=%s',(p['document']['id'],))
        overlay=R.apply_reviewed(c,iid,{},[doc]);assert overlay['_original_facts']['CostOfRevenue'][0]['value']=='40000000'
        with pytest.raises(Exception):c.execute('UPDATE financial_recovery_readings SET result=%s WHERE id=%s',('{}',r['id']))
    with pytest.raises(ValueError,match='elsewhere'):R.review(owner,iid,r['id'],[],None)
    revoked=R.review(owner,iid,r['id'],[],saved['review_id']);assert revoked['accepted']==[]
    with transaction(owner) as c:assert R.apply_reviewed(c,iid,{},[doc])['_ai_recovery_count']==0


def test_source_withdrawal_and_changed_plan(owner,clean_model_ledger,disclosure_scope):
    iid,p=setup(owner)
    with pytest.raises(ValueError,match='selection changed'):R.generate(owner,iid,p['document']['id'],'wrong',transport=lambda _:pytest.fail('dispatched'))
    r=R.generate(owner,iid,p['document']['id'],p['plan_id'],transport=response)
    reset_attempt(iid);disclosures.refresh(iid,submissions=metadata(),fetcher=lambda _:source().replace(b'>40<',b'>41<'))
    with transaction(owner) as c:
        row=one(c,'SELECT * FROM financial_recovery_readings WHERE id=%s',(r['id'],));assert R.visible(c,row)['withheld']
    with pytest.raises(ValueError,match='unavailable'):R.review(owner,iid,r['id'],['cost'],None)
    with transaction(admin=True) as c:c.execute("UPDATE sources SET entitlement='fictional' WHERE id='sec-disclosures'")
    with transaction(owner) as c:
        with pytest.raises(ValueError,match='access'):R.present(c,iid)


def test_unsettled_call_is_never_retried(owner,clean_model_ledger,disclosure_scope):
    iid,p=setup(owner)
    def fail(_):raise TimeoutError('authored interruption')
    with pytest.raises(Exception):R.generate(owner,iid,p['document']['id'],p['plan_id'],transport=fail)
    with pytest.raises(Exception):R.generate(owner,iid,p['document']['id'],p['plan_id'],transport=lambda _:pytest.fail('paid retry'))
    with transaction(owner) as c:
        assert not R.present(c,iid)['can_run'];assert one(c,'SELECT count(*) n FROM model_calls')['n']==1


def packet():
    return dict(kind='annual',missing=[dict(key='cost')],cells=[dict(id='a',concept='custom:ServiceCost',label='Service cost',text='Service cost 0.1',value='0.1',unit='USD',start='2024-10-01',end='2025-09-30'),dict(id='b',concept='custom:ProductCost',label='Product cost',text='Product cost 0.2',value='0.2',unit='USD',start='2024-10-01',end='2025-09-30')])


def rendered(items,p=None):
    return R.render(dict(status='settled',response_body=dict(status='completed',output=[dict(type='message',content=[dict(type='output_text',text=json.dumps(dict(items=items)))])])),p or packet())


def item():return dict(target='cost',operation='sum',inputs=['a','b'],explanation='Separately reported service and product costs.')


def test_exact_decimal_arithmetic_and_duplicate_targets():
    assert rendered([item()])['items'][0]['value']=='0.3'
    assert rendered([item(),item()])['items']==[]


@pytest.mark.parametrize('mutation',['invented','repeated','period','unit','quarter-ytd','same-concept','negative','invented-target','operation','extra-value'])
def test_incompatible_ai_suggestions_stay_unknown(mutation):
    p=packet();i=item()
    if mutation=='invented':i['inputs']=['unknown']
    if mutation=='repeated':i['inputs']=['a','a']
    if mutation=='period':p['cells'][1]['start']='2024-01-01'
    if mutation=='unit':p['cells'][1]['unit']='EUR'
    if mutation=='quarter-ytd':p['kind']='quarter'
    if mutation=='same-concept':p['cells'][1]['concept']=p['cells'][0]['concept']
    if mutation=='negative':p['cells'][1]['value']='-3'
    if mutation=='invented-target':i['target']='made_up'
    if mutation=='operation':i['operation']='multiply'
    if mutation=='extra-value':i['value']='999'
    assert rendered([i],p)['items']==[]


def test_whole_filing_facts_overlay_is_exact_and_does_not_mutate_raw():
    from datetime import datetime,timezone
    from hashlib import sha256
    from thesis.research.sec.disclosure_text import archive_url
    raw=source().replace(b'custom:CostOfRevenue',b'us-gaap:CostOfRevenue');b=bundle(annual=True);before=deepcopy(b)
    d=dict(id=str(uuid4()),url=archive_url(789019,'0000789019-25-000001','example-20250930.htm'),form='10-K',raw_html=raw,content_hash=sha256(raw).hexdigest())
    out=F.attach(b,[d],789019,datetime.now(timezone.utc))
    assert out['_original_facts']['CostOfRevenue'][0]['value']=='40000000' and b==before
    d['content_hash']='wrong';assert not F.attach(b,[d],789019,datetime.now(timezone.utc))['_original_facts']


def test_split_exhibit_row_recovers_only_same_accession():
    from thesis.research.sec.disclosure_text import parse,exhibits,archive_url
    from test_disclosures import HTML
    raw=HTML.replace(b'</body>',b'<table><tr><td>99.1</td><td><a href="fy26q4earningspressrelease.htm">Press</a> release for financial results</td></tr></table></body>')
    url=archive_url(789019,'0000789019-25-000001','main.htm')
    assert exhibits(parse(raw,form='8-K',cik=789019),url)==[url.rsplit('/',1)[0]+'/fy26q4earningspressrelease.htm']


def test_access_revoked_during_paid_call_keeps_charge_without_publishing(owner,clean_model_ledger,disclosure_scope):
    iid,p=setup(owner)
    def withdraw(body):
        with transaction(admin=True) as c:c.execute("UPDATE sources SET entitlement='fictional' WHERE id='sec-disclosures'")
        return response(body)
    with pytest.raises(ValueError,match='access changed'):R.generate(owner,iid,p['document']['id'],p['plan_id'],transport=withdraw)
    with transaction(admin=True) as c:
        assert one(c,'SELECT count(*) n FROM financial_recovery_readings')['n']==0
        assert one(c,"SELECT count(*) n FROM model_calls WHERE status='settled'")['n']==1
        c.execute("UPDATE sources SET entitlement='sec-public' WHERE id='sec-disclosures'")
    with transaction(owner) as c:
        retry=R.present(c,iid);assert retry['maximum_cost_usd']==0 and retry['can_run']
    assert R.generate(owner,iid,p['document']['id'],p['plan_id'],transport=lambda _:pytest.fail('duplicate charge'))['accepted']==[]


def test_unusable_settled_response_stays_blocked_without_new_call(owner,clean_model_ledger,disclosure_scope):
    iid,p=setup(owner)
    def unusable(body):
        value=response(body);value['output'][0]['content'][0]['text']='not json';return value
    with pytest.raises(ValueError,match='unusable'):R.generate(owner,iid,p['document']['id'],p['plan_id'],transport=unusable)
    with transaction(owner) as c:
        preview=R.present(c,iid);assert not preview['can_run'] and preview['maximum_cost_usd']==0
        assert 'unusable' in preview['message']
    with pytest.raises(ValueError,match='unusable'):R.generate(owner,iid,p['document']['id'],p['plan_id'],transport=lambda _:pytest.fail('duplicate charge'))
