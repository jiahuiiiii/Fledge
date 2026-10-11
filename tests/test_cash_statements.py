"""General original cash-flow recovery, without issuer names or inferred zeros."""
from copy import deepcopy
from datetime import datetime,timezone
import json,os
from pathlib import Path
import pytest
from thesis.research.sec import cash_statements as C,filing_facts as F,financial_story as S,financial_depth as D
from thesis.research.sec.normalize import filing_rows
from test_original_statements import statement
from test_segment_revenue import fact
from test_financial_depth import trailing_bundle


def cash_table(label='Purchases related to property and equipment and intangible assets',tag='custom:CashPurchases',value='12'):
    return statement([
      ('Cash flows from operating activities:',''),('Net income',fact('total','30',concept='us-gaap:NetIncomeLoss',id='net')),
      ('Net cash provided by operating activities',fact('total','50',concept='us-gaap:'+C.CONTINUING,id='ocf')),
      ('Cash flows from investing activities:',''),(label,fact('total',value,concept=tag,id='capex')),
      ('Net cash used in investing activities',fact('total','-12',concept='us-gaap:NetCashProvidedByUsedInInvestingActivities',id='invest')),
      ('Cash flows from financing activities:',''),('Net cash used in financing activities',fact('total','-5',concept='us-gaap:NetCashProvidedByUsedInFinancingActivities',id='finance'))])


def evidence():
    b=trailing_bundle();f=filing_rows(b['submissions'],datetime(2026,11,1,tzinfo=timezone.utc))[0]
    return b,f


def recover(raw,b=None,f=None):
    if b is None:b,f=evidence()
    return C.tagged_recoveries(F.read(raw,789019),b,f)


def test_custom_capital_spending_in_original_cash_statement_general_labels():
    rows=recover(cash_table());m=next(r for r in rows if r['target']==C.PRODUCTIVE)
    assert m['value']=='12000000' and m['inputs'][0]['concept']=='custom:CashPurchases'
    assert m['inputs'][0]['row_label']=='Purchases related to property and equipment and intangible assets'
    assert next(r for r in rows if r['target']==C.OPERATING)['value']=='50000000'
    assert any(r['target']==C.PPE for r in recover(cash_table('Payments for acquisition of property, plant and equipment')))


@pytest.mark.parametrize('label',['Principal payments on property and equipment','Property and equipment acquired in business combinations','Purchases of property and equipment, net of proceeds','Noncash purchases of property and equipment','Purchases of intangible assets'])
def test_other_amounts_are_not_capital_spending(label):
    assert not any(r['target'] in (C.PPE,C.PRODUCTIVE) for r in recover(cash_table(label)))


@pytest.mark.parametrize('problem',['negative','currency','dimension','financing','missing_section','discontinued','hidden'])
def test_unsupported_cash_statement_cells_remain_unavailable(problem):
    raw=cash_table()
    if problem=='negative':raw=cash_table(value='-12')
    if problem=='currency':raw=raw.replace(b'iso4217:USD',b'iso4217:EUR')
    if problem=='dimension':raw=raw.replace(b'contextRef="total"',b'contextRef="s0"')
    if problem=='financing':raw=raw.replace(b'Cash flows from investing activities:',b'Cash flows from financing activities:')
    if problem=='missing_section':raw=raw.replace(b'financing activities',b'other activities')
    if problem=='discontinued':raw=raw.replace(b'Net income',b'Net income from discontinued operations')
    if problem=='hidden':raw=raw.replace(b'<table>',b'<table style="display:none">')
    assert not any(r['target']==C.PRODUCTIVE for r in recover(raw))


def legacy(bundle,filing,value='50',label='Net cash provided by operating activities',scale='millions',year='2025'):
    f=dict(accn=filing['accessionNumber'],form=filing['form'],filed=filing['filingDate'],start='2024-10-01',end='2025-09-30',val=50000000)
    bundle['companyfacts']['facts']['us-gaap'][C.CONTINUING]={'units':{'USD':[f]}}
    return (f'<html><p>Consolidated statements of cash flows (in {scale})</p><table><tr><td>Year ended {year}</td></tr>'
      '<tr><td>Net income</td><td>30</td></tr><tr><td>Operating activities</td></tr>'
      f'<tr><td>{label}</td><td>$</td><td>{value}</td></tr><tr><td>Investing activities</td></tr><tr><td>Financing activities</td></tr></table></html>').encode()


def test_legacy_total_needs_exact_original_amount_scale_and_year():
    b,f=evidence();raw=legacy(b,f);before=deepcopy(b)
    r=C.legacy_recoveries(raw,b,f);assert r[0]['value']=='50000000' and r[0]['inputs'][0]['concept']==C.CONTINUING
    assert b==before
    for bad in [legacy(b,f,value='51'),legacy(b,f,scale='thousands'),legacy(b,f,scale='units'),legacy(b,f,year='2024'),legacy(b,f,label='Cash provided by continuing operating activities'),raw.replace(b'<table>',b'<table hidden>')]:
        assert not C.legacy_recoveries(bad,b,f)
    # Parentheses may be in their own cell; negative operating cash is valid.
    raw=legacy(b,f,value='(50</td><td>)',label='Net cash (used in) provided by operating activities')
    b['companyfacts']['facts']['us-gaap'][C.CONTINUING]['units']['USD'][0]['val']=-50000000
    assert C.legacy_recoveries(raw,b,f)[0]['value']=='-50000000'


