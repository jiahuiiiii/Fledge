"""Independent arithmetic/date controls over authored SEC-format inputs."""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import pytest
from thesis.research.sec.financial_depth import normalize_depth
from thesis.research.sec.normalize import REVENUE
from test_sec_fundamentals import bundle, CIK, NOW


def trailing_bundle():
    annual=bundle(annual=True,revenue=500,prior=400,income=100)
    current=bundle(accession='0000789019-26-000002',revenue=170,prior=120,income=40)
    r=current['submissions']['filings']['recent']
    r['reportDate']=['2026-06-30'];r['filingDate']=['2026-07-30'];r['acceptanceDateTime']=['2026-07-30T20:00:00Z']
    for tag in current['companyfacts']['facts']['us-gaap'].values():
        for i,f in enumerate(tag['units']['USD']):
            f.update(start='2025-10-01' if i==0 else '2024-10-01',end='2026-06-30' if i==0 else '2025-06-30',filed='2026-07-30')
    data=deepcopy(annual)
    for key,values in r.items():data['submissions']['filings']['recent'][key]+=values
    facts=data['companyfacts']['facts']['us-gaap']
    for key,value in current['companyfacts']['facts']['us-gaap'].items():facts[key]['units']['USD']+=value['units']['USD']
    for tag,values in [('NetCashProvidedByUsedInOperatingActivities',(90,60,40)),('PaymentsToAcquirePropertyPlantAndEquipment',(35,15,10)),('NetIncomeLoss',(70,50,30))]:
        facts[tag]={'units':{'USD':[]}}
        for value,accn,form,filed,start,end in [(values[0],'0000789019-25-000001','10-K','2025-10-30','2024-10-01','2025-09-30'),(values[1],'0000789019-26-000002','10-Q','2026-07-30','2025-10-01','2026-06-30'),(values[2],'0000789019-26-000002','10-Q','2026-07-30','2024-10-01','2025-06-30')]:
            facts[tag]['units']['USD'].append(dict(val=value,accn=accn,form=form,filed=filed,start=start,end=end))
    # Prior operating income is absent on purpose; margin must remain unknown.
    for tag,value in [('LongTermDebt',30),('LongTermDebtCurrent',5),('LongTermDebtNoncurrent',25),('ShortTermBorrowings',7),('CommercialPaper',7)]:
        facts[tag]={'units':{'USD':[dict(val=value,end='2026-06-30',accn='0000789019-26-000002',form='10-Q',filed='2026-07-30')]}}
    return data


def report(data=None):return normalize_depth(data or trailing_bundle(),CIK,NOW)
def keyed(result):return {row['key']:row for row in result['trailing']}


def test_trailing_bridge_fcf_and_debt_do_not_double_count():
    result=report();metrics=keyed(result)
    assert metrics['revenue']['value']=='550' # 500 + 170 - 120
    assert metrics['net_income']['value']=='90'
    assert metrics['free_cash_flow']['value']=='70' # (90+60-40)-(35+15-10)
    assert metrics['revenue']['start']=='2025-07-01' and metrics['revenue']['end']=='2026-06-30'
    assert metrics['operating_margin']['value'] is None
    assert result['debt']['value']=='37' # Total LTD includes its current part; CP is already in short-term debt.
    assert len(result['debt']['inputs'])==2
    assert all(f['filing_url'].startswith('https://www.sec.gov/Archives/') for f in metrics['revenue']['inputs'])


@pytest.mark.parametrize('change',['prior_missing','fiscal_gap','currency','conflict'])
def test_incomplete_or_incompatible_bridge_is_unknown(change):
    data=trailing_bundle();facts=data['companyfacts']['facts']['us-gaap'][REVENUE[0]]['units']['USD']
    if change=='prior_missing':facts.pop()
    elif change=='fiscal_gap':facts[-2]['start']='2025-10-03'
    elif change=='currency':data['companyfacts']['facts']['us-gaap'][REVENUE[0]]['units']={'EUR':facts}
    elif change=='conflict':facts.append(dict(facts[-1],val=121))
    metric=keyed(report(data))['revenue']
    assert metric['value'] is None and metric['reason']


def test_debt_missing_is_unknown_but_explicit_zero_is_valid():
    data=trailing_bundle();facts=data['companyfacts']['facts']['us-gaap'];del facts['ShortTermBorrowings']
    assert report(data)['debt']['value'] is None
    facts['ShortTermBorrowings']={'units':{'USD':[dict(facts['LongTermDebt']['units']['USD'][0],val=0)]}}
    assert report(data)['debt']['value']=='30'
    del facts['LongTermDebt']
    assert report(data)['debt']['value']=='30'
    del facts['LongTermDebtCurrent']
    assert report(data)['debt']['value'] is None


def test_annual_values_remain_reported_and_wrong_issuer_rejected():
    result=normalize_depth(bundle(annual=True),CIK,NOW)
    metric=keyed(result)['revenue']
    assert metric['value']=='120' and metric['calculated'] is False
    with pytest.raises(ValueError,match='another company'):normalize_depth(trailing_bundle(),320193,NOW)


def test_invalid_reported_debt_total_is_not_masked_with_components():
    data=trailing_bundle();facts=data['companyfacts']['facts']['us-gaap']
    facts['DebtLongtermAndShorttermCombinedAmount']={'units':{'USD':[dict(facts['LongTermDebt']['units']['USD'][0],val=-1)]}}
    assert report(data)['debt']['value'] is None
    facts['DebtLongtermAndShorttermCombinedAmount']['units']['USD']=[dict(facts['LongTermDebt']['units']['USD'][0],val=37),dict(facts['LongTermDebt']['units']['USD'][0],val=38)]
    assert report(data)['debt']['value'] is None


def test_text_filing_has_index_evidence_link_without_breaking_numbers():
    data=bundle(annual=True);data['submissions']['filings']['recent']['primaryDocument']=['report.txt']
    result=normalize_depth(data,CIK,NOW)
    assert keyed(result)['revenue']['value']=='120'
    assert keyed(result)['revenue']['inputs'][0]['filing_url'].endswith('-index.html')
