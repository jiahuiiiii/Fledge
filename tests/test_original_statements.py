"""Statement arithmetic and optional retained-public-filing regressions."""
from copy import deepcopy
from datetime import datetime
import json,os
from pathlib import Path
import pytest
from thesis.research.sec import filing_facts as F,income_flow,financial_depth,segment_revenue
from test_segment_revenue import context,fact,filing


def statement(rows,contexts=''):
    return filing(members=[],more_contexts=contexts,more_facts='<table>'+''.join('<tr><td>'+label+'</td><td>'+value+'</td></tr>' for label,value in rows)+'</table>')


def balance(extra=None):
    instant=context('instant').replace('<xbrli:startDate>2024-10-01</xbrli:startDate><xbrli:endDate>2025-09-30</xbrli:endDate>','<xbrli:instant>2025-09-30</xbrli:instant>')
    values=[('Assets','100'),('Liabilities','60'),('StockholdersEquity','40'),('LongTermDebtCurrent','5'),('LongTermDebtNoncurrent','20'),('CommercialPaper','2')]+(extra or [])
    return statement([(tag,fact('instant',val,concept='us-gaap:'+tag,id='v'+str(i))) for i,(tag,val) in enumerate(values)],instant)


def costs(extra=None):
    contexts=context('p','custom:ProductsMember',axis='srt:ProductOrServiceAxis')+context('s','custom:ServicesMember',axis='srt:ProductOrServiceAxis')
    values=[('Product revenue',fact('p','60',id='r-p')),('Service revenue',fact('s','40',id='r-s')),('Total revenue',fact('total','100',id='r-total')),('Cost of revenue:',''),
      ('Product cost',fact('p','20',concept='us-gaap:CostOfRevenue',id='c-p')),('Service cost',fact('s','15',concept='us-gaap:CostOfRevenue',id='c-s')),('Amortization',fact('total','5',concept='us-gaap:CostOfGoodsAndServicesSoldAmortization',id='amort'))]
    values+=extra or []
    values += [('Selling',fact('total','10',concept='us-gaap:SellingAndMarketingExpense',id='selling')),('Administration',fact('total','5',concept='us-gaap:GeneralAndAdministrativeExpense',id='admin')),('Total costs and expenses',fact('total','80',concept='us-gaap:CostsAndExpenses',id='all-cost')),('Operating income',fact('total','20',concept='us-gaap:OperatingIncomeLoss',id='op'))]
    return statement(values,contexts)


def recovered(raw):return {r['target']:r for r in F.statement_recoveries(F.read(raw,789019))}


def test_complete_balance_and_explicit_debt_scope():
    d=recovered(balance())['balance_sheet_borrowing'];assert d['value']=='27000000' and len(d['inputs'])==3
    assert 'Lease liabilities' in d['explanation']
    for raw in [balance([('ShortTermBorrowings','2')]),balance([('CommercialPaper','3')]),balance().replace(b'>100<',b'>101<'),balance().replace(b'iso4217:USD',b'iso4217:EUR')]:
        assert 'balance_sheet_borrowing' not in recovered(raw)


def test_cost_section_complete_and_not_a_subset_sum():
    result=recovered(costs());assert result['CostOfRevenue']['value']=='40000000'
    assert result['SellingGeneralAndAdministrativeExpense']['value']=='15000000'
    for extra in [[('Unfamiliar cost',fact('total','2',concept='custom:SpecialCost',id='extra'))],[('Untagged cost','2')]]:
        assert 'CostOfRevenue' not in recovered(costs(extra))
    assert 'CostOfRevenue' not in recovered(costs().replace(b'>60<',b'>61<'))


def test_zero_transform_requires_explicit_xbrl_zero():
    raw=filing(total='100',members=[('custom:OtherMember','100'),('custom:EmptyMember','—')])
    assert not segment_revenue.extract(raw,789019)['groups'][0]['chartable']
    zero=raw.replace(b'format="ixt:num-dot-decimal" id="f-s1"',b'format="ixt:fixed-zero" id="f-s1"')
    assert segment_revenue.extract(zero,789019)['groups'][0]['chartable']
    nil=zero.replace(b'id="f-s1"',b'id="f-s1" xsi:nil="true"')
    assert not segment_revenue.extract(nil,789019)['groups'][0]['chartable']


