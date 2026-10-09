"""General retained-fact recovery; no issuer lists or live requests."""
from copy import deepcopy
import hashlib
import pytest
from thesis.research.sec import financial_story, financial_depth, amendments, income_flow
from thesis.research.sec.normalize import REVENUE
from thesis.research.sec.disclosure_text import parse
from test_financial_story import fixture, keyed
from test_financial_depth import trailing_bundle
from test_sec_fundamentals import CIK, NOW
from test_reviewed_annual import amended, document, resolved


def story(data):return financial_story.normalize_story(data,CIK,NOW)


def test_common_tag_requires_exact_original_inputs_without_aliasing():
    data=trailing_bundle();facts=data['companyfacts']['facts']['us-gaap']
    original=facts[REVENUE[0]]['units']['USD']
    facts['Revenues']={'units':{'USD':deepcopy(original)}}
    facts[REVENUE[0]]['units']['USD']=[v for v in original if v['form']=='10-K']
    revenue=keyed(story(data)['trailing'][-1])['revenue']
    assert revenue['value']=='550'
    assert {f['concept'] for f in revenue['inputs']}=={'Revenues'}
    facts['Revenues']['units']['USD']=[v for v in facts['Revenues']['units']['USD'] if v['form']!='10-K']
    assert keyed(story(data)['trailing'][-1])['revenue']['value'] is None


def productive(data):
    facts=data['companyfacts']['facts']['us-gaap']
    facts['PaymentsToAcquireProductiveAssets']=facts.pop('PaymentsToAcquirePropertyPlantAndEquipment')
    return data


@pytest.mark.parametrize('kind',['annual','trailing'])
def test_productive_asset_cash_spending_is_labelled_and_preserves_its_definition(kind):
    data=productive(fixture() if kind=='annual' else trailing_bundle())
    metrics=keyed(story(data)[kind][-1])
    assert metrics['free_cash_flow']['value']==('27.0000000000000000001' if kind=='annual' else '70')
    assert metrics['capital_spending']['spending_basis']=='productive_assets'
    assert 'software' in metrics['free_cash_flow']['explanation']
    assert {f['concept'] for f in metrics['capital_spending']['inputs']}=={'PaymentsToAcquireProductiveAssets'}


@pytest.mark.parametrize('case',['preferred','zero','conflict','currency','prior_missing','negative'])
def test_broader_capex_does_not_conceal_preferred_or_invalid_inputs(case):
    data=trailing_bundle();facts=data['companyfacts']['facts']['us-gaap'];preferred=facts['PaymentsToAcquirePropertyPlantAndEquipment']['units']['USD']
    facts['PaymentsToAcquireProductiveAssets']={'units':{'USD':[dict(v,val=1) for v in preferred]}}
    if case=='zero':
        for v in preferred:v['val']=0
    elif case=='conflict':preferred.append(dict(preferred[-1],val=11))
    elif case=='currency':facts['PaymentsToAcquirePropertyPlantAndEquipment']['units']={'EUR':preferred}
    elif case=='prior_missing':preferred.pop()
    elif case=='negative':
        for v in preferred:v['val']=-1
    metrics=keyed(story(data)['trailing'][-1])
    if case in ('preferred','zero'):
        assert metrics['capital_spending']['value']==('40' if case=='preferred' else '0')
        assert metrics['free_cash_flow']['value']==('70' if case=='preferred' else '110')
    else:assert metrics['free_cash_flow']['value'] is None
    assert metrics['capital_spending']['spending_basis']=='property_plant_equipment'


@pytest.mark.parametrize('key,original,alternate',[
    ('receivables','AccountsReceivableNetCurrent','AccountsAndOtherReceivablesNetCurrent'),
    ('intangibles','FiniteLivedIntangibleAssetsNet','IntangibleAssetsNetExcludingGoodwill'),
    ('property','PropertyPlantAndEquipmentNet','PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization'),
    ('payables','AccountsPayableCurrent','AccountsPayableTradeCurrent'),
])
def test_balance_categories_are_explicit_and_never_mask_conflicting_primary(key,original,alternate):
    data=fixture();facts=data['companyfacts']['facts']['us-gaap'];source=facts.pop(original)
    facts[alternate]=deepcopy(source)
    row=keyed(story(data)['balances'][-1])[key]
    assert row['value'] is not None and row['inputs'][0]['concept']==alternate
    assert 'scope' in row['explanation']
    facts[original]=source;v=source['units']['USD'][0];source['units']['USD'].append(dict(v,val=999))
    assert keyed(story(data)['balances'][-1])[key]['value'] is None


def test_liabilities_sum_needs_both_explicit_components_and_keeps_conflicts():
    data=fixture();facts=data['companyfacts']['facts']['us-gaap'];base=facts.pop('Liabilities')['units']['USD'][0]
    facts['LiabilitiesNoncurrent']={'units':{'USD':[dict(base,val=60)]}}
    row=keyed(story(data)['balances'][-1])['liabilities']
    assert row['value']=='90' and row['calculated'] and len(row['inputs'])==2
    del facts['LiabilitiesNoncurrent']
    assert keyed(story(data)['balances'][-1])['liabilities']['value'] is None