def test_discontinued_operations_are_not_assumed_zero():
    b,f=evidence();raw=legacy(b,f)
    source=b['companyfacts']['facts']['us-gaap'][C.CONTINUING]['units']['USD'][0]
    b['companyfacts']['facts']['us-gaap']['CashProvidedByUsedInOperatingActivitiesDiscontinuedOperations']={'units':{'USD':[dict(source,val=1)]}}
    assert not C.legacy_recoveries(raw,b,f)
    b['companyfacts']['facts']['us-gaap']['CashProvidedByUsedInOperatingActivitiesDiscontinuedOperations']['units']['USD'][0]['val']='0'
    assert C.legacy_recoveries(raw,b,f)


def test_recovered_ppe_keeps_its_scope_when_standard_ppe_is_absent():
    b,f=evidence();b['companyfacts']['facts']['us-gaap'].pop(C.PPE,None)
    b['_original_facts']={C.PPE:[dict(concept=C.PPE,namespace='app-calculation',value='12',unit='USD',start='2024-10-01',end=f['end'].isoformat(),accession=f['accessionNumber'],form=f['form'],filed=f['filingDate'])]}
    result=D.capital_spending(b,filing_rows(b['submissions'],datetime(2026,11,1,tzinfo=timezone.utc)),f)
    assert result['value']=='12' and result['spending_basis']=='property_plant_equipment'


@pytest.mark.parametrize('symbol',['AAPL','AMD','AVGO','FN','INTU','MRVL','MU','NVDA','QCOM'])
def test_actual_saved_cash_history_preserves_original_values(symbol):
    root=os.getenv('THESIS_CASH_FLOW_CORPUS')
    if not root:pytest.skip('Optional retained original cash-flow corpus')
    folder=Path(root)/symbol;m=json.loads((folder/'manifest.json').read_text());saved=m['saved'];now=datetime.fromisoformat(saved['checked_at'])
    docs=[dict(d,raw_html=(folder/d['filename']).read_bytes()) for d in m['documents']]
    base=saved['payload'];before=deepcopy(base);enriched=F.attach(base,docs,saved['cik'],now)
    old=S.normalize_story(base,saved['cik'],now);new=S.normalize_story(enriched,saved['cik'],now)
    for kind in ['annual','trailing']:
        by_id={p['id']:p for p in new[kind]}
        for p in old[kind]:
            after={m['key']:m for m in by_id[p['id']]['metrics']}
            for metric in p['metrics']:
                if metric['value'] is not None:assert after[metric['key']]['value']==metric['value'],(symbol,kind,p['end'],metric['key'])
    if symbol in ('AAPL','NVDA','FN'):
        assert all(next(m for m in p['metrics'] if m['key']=='free_cash_flow')['value'] is not None for p in new['annual'])
    assert base==before


def test_original_filing_plan_is_bounded_and_issuer_independent():
    from thesis.research.sec.disclosures import cash_flow_history_plan
    b,f=evidence();before=deepcopy(b);now=datetime(2026,11,1,tzinfo=timezone.utc)
    # Complete structured cash inputs need no additional originals.
    assert cash_flow_history_plan(b,789019,now)==[]
    gaap=b['companyfacts']['facts']['us-gaap']
    gaap[C.CONTINUING]=gaap.pop(C.OPERATING)
    plan=cash_flow_history_plan(b,789019,now)
    assert plan and all(p['history'] and p['slot']=='cash_flow_history' for p in plan)
    assert len({p['url'] for p in plan})==len(plan)
    assert {p['accession'] for p in plan}.issubset({x['accessionNumber'] for x in filing_rows(b['submissions'],now)})
    with pytest.raises(ValueError):cash_flow_history_plan(b,320193,now)
    b['companyfacts']['facts']['us-gaap'][C.OPERATING]=b['companyfacts']['facts']['us-gaap'].pop(C.CONTINUING)
    assert b==before


def test_recovery_cannot_mask_reported_conflicts_or_other_currency():
    from thesis.research.sec.performance import collect,select
    b,f=evidence();gaap=b['companyfacts']['facts']['us-gaap'];existing=collect(b,f,(C.OPERATING,))[0]
    b['_original_facts']={C.OPERATING:[dict(existing,value='999',namespace='app-calculation')]}
    facts=collect(b,f,(C.OPERATING,));assert all(x['value']!='999' for x in facts)
    raw=gaap[C.OPERATING]['units']['USD'][0]
    gaap[C.OPERATING]['units']['USD'].append(dict(raw,val=999))
    assert select(collect(b,f,(C.OPERATING,)),f,'annual','Business performance',(C.OPERATING,))[0] is None
    gaap[C.OPERATING]['units']={'EUR':[raw]}
    assert collect(b,f,(C.OPERATING,))==[]


def test_invalid_inline_filing_does_not_fall_back_to_legacy_html(monkeypatch):
    import hashlib
    from thesis.research.sec.disclosure_text import archive_url
    b,f=evidence();raw=cash_table();calls=[]
    def reject(*args):raise ValueError('Invalid inline structure')
    monkeypatch.setattr(F,'read',reject)
    monkeypatch.setattr(C,'legacy_recoveries',lambda *args:calls.append(args) or [])
    doc=dict(id='bad-inline',form=f['form'],url=archive_url(789019,f['accessionNumber'],f['primaryDocument']),raw_html=raw,content_hash=hashlib.sha256(raw).hexdigest())
    F.attach(b,[doc],789019,datetime(2026,11,1,tzinfo=timezone.utc))
    assert not calls
