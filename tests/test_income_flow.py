"""Independent arithmetic and scope checks for the income-flow projection."""
from copy import deepcopy
from decimal import Decimal
from datetime import datetime, timezone
import pytest
from thesis.research.sec import income_flow
from thesis.research.sec.normalize import REVENUE
from test_sec_fundamentals import bundle, CIK, NOW
from test_financial_depth import trailing_bundle


def fixture():
    data = bundle(annual=True, revenue=100, income=25)
    facts = data['companyfacts']['facts']['us-gaap']
    base = facts['OperatingIncomeLoss']['units']['USD'][0]
    for tag, value in [('CostOfRevenue', 40), ('GrossProfit', 60), ('OperatingExpenses', 35),
                       ('ProfitLoss', 20), ('NetIncomeLoss', 19), ('ResearchAndDevelopmentExpense', 10),
                       ('SellingGeneralAndAdministrativeExpense', 20)]:
        facts[tag] = {'units': {'USD': [dict(base, val=value)]}}
    return data


def period(data=None):
    return income_flow.normalize_flow(data or fixture(), CIK, NOW)['periods'][0]


def keyed(result): return {row['key']: row for row in result['metrics']}


def test_balanced_flow_and_expense_remainder_have_exact_evidence():
    result = period(); rows = keyed(result)
    assert result['chartable'] and len(result['links']) == 6
    assert rows['net_result']['value'] == '20'
    assert rows['net_result']['label'] == 'Net result including non-controlling interests'
    assert rows['net_items']['value'] == '5' and rows['net_items']['calculated']
    assert result['expense_parts'][-1]['value'] == '5'
    for node in result['nodes']:
        incoming = [Decimal(l['value']) for l in result['links'] if l['target'] == node['key']]
        outgoing = [Decimal(l['value']) for l in result['links'] if l['source'] == node['key']]
        if incoming: assert sum(incoming) == Decimal(node['value'])
        if outgoing: assert sum(outgoing) == Decimal(node['value'])
    assert all(f['filing_url'].startswith('https://www.sec.gov/Archives/') for row in result['nodes'] for f in row['inputs'])


@pytest.mark.parametrize('tag', ['GrossProfit', 'CostOfRevenue', 'OperatingExpenses'])
def test_missing_total_is_explicit_difference_but_conflict_is_not_hidden(tag):
    data = fixture(); facts = data['companyfacts']['facts']['us-gaap']; original = facts.pop(tag)
    result = period(data)
    assert result['chartable']
    key = {'GrossProfit': 'gross', 'CostOfRevenue': 'cost', 'OperatingExpenses': 'expenses'}[tag]
    assert keyed(result)[key]['calculated'] and len(keyed(result)[key]['inputs']) == 2
    facts[tag] = original
    facts[tag]['units']['USD'].append(dict(original['units']['USD'][0], val=999))
    assert not period(data)['chartable'] and not period(data)['nodes']


@pytest.mark.parametrize('case', ['period', 'unit', 'accession', 'conflict', 'balance', 'negative', 'zero_revenue'])
def test_incompatible_or_unbalanced_figures_do_not_create_flows(case):
    data = fixture(); facts = data['companyfacts']['facts']['us-gaap']
    row = facts['OperatingIncomeLoss']['units']['USD'][0]
    if case == 'period': row['start'] = '2024-10-02'
    if case == 'unit': facts['OperatingIncomeLoss']['units'] = {'EUR': [row]}
    if case == 'accession': row['accn'] = '0000789019-25-000999'
    if case == 'conflict': facts['OperatingIncomeLoss']['units']['USD'].append(dict(row, val=26))
    if case == 'balance': row['val'] = 26
    if case == 'negative': row['val'] = -1
    if case == 'zero_revenue': facts[REVENUE[0]]['units']['USD'][0]['val'] = 0
    result = period(data)
    assert not result['chartable'] and result['reason'] and result['nodes'] == []


def test_parent_and_consolidated_results_are_not_equivalent():
    data = fixture(); facts = data['companyfacts']['facts']['us-gaap']; del facts['ProfitLoss']
    result = period(data); rows = keyed(result)
    assert rows['net_result']['value'] == '19' and 'parent' in rows['net_result']['label']
    assert rows['net_items']['value'] == '6'
    facts['ProfitLoss'] = {'units': {'USD': [dict(facts['NetIncomeLoss']['units']['USD'][0], val=20), dict(facts['NetIncomeLoss']['units']['USD'][0], val=21)]}}
    assert keyed(period(data))['net_result']['value'] is None


