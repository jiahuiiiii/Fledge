"""Quarter history never loses Q4 merely because it is in a 10-K."""
from copy import deepcopy
from datetime import datetime, timezone
import json, os
from pathlib import Path
import pytest
from thesis.research.sec.financial_story import normalize_story
from thesis.research.sec.normalize import REVENUE
from test_financial_depth import trailing_bundle
from test_sec_fundamentals import CIK, NOW


def bundle():
    data = trailing_bundle()
    recent = data['submissions']['filings']['recent']
    for key, value in dict(accessionNumber='0000789019-26-000003', form='10-K', reportDate='2026-09-30',
        filingDate='2026-10-30', acceptanceDateTime='2026-10-30T20:00:00Z', primaryDocument='annual.htm').items():
        recent[key].append(value)
    facts = data['companyfacts']['facts']['us-gaap']
    for tag, value in [(REVENUE[0], '250.1234567890123456789'), ('NetIncomeLoss', '60'), ('OperatingIncomeLoss', '75')]:
        facts[tag]['units']['USD'].append(dict(val=value, accn=recent['accessionNumber'][-1], form='10-K',
            filed='2026-10-30', start='2025-10-01', end='2026-09-30'))
    return data


def result(data):
    return normalize_story(data, CIK, datetime(2026, 11, 1, tzinfo=timezone.utc))


def last(data): return {m['key']: m for m in result(data)['quarterly'][-1]['metrics']}


def test_fourth_quarter_exact_arithmetic_dates_and_original_evidence():
    data=bundle();before=deepcopy(data);m=last(data)['revenue']
    assert m['value']=='80.1234567890123456789' and m['calculated']
    assert (m['start'],m['end'])==('2026-07-01','2026-09-30')
    assert [f['value'] for f in m['inputs']]==['250.1234567890123456789','170']
    assert len({f['accession'] for f in m['inputs']})==2
    assert all(f['filing_url'].startswith('https://www.sec.gov/Archives/') for f in m['inputs'])
    assert last(data)['net_income']['value']=='10'
    assert 'free_cash_flow' not in last(data)
    assert data==before


def test_reported_fourth_quarter_precedes_calculation_and_conflict_is_not_masked():
    data=bundle();facts=data['companyfacts']['facts']['us-gaap'][REVENUE[0]]['units']['USD']
    reported=dict(facts[-1],start='2026-07-01',val='81')
    facts.append(reported)
    assert last(data)['revenue']['value']=='81' and not last(data)['revenue']['calculated']
    facts.append(dict(reported,val=82))
    assert last(data)['revenue']['value'] is None
    assert 'Conflicting' in last(data)['revenue']['reason']


@pytest.mark.parametrize('problem',['concept','dates','currency','conflict','amendment','late','missing','reported_eur'])
def test_incompatible_quarter_inputs_are_not_subtracted(problem):
    data=bundle();gaap=data['companyfacts']['facts']['us-gaap'];units=gaap[REVENUE[0]]['units'];facts=units['USD']
    ytd=next(r for r in facts if r['end']=='2026-06-30')
    if problem=='concept':
        facts.remove(ytd);gaap['Revenues']={'units':{'USD':[ytd]}}
    if problem=='dates': ytd['start']='2025-10-02'
    if problem=='currency':facts.remove(ytd);units['EUR']=[ytd]
    if problem=='conflict':facts.append(dict(ytd,val=171))
    if problem=='missing':facts.remove(ytd)
    if problem=='reported_eur':units['EUR']=[dict(facts[-1],start='2026-07-01',val=81)]
    if problem in ('amendment','late'):
        recent=data['submissions']['filings']['recent']
        if problem=='amendment':recent['form'][1]='10-Q/A';ytd['form']='10-Q/A'
        else:recent['acceptanceDateTime'][1]='2026-10-31T20:00:00Z'
    assert last(data)['revenue']['value'] is None


def test_whole_group_and_parent_quarter_profit_do_not_mix():
    data=bundle();gaap=data['companyfacts']['facts']['us-gaap']
    parent=gaap['NetIncomeLoss']['units']['USD'][-1]
    gaap['ProfitLoss']={'units':{'USD':[dict(parent,val=65)]}}
    assert last(data)['net_income']['label']=='Net income attributable to parent'
    assert last(data)['net_income']['value']=='10'
    gaap['ProfitLoss']['units']['USD'] += [dict(parent,start='2026-07-01',val=12),dict(parent,start='2026-07-01',val=13)]
    assert last(data)['net_income']['value'] is None
    assert 'Conflicting' in last(data)['net_income']['reason']


def test_dual_tagged_exact_inputs_can_establish_the_same_q4_definition():
    data=bundle();gaap=data['companyfacts']['facts']['us-gaap']
    facts=gaap[REVENUE[0]]['units']['USD']
    ytd=next(r for r in facts if r['end']=='2026-06-30')
    facts.remove(ytd)
    gaap['Revenues']={'units':{'USD':[dict(facts[-1]),ytd]}}
    m=last(data)['revenue']
    assert m['value']=='80.1234567890123456789'
    assert {f['concept'] for f in m['inputs']}=={'Revenues'}


@pytest.mark.parametrize('symbol',['AAPL','INTU','QCOM','AMD','AVGO','MU','NVDA','MRVL','FN'])
def test_saved_company_history_retains_old_values_and_has_q4(symbol):
    root=os.getenv('THESIS_FINANCIAL_RECOVERY_CORPUS')
    if not root:pytest.skip('Optional saved public filing corpus')
    saved=json.loads((Path(root)/symbol/'manifest.json').read_text())['saved']
    data=saved['payload'];now=datetime.fromisoformat(saved['checked_at'])
    story=normalize_story(data,saved['cik'],now)
    fourth=[p for p in story['quarterly'] if p['form']=='10-K']
    assert fourth
    assert any(next(m for m in p['metrics'] if m['key']=='revenue')['value'] is not None for p in fourth)
    for p in fourth:
        for m in p['metrics']:
            if m['value'] is not None:
                assert m['start'] and m['end']==p['end']
                if m['calculated']:
                    assert len({f['concept'] for f in m['inputs']})==1
                    assert len(m['inputs'])==2 and m['inputs'][0]['start']==m['inputs'][1]['start']
    assert all(p['kind']=='quarter' for p in story['quarterly'])