@pytest.mark.parametrize('case',['valid','missing_lease','negative','exceeds','conflict','foreign_direct'])
def test_debt_can_remove_explicit_finance_leases_but_not_assume_them(case):
    data=fixture();facts=data['companyfacts']['facts']['us-gaap'];base=facts.pop('DebtLongtermAndShorttermCombinedAmount')['units']['USD'][0]
    facts['DebtAndCapitalLeaseObligations']={'units':{'USD':[dict(base,val=80)]}}
    facts['FinanceLeaseLiability']={'units':{'USD':[dict(base,val=12)]}}
    if case=='missing_lease':del facts['FinanceLeaseLiability']
    elif case=='negative':facts['FinanceLeaseLiability']['units']['USD'][0]['val']=-1
    elif case=='exceeds':facts['FinanceLeaseLiability']['units']['USD'][0]['val']=81
    elif case=='conflict':facts['DebtAndCapitalLeaseObligations']['units']['USD'].append(dict(base,val=90))
    elif case=='foreign_direct':facts['DebtLongtermAndShorttermCombinedAmount']={'units':{'EUR':[base]}}
    row=keyed(story(data)['balances'][-1])['debt']
    assert row['value']==('68' if case=='valid' else None)
    if case=='valid':assert row['calculated'] and len(row['inputs'])==2


def test_existing_complete_debt_components_keep_their_original_basis():
    data=trailing_bundle();facts=data['companyfacts']['facts']['us-gaap'];base=facts['LongTermDebt']['units']['USD'][0]
    facts['DebtAndCapitalLeaseObligations']={'units':{'USD':[dict(base,val=90)]}}
    facts['FinanceLeaseLiability']={'units':{'USD':[dict(base,val=30)]}}
    debt=financial_depth.normalize_depth(data,CIK,NOW)['debt']
    assert debt['value']=='37'
    assert {f['concept'] for f in debt['inputs']}=={'LongTermDebt','ShortTermBorrowings'}


SCOPE="The Company is filing this amendment solely for the purpose of correcting numerical disclosures in the Management’s Discussion and Analysis of Financial Condition and Results of Operations (MD&A). Except as described above, this Amendment does not amend, update or change any other items or disclosures contained in the Original Filing."


def amended_with_net(cik=CIK):
    b=amended(cik=cik);facts=b['companyfacts']['facts']['us-gaap']
    facts['NetIncomeLoss']=deepcopy(facts['OperatingIncomeLoss'])
    return b


def scope_document(b,note=SCOPE,items='<h2>Item 7. Management’s Discussion and Analysis</h2><p>Corrected narrative.</p>'):
    d=document(b,note)
    raw=d['raw_html'].replace(b'<h2>Part III</h2>',('<h2>Part II</h2>'+items).encode())
    d['raw_html']=raw;d['content_hash']=hashlib.sha256(raw).hexdigest()
    d['data']=parse(raw,form=d['form'],cik=int(b['companyfacts']['cik']));d['data']['report_period_end']='2025-09-30'
    return d


@pytest.mark.parametrize('cik',[CIK,123456])
def test_explicit_mda_scope_restores_statements_for_any_issuer(cik):
    b=amended_with_net(cik=cik);d=scope_document(b);metrics,summary,resolver=resolved(b,d)
    assert metrics['net_income']['value'] is not None
    assert metrics['operating_cash']['value'] is not None
    support=metrics['net_income']['filing_resolution']['amendments'][0]['support'][0]
    assert support['kind']=='unchanged_statement_section'
    assert d['data']['body'][support['start']:support['end']]==support['quote']
    result=income_flow.normalize_flow(b,cik,NOW,resolver)
    annual=next(p for p in result['periods'] if p['kind']=='annual')
    assert next(m for m in annual['metrics'] if m['key']=='net_result')['value'] is not None


@pytest.mark.parametrize('case',['no_sole_purpose','no_unchanged','restatement','financial_statements','item8','no_item7','quarter','foreign_doc','conflicting_facts'])
def test_mda_scope_requires_complete_explicit_evidence(case):
    b=amended_with_net();note=SCOPE
    if case=='no_sole_purpose':note=note.replace('solely ','')
    elif case=='no_unchanged':note=note.split('Except')[0]
    elif case=='restatement':note+=' A material error requires restatement.'
    elif case=='financial_statements':note+=' Financial statements also change.'
    items='<h2>Item 7. Management’s Discussion and Analysis</h2>'
    if case=='item8':items+='<h2>Item 8. Financial Statements</h2>'
    elif case=='no_item7':items=''
    d=scope_document(b,note,items)
    if case=='quarter':d['form']='10-Q/A'
    elif case=='foreign_doc':d['url']=d['url'].replace('789019','999999')
    elif case=='conflicting_facts':
        from test_reviewed_annual import add_corrected_facts
        add_corrected_facts(b)
        # A contradiction elsewhere also invalidates the blanket scope proof.
        b['companyfacts']['facts']['us-gaap']['NetIncomeLoss']['units']['USD']=[v for v in b['companyfacts']['facts']['us-gaap']['NetIncomeLoss']['units']['USD'] if v['form']!='10-K/A']
    metrics,_,_=resolved(b,d)
    assert metrics['net_income']['value'] is None