@pytest.mark.parametrize('value', [-2, 26])
def test_net_loss_or_gain_is_preserved_without_positive_outflow(value):
    data = fixture(); data['companyfacts']['facts']['us-gaap']['ProfitLoss']['units']['USD'][0]['val'] = value
    result = period(data)
    assert result['chartable'] and len(result['links']) == 4 and result['notes']
    assert keyed(result)['net_result']['value'] == str(value)


def test_explicit_zero_and_decimal_widths_remain_exact():
    data = fixture(); facts = data['companyfacts']['facts']['us-gaap']
    facts['ProfitLoss']['units']['USD'][0]['val'] = 0
    facts['ResearchAndDevelopmentExpense']['units']['USD'][0]['val'] = 0
    result = period(data)
    assert result['chartable'] and keyed(result)['net_result']['value'] == '0'
    assert result['expense_parts'][0]['value'] == '0'
    for tag in [REVENUE[0], 'CostOfRevenue', 'GrossProfit', 'OperatingExpenses', 'OperatingIncomeLoss', 'ProfitLoss']:
        row = facts[tag]['units']['USD'][0]; row['val'] = str(Decimal(row['val']) / 10)
    assert period(data)['chartable']


def test_partial_expense_components_are_not_a_complete_breakdown():
    data = fixture(); facts = data['companyfacts']['facts']['us-gaap']
    del facts['ResearchAndDevelopmentExpense']
    assert period(data)['expense_parts'] == []
    data = fixture(); data['companyfacts']['facts']['us-gaap']['ResearchAndDevelopmentExpense']['units']['USD'][0]['val'] = 99
    assert period(data)['expense_parts'] == []


def test_trailing_bridge_uses_exact_periods_and_vintages():
    data = trailing_bundle(); facts = data['companyfacts']['facts']['us-gaap']
    # Revenue bridge is 500 + 170 - 120 = 550; this complete authored statement
    # gives cost 220, gross 330, operating costs 165 and operating profit 165.
    revenue = facts[REVENUE[0]]['units']['USD']
    for tag, fraction in [('CostOfRevenue', '.4'), ('GrossProfit', '.6'), ('OperatingExpenses', '.3'), ('OperatingIncomeLoss', '.3'), ('ProfitLoss', '.2')]:
        facts[tag] = {'units': {'USD': [dict(row, val=str(Decimal(row['val']) * Decimal(fraction))) for row in revenue]}}
    result = period(data)
    assert result['kind'] == 'trailing' and result['chartable']
    assert result['start'] == '2025-07-01' and result['end'] == '2026-06-30'
    assert keyed(result)['gross']['value'] == '330' and len(keyed(result)['gross']['inputs']) == 3
    facts['GrossProfit']['units']['USD'][-1]['start'] = '2024-10-03'
    assert not period(data)['chartable']


def test_amendment_gap_and_wrong_issuer_are_not_filled_from_old_report():
    data = fixture(); recent = data['submissions']['filings']['recent']
    for key, values in list(recent.items()): values.append(values[0])
    recent['form'][-1] = '10-K/A'; recent['accessionNumber'][-1] = '0000789019-25-000002'
    recent['acceptanceDateTime'][-1] = '2025-11-01T20:00:00Z'; recent['filingDate'][-1] = '2025-11-01'
    result = period(data)
    assert result['form'] == '10-K/A' and not result['chartable']
    with pytest.raises(ValueError, match='another company'): income_flow.normalize_flow(data, 1, NOW)


def test_source_withdrawal_hides_read_only_projection(owner):
    from thesis.db import transaction
    from thesis.research.sec.service import add_company, commit_bundle
    from thesis import service
    iid = add_company('MSFT')['instrument_id']
    with transaction(source=True) as conn: commit_bundle(conn, iid, fixture(), datetime.now(timezone.utc))
    assert service.state(owner, iid)['income_flow']['periods'][0]['chartable']
    with transaction(admin=True) as conn: conn.execute("UPDATE sources SET entitlement='fictional' WHERE id='sec-companyfacts'")
    try:
        result = service.state(owner, iid)['income_flow']
        assert result['status'] == 'unavailable' and result['periods'] == []
    finally:
        with transaction(admin=True) as conn: conn.execute("UPDATE sources SET entitlement='sec-public' WHERE id='sec-companyfacts'")
