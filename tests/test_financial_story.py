"""Read-only histories, exact arithmetic and scope over authored SEC facts."""
from copy import deepcopy
from decimal import Decimal
import pytest
from thesis.research.sec import financial_story as story
from thesis.research.sec.normalize import REVENUE
from test_sec_fundamentals import CIK, NOW, bundle, apply
from test_financial_depth import trailing_bundle
from thesis.db import transaction, one


def fixture():
    data = bundle(annual=True, revenue=100, income=25)
    facts = data['companyfacts']['facts']['us-gaap']
    base = facts['OperatingIncomeLoss']['units']['USD'][0]
    for tag, value in [('ProfitLoss', 20), ('NetIncomeLoss', 19),
                       ('NetCashProvidedByUsedInOperatingActivities', '31.1234567890123456789'),
                       ('PaymentsToAcquirePropertyPlantAndEquipment', '4.1234567890123456788'),
                       ('InterestExpenseNonOperating', 5)]:
        facts[tag] = {'units': {'USD': [dict(base, val=value)]}}
    for tag, value in [('Assets', 200), ('Liabilities', 90), ('AssetsCurrent', 60),
                       ('LiabilitiesCurrent', 30), ('CashAndCashEquivalentsAtCarryingValue', 25),
                       ('DebtLongtermAndShorttermCombinedAmount', 68), ('AccountsReceivableNetCurrent', 15),
                       ('InventoryNet', 5), ('PropertyPlantAndEquipmentNet', 10),
                       ('Goodwill', 50), ('FiniteLivedIntangibleAssetsNet', 40), ('AccountsPayableCurrent', 8)]:
        row = dict(base, val=value); row.pop('start')
        facts[tag] = {'units': {'USD': [row]}}
    return data


def normalized(data=None): return story.normalize_story(data or fixture(), CIK, NOW)
def keyed(period): return {row['key']: row for row in period['metrics']}


def test_exact_cash_equity_and_remainders_preserve_inputs():
    result = normalized(); income = keyed(result['annual'][-1]); balance = keyed(result['balances'][-1])
    assert income['free_cash_flow']['value'] == '27.0000000000000000001'
    assert income['net_income']['value'] == '20' and 'non-controlling' in income['net_income']['label']
    assert income['net_margin']['value'] == '20' and income['interest_coverage']['value'] == '5'
    assert balance['equity']['value'] == '110' and balance['net_debt']['value'] == '43'
    assert balance['working_capital']['value'] == '30'
    assert balance['noncurrent_assets']['value'] == '140' and balance['noncurrent_liabilities']['value'] == '60'
    assert balance['other_assets']['value'] == '55' and balance['other_liabilities']['value'] == '14'
    assert len(balance['equity']['inputs']) == 2 and len(income['free_cash_flow']['inputs']) == 2
    assert all(f['filing_url'].startswith('https://www.sec.gov/Archives/') for row in balance.values() for f in row['inputs'])


def test_trailing_history_reuses_exact_three_filing_bridge():
    result = normalized(trailing_bundle()); income = keyed(result['trailing'][-1]); balance = keyed(result['balances'][-1])
    assert income['revenue']['value'] == '550' and income['revenue']['start'] == '2025-07-01'
    assert income['free_cash_flow']['value'] == '70' and len(income['revenue']['inputs']) == 3
    assert income['operating_income']['value'] is None
    assert balance['debt']['value'] == '37'
    assert keyed(result['balances'][0])['debt']['value'] is None  # newer borrowing never moves backwards


@pytest.mark.parametrize('case', ['period', 'unit', 'accession', 'conflict', 'duration'])
def test_incompatible_current_assets_stay_unknown(case):
    data = fixture(); facts = data['companyfacts']['facts']['us-gaap']; row = facts['AssetsCurrent']['units']['USD'][0]
    if case == 'period': row['end'] = '2024-09-30'
    if case == 'unit': facts['AssetsCurrent']['units'] = {'EUR': [row]}
    if case == 'accession': row['accn'] = '0000789019-25-000999'
    if case == 'conflict': facts['AssetsCurrent']['units']['USD'].append(dict(row, val=61))
    if case == 'duration': row['start'] = '2024-10-01'
    metrics = keyed(normalized(data)['balances'][-1])
    assert metrics['current_assets']['value'] is None and metrics['working_capital']['value'] is None


def test_direct_noncurrent_conflict_cannot_be_masked_by_difference():
    data = fixture(); facts = data['companyfacts']['facts']['us-gaap']; row = facts['Assets']['units']['USD'][0]
    facts['AssetsNoncurrent'] = {'units': {'USD': [dict(row, val=140), dict(row, val=141)]}}
    assert keyed(normalized(data)['balances'][-1])['noncurrent_assets']['value'] is None