@pytest.mark.parametrize('symbol',['AAPL','INTU','QCOM','AMD','AVGO','MU','NVDA','MRVL','FN'])
def test_retained_originals_preserve_available_figures_and_restore_target_gaps(symbol):
    root=os.getenv('THESIS_FINANCIAL_RECOVERY_CORPUS')
    if not root:pytest.skip('Optional retained public filing corpus')
    root=Path(root)/symbol;m=json.loads((root/'manifest.json').read_text());saved=m['saved'];docs=[dict(d,raw_html=(root/d['filename']).read_bytes()) for d in m['documents']]
    now=datetime.fromisoformat(saved['checked_at']);base=saved['payload'];before=deepcopy(base)
    enriched=F.attach(base,docs,saved['cik'],now)
    from thesis.research.sec.amendments import Resolver
    from thesis.research.sec.disclosure_text import parse
    amendments={d['url'].split('/')[-2][:10]+'-'+d['url'].split('/')[-2][10:12]+'-'+d['url'].split('/')[-2][12:]:dict(d,data=parse(d['raw_html'],form=d['form'],cik=saved['cik'])) for d in docs if d['form'].endswith('/A')}
    from thesis.research.sec.normalize import filing_rows
    for f in filing_rows(base['submissions'],now):
        if f['accessionNumber'] in amendments:amendments[f['accessionNumber']]['data']['report_period_end']=f['end'].isoformat()
    original=income_flow.normalize_flow(base,saved['cik'],now,Resolver(base,saved['cik'],now,amendments));updated=income_flow.normalize_flow(enriched,saved['cik'],now,Resolver(enriched,saved['cik'],now,amendments))
    assert base==before and updated['periods'][0]['chartable']
    by_id={p['id']:p for p in updated['periods']}
    for old in original['periods']:
        new={m['key']:m for m in by_id[old['id']]['metrics']}
        for metric in old['metrics']:
            if metric['value'] is not None:assert new[metric['key']]['value']==metric['value'],(symbol,old['id'],metric['key'])
    if symbol in ('AAPL','INTU','QCOM'):
        debt=financial_depth.normalize_depth(enriched,saved['cik'],now)['debt']
        assert debt['value']=={'AAPL':'84344000000','INTU':'7669000000','QCOM':'15270000000'}[symbol]
    if symbol=='AMD':assert any(r['target']=='Liabilities' and r['value']=='17240000000' for d in docs for r in F.statement_recoveries(F.read(d['raw_html'],saved['cik'])))
    if symbol=='INTU':assert all(p['chartable'] for p in updated['periods'])
    if symbol in ('QCOM','AMD'):
        groups=[]
        for d in docs:
            for g in segment_revenue.extract(d['raw_html'],saved['cik'],True,True)['groups']:
                groups.append(dict(g,url=d['url'],form=d['form'],document_id=d['id'],content_hash=d['content_hash'],accepted_at=d['published_at'],available_at=d['available_at']))
        period=next(p for p in updated['periods'] if p['kind']=='trailing')
        trailing=segment_revenue.trailing_groups(period,groups)
        assert any(g['chartable'] and g['total']=={'QCOM':'44069000000','AMD':'41305000000'}[symbol] for g in trailing)


def test_borrowing_from_separate_current_noncurrent_sections():
    raw=balance().replace(b'us-gaap:LongTermDebtCurrent',b'us-gaap:DebtCurrent').replace(b'us-gaap:LongTermDebtNoncurrent',b'us-gaap:LongTermDebt')
    # Without proof of separate sections, do not reinterpret LongTermDebt.
    assert 'balance_sheet_borrowing' not in recovered(raw)
    rows=[('Assets','Assets','100'),('Short-term debt','DebtCurrent','5'),('Total current liabilities','LiabilitiesCurrent','10'),('Long-term debt','LongTermDebt','20'),('Liabilities','Liabilities','60'),('Equity','StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest','40')]
    instant=context('instant').replace('<xbrli:startDate>2024-10-01</xbrli:startDate><xbrli:endDate>2025-09-30</xbrli:endDate>','<xbrli:instant>2025-09-30</xbrli:instant>')
    raw=statement([(label,fact('instant',value,concept='us-gaap:'+tag,id=tag)) for label,tag,value in rows],instant)
    assert recovered(raw)['balance_sheet_borrowing']['value']=='25000000'
    reordered=statement([(label,fact('instant',value,concept='us-gaap:'+tag,id=tag)) for label,tag,value in [rows[0],rows[3],rows[1],rows[2],rows[4],rows[5]]],instant)
    assert 'balance_sheet_borrowing' not in recovered(reordered)


def test_liabilities_need_the_complete_section_and_equation():
    instant=context('instant').replace('<xbrli:startDate>2024-10-01</xbrli:startDate><xbrli:endDate>2025-09-30</xbrli:endDate>','<xbrli:instant>2025-09-30</xbrli:instant>')
    values=[('Assets','Assets','100'),('Current liabilities','LiabilitiesCurrent','10'),('Long-term debt','LongTermDebtNoncurrent','20'),('Other liabilities','OtherLiabilitiesNoncurrent','30'),("Stockholders’ equity:",None,None),('Equity','StockholdersEquity','40'),('Liabilities and equity','LiabilitiesAndStockholdersEquity','100')]
    raw=statement([(label,fact('instant',value,concept='us-gaap:'+tag,id=tag) if tag else '') for label,tag,value in values],instant)
    assert recovered(raw)['Liabilities']['value']=='60000000'
    for invalid in [raw.replace(b'>30<',b'>31<'),raw.replace(b'us-gaap:OtherLiabilitiesNoncurrent',b'custom:UnknownObligation'),raw.replace(b'<td>Other liabilities</td>',b'<td>Unrecognized cost</td>').replace(fact('instant','30',concept='us-gaap:OtherLiabilitiesNoncurrent',id='OtherLiabilitiesNoncurrent').encode(),b'30')]:
        assert 'Liabilities' not in recovered(invalid)
