"""General 20-F annual extraction, native ratios and immutable collection."""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import pytest
from thesis.config import OWNER
from thesis.db import transaction, one
from thesis.research.sec.normalize import normalize, filing_rows
from thesis.research.sec.performance import normalize_performance, present
from thesis.research.sec.service import add_company, refresh
from thesis.research.sec.amendments import Resolver
from test_sec_fundamentals import bundle, CIK, NOW


def foreign(currency='CNY', namespace='us-gaap', form='20-F'):
    data=bundle(annual=True, revenue=500, prior=400, income=100)
    data['submissions']['filings']['recent']['form']=[form]
    source=data['companyfacts']['facts'].pop('us-gaap')
    if namespace=='ifrs-full':
        source={'Revenue':source['RevenueFromContractWithCustomerExcludingAssessedTax'], 'ProfitLossFromOperatingActivities':source['OperatingIncomeLoss']}
    for concept in source.values():
        values=concept['units'].pop('USD')
        for row in values:row['form']=form
        concept['units'][currency]=values
    data['companyfacts']['facts'][namespace]=source
    return data


def parsed(data):
    return normalize(data['companyfacts'],data['submissions'],CIK,NOW)


@pytest.mark.parametrize('currency,namespace',[('USD','us-gaap'),('CNY','us-gaap'),('EUR','ifrs-full'),('JPY','ifrs-full')])
def test_foreign_annual_ratios_keep_one_explicit_currency_and_taxonomy(currency,namespace):
    data=foreign(currency,namespace);before=deepcopy(data);result=parsed(data)
    assert result['period_type']=='annual' and result['form']=='20-F'
    assert [Decimal(c['value']) for c in result['calculations']]==[Decimal(25),Decimal(20)]
    assert result['financial_basis']['currency']==currency and result['financial_basis']['namespace']==namespace
    assert all(f['unit']==currency and f['namespace']==namespace and f['form']=='20-F' for f in result['facts'])
    report=normalize_performance(data,CIK,NOW)['reports']
    assert report['quarter'] is None and report['annual']['form']=='20-F'
    assert report['annual']['financial_basis']==result['financial_basis']
    assert next(m for m in report['annual']['metrics'] if m['key']=='revenue_growth')['value']=='25.00'
    assert data==before


def test_current_only_usd_translation_does_not_replace_complete_native_pair():
    data=foreign();source=data['companyfacts']['facts']['us-gaap']
    for concept in source.values():concept['units']['USD']=[dict(concept['units']['CNY'][0],val='50')]
    result=parsed(data)
    assert result['financial_basis']['currency']=='CNY'
    assert result['calculations'][0]['value']=='25.00'
    # A reported USD current-year amount can supply the USD-only size card;
    # neither a prior USD amount nor a conversion is invented.
    report=normalize_performance(data,CIK,NOW)['reports']['annual']
    assert next(m for m in report['metrics'] if m['key']=='revenue')['value']=='50'
    assert all(f['unit']=='CNY' for f in next(m for m in report['metrics'] if m['key']=='revenue_growth')['inputs'])


def test_multiple_complete_currencies_or_taxonomies_are_withheld():
    for variant in ('currency','taxonomy'):
        data=foreign();source=data['companyfacts']['facts']['us-gaap']
        if variant=='currency':
            for concept in source.values():concept['units']['USD']=deepcopy(concept['units']['CNY'])
        else:
            extra=foreign('EUR','ifrs-full')['companyfacts']['facts']['ifrs-full']
            data['companyfacts']['facts']['ifrs-full']=extra
        result=parsed(data)
        assert result['financial_basis']['currency'] is None
        assert all(c['value'] is None and 'Multiple currencies or accounting bases' in c['reason'] for c in result['calculations'])


def test_conflict_does_not_switch_to_incomplete_translation_and_mixed_units_do_not_supply_growth():
    data=foreign();source=data['companyfacts']['facts']['us-gaap'];revenue=source['RevenueFromContractWithCustomerExcludingAssessedTax']['units']
    revenue['CNY'].append(dict(revenue['CNY'][0],val=501));revenue['USD']=[dict(revenue['CNY'][0],val=50)]
    result=parsed(data)
    assert result['financial_basis']['currency']=='CNY' and result['calculations'][0]['value'] is None
    assert 'Conflicting' in result['calculations'][0]['reason']
    data=foreign();revenue=data['companyfacts']['facts']['us-gaap']['RevenueFromContractWithCustomerExcludingAssessedTax']['units']
    revenue['USD']=[revenue['CNY'].pop()]
    assert parsed(data)['calculations'][0]['value'] is None