def test_parent_only_result_is_labelled_and_conflicting_consolidated_is_withheld():
    data = fixture(); facts = data['companyfacts']['facts']['us-gaap']; del facts['ProfitLoss']
    income = keyed(normalized(data)['annual'][-1])
    assert income['net_income']['value'] == '19' and 'parent' in income['net_income']['label']
    base = facts['NetIncomeLoss']['units']['USD'][0]
    facts['ProfitLoss'] = {'units': {'USD': [dict(base, val=20), dict(base, val=21)]}}
    assert keyed(normalized(data)['annual'][-1])['net_income']['value'] is None


@pytest.mark.parametrize('value', [0, -20])
def test_zero_and_losses_are_kept_but_ratio_requires_positive_denominator(value):
    data = fixture(); facts = data['companyfacts']['facts']['us-gaap']
    facts['ProfitLoss']['units']['USD'][0]['val'] = value
    facts['Liabilities']['units']['USD'][0]['val'] = 200 if value == 0 else 220
    result = normalized(data); income = keyed(result['annual'][-1]); balance = keyed(result['balances'][-1])
    assert income['net_margin']['value'] == str(value)
    assert balance['equity']['value'] == str(value)
    assert balance['debt_equity']['value'] is None and 'positive' in balance['debt_equity']['reason']


def test_missing_categories_are_unclassified_not_zero_and_overlap_is_withheld():
    data = fixture(); facts = data['companyfacts']['facts']['us-gaap']; del facts['Goodwill']
    rows = keyed(normalized(data)['balances'][-1])
    assert rows['goodwill']['value'] is None and rows['other_assets']['value'] == '105'
    facts['InventoryNet']['units']['USD'][0]['val'] = 500
    assert keyed(normalized(data)['balances'][-1])['other_assets']['value'] is None


def test_cash_dates_and_negative_capital_spending_do_not_form_fcf():
    data = fixture(); facts = data['companyfacts']['facts']['us-gaap']
    facts['NetCashProvidedByUsedInOperatingActivities']['units']['USD'][0]['start'] = '2024-10-02'
    assert keyed(normalized(data)['annual'][-1])['free_cash_flow']['value'] is None
    data = fixture(); data['companyfacts']['facts']['us-gaap']['PaymentsToAcquirePropertyPlantAndEquipment']['units']['USD'][0]['val'] = -1
    assert keyed(normalized(data)['annual'][-1])['free_cash_flow']['value'] is None


def test_latest_amendment_keeps_missing_history_instead_of_backfilling():
    data = fixture(); recent = data['submissions']['filings']['recent']
    for key, value in dict(accessionNumber='0000789019-25-000009', form='10-K/A', filingDate='2025-11-03', reportDate='2025-09-30', acceptanceDateTime='2025-11-03T20:00:00Z', primaryDocument='amended.htm').items(): recent[key].append(value)
    result = normalized(data)
    assert len(result['annual']) == 1 and result['annual'][0]['form'] == '10-K/A'
    assert keyed(result['annual'][0])['revenue']['value'] is None
    assert keyed(result['balances'][0])['assets']['value'] is None


def test_history_deduplicates_and_bounds_in_date_order_without_mutating_source():
    data = fixture(); recent = data['submissions']['filings']['recent']
    for year in range(1970, 2025):
        for key, value in dict(accessionNumber=f'0000789019-{str(year)[2:]}-000001', form='10-K', filingDate=f'{year}-10-30', reportDate=f'{year}-09-30', acceptanceDateTime=f'{year}-10-30T20:00:00Z', primaryDocument=f'year-{year}.htm').items(): recent[key].append(value)
    original = deepcopy(data); result = normalized(data)
    assert len(result['annual']) == 12 and len(result['balances']) == len(result['trailing']) == 40
    assert result['annual'][-1]['end'] == '2025-09-30' and data == original


def test_wrong_issuer_and_bad_metadata_are_rejected():
    data = fixture(); data['companyfacts']['cik'] = 320193
    with pytest.raises(ValueError, match='another company'): normalized(data)


def test_present_is_read_only_and_withdrawal_hides_all_history(owner):
    from thesis.research.sec.service import add_company
    iid = add_company('MSFT')['instrument_id']; apply(iid, fixture())
    with transaction(admin=True, consistent=True) as conn:
        before = one(conn, 'SELECT md5(string_agg(to_jsonb(p)::text,\'\' ORDER BY p.id)) fingerprint FROM source_payloads p')
        result = story.present(conn, iid)
        assert result['status'] == 'available' and result['payload_id']
        assert before == one(conn, 'SELECT md5(string_agg(to_jsonb(p)::text,\'\' ORDER BY p.id)) fingerprint FROM source_payloads p')
    with transaction(admin=True) as conn: conn.execute("UPDATE sources SET entitlement='fictional' WHERE id='sec-companyfacts'")
    with transaction(consistent=True) as conn:
        result = story.present(conn, iid)
        assert result['status'] == 'unavailable' and 'annual' not in result and 'balances' not in result