@pytest.mark.parametrize('value',['NaN','Infinity','1e101'])
def test_invalid_native_inputs_fail_closed(value):
    data=foreign();data['companyfacts']['facts']['us-gaap']['OperatingIncomeLoss']['units']['CNY'][0]['val']=value
    with pytest.raises(ValueError):parsed(data)


def test_foreign_6k_does_not_become_a_quarter_and_latest_amendment_does_not_borrow():
    original=foreign();amended=foreign(form='20-F/A')
    recent=original['submissions']['filings']['recent'];new=amended['submissions']['filings']['recent']
    for key in recent:
        recent[key]+=new[key]
    recent['accessionNumber'][1]='0000789019-25-000002'
    recent['acceptanceDateTime'][1]='2025-11-01T20:00:00Z';recent['filingDate'][1]='2025-11-01'
    # No usable amended facts. The original totals remain unavailable.
    result=normalize_performance(original,CIK,NOW)
    assert result['reports']['annual']['form']=='20-F/A'
    assert all(m['value'] is None for m in result['reports']['annual']['metrics'])
    resolver=Resolver(original,CIK,NOW,{})
    resolved,summary=resolver.resolve(filing_rows(original['submissions'],NOW)[-1],result['reports']['annual']['metrics'])
    assert summary['retained']==[] and not summary['needs_documents'] and all(m['value'] is None for m in resolved)
    only=foreign(form='6-K')
    with pytest.raises(ValueError,match='No supported'):parsed(only)


def test_unsupported_form_has_a_safe_actionable_failure_reason():
    from thesis.research.sec.client import failure_message
    from thesis.research.sec.normalize import UnsupportedFiling
    assert '10-K, 10-Q or 20-F' in failure_message(UnsupportedFiling('private text'))
    assert 'private' not in failure_message(UnsupportedFiling('private text'))


def test_foreign_reports_keep_annual_classification_in_shared_views_and_original_plans():
    from thesis.research.sec.financial_depth import normalize_depth
    from thesis.research.sec.financial_story import normalize_story
    from thesis.research.sec.income_flow import normalize_flow
    from thesis.research.sec.disclosures import revenue_history_plan
    data=foreign('USD')
    story=normalize_story(data,CIK,NOW)
    assert story['annual'][0]['form']=='20-F'
    assert next(m for m in story['annual'][0]['metrics'] if m['key']=='revenue')['value']=='500'
    assert next(m for m in normalize_depth(data,CIK,NOW)['trailing'] if m['key']=='revenue')['value']=='500'
    flow=normalize_flow(data,CIK,NOW)
    assert flow['periods'][0]['kind']=='annual' and flow['periods'][0]['form']=='20-F'
    assert revenue_history_plan(data['submissions'],CIK,NOW)[0]['form']=='20-F'


def test_normal_collection_saves_foreign_annual_and_preserves_permission_checks(owner):
    iid=add_company('MSFT')['instrument_id'];data=foreign()
    refresh(iid,fetcher=lambda cik:data)
    with transaction(owner) as c:
        result=present(c,iid)
        assert result['reports']['annual']['form']=='20-F' and result['reports']['quarter'] is None
        assert one(c,'SELECT last_error FROM sec_refresh_state WHERE instrument_id=%s',(iid,))['last_error'] is None
        assert one(c,"SELECT count(*) n FROM source_checks WHERE instrument_id=%s AND source_id='sec-companyfacts' AND outcome='success'",(iid,))['n']==1
        text=one(c,'SELECT v.body FROM document_versions v JOIN documents d ON d.id=v.document_id WHERE d.instrument_id=%s ORDER BY v.available_at DESC LIMIT 1',(iid,))['body']
        assert 'CNY 500' in text and 'USD 500' not in text
    with transaction(admin=True) as c:c.execute("UPDATE sources SET entitlement='fictional' WHERE id='sec-companyfacts'")
    with transaction(owner) as c:assert present(c,iid)['status']=='unavailable'
