"""Authored public tables: range meaning, access and shared-page acquisition."""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import os
import psycopg
import pytest
from thesis.db import transaction, one
from thesis.research import analyst_targets as targets, public_forecasts as forecasts
from thesis.research.sec.service import add_company
from test_analyst_targets import page as target_page


def page():
    table = '''<h2>Financial Forecast</h2><table>
    <tr><th>Fiscal Year</th><th>FY 2025</th><th>FY 2026</th><th>FY 2027</th></tr>
    <tr><td>Period Ending</td><td>Sep 30, 2025</td><td>Sep 30, 2026</td><td>Sep 30, 2027</td></tr>
    <tr><td>Revenue</td><td>90.0B</td><td>105.97B</td><td>Upgrade</td></tr>
    <tr><td>EPS</td><td>1.0</td><td>-1.11</td><td>Upgrade</td></tr>
    <tr><td>No. Analysts</td><td>-</td><td>40</td><td>Upgrade</td></tr></table>
    EPS and Forward PE are based on non-GAAP adjusted numbers.
    <h2>Revenue Forecast</h2><table><tr><th>Revenue</th><th>2026</th><th>2027</th></tr>
    <tr><td>High</td><td>106.7B</td><td>Pro</td></tr><tr><td>Avg</td><td>106.0B</td><td>Pro</td></tr>
    <tr><td>Low</td><td>105.8B</td><td>Pro</td></tr></table>
    <h2>EPS Forecast</h2><table><tr><th>EPS</th><th>2026</th><th>2027</th></tr>
    <tr><td>High</td><td>0</td><td>Pro</td></tr><tr><td>Avg</td><td>-1.11</td><td>Pro</td></tr>
    <tr><td>Low</td><td>-2</td><td>Pro</td></tr></table>
    Data Sources: S&amp;P Global Market Intelligence and TipRanks Last updated: Oct 2, 2026
    Price targets, consensus ratings and financial forecasts are provided by S&amp;P Global Market Intelligence.
    '''
    return target_page().replace('</body>', table+'</body>')


def setup():
    with transaction(admin=True) as c:
        c.execute("INSERT INTO sources VALUES(%s,'Authored forecast fixture','local-stockanalysis-forecasts')", (forecasts.SOURCE,))
        c.execute("INSERT INTO sources VALUES(%s,'Authored target fixture','local-stockanalysis-targets')", (targets.SOURCE,))
    return add_company('MSFT')['instrument_id']


def test_visible_ranges_keep_precision_definitions_and_restricted_years():
    result = forecasts.normalized(page(), 'MSFT')
    f = result['forecasts'][0]
    assert f['period_end'] == '2026-09-30' and f['currency'] is None
    assert result['restricted_years'] == ['2027']
    assert f['metrics'][0]['average'] == '105970000000'
    assert f['metrics'][0]['range_average'] == '106000000000'
    assert f['metrics'][1]['low'] == '-2'
    assert f['metrics'][1]['basis'] == 'non-GAAP adjusted'
    assert f['displayed_analyst_count'] == 40 and f['metrics'][0]['analysts'] is None
    assert result['provider_as_of'] is None and result['page_updated_on'] == '2026-10-02'


@pytest.mark.parametrize('old,new', [
    ('(MSFT)', '(AAPL)'), ('NASDAQ: MSFT', 'NASDAQ: AAPL'),
    ('non-GAAP adjusted numbers', 'reported numbers'),
    ('financial forecasts are provided by S&amp;P Global', 'financial forecasts are provided by Unknown'),
    ('105.97B', '104.0B'), ('106.0B', '106.5B'), ('105.8B', '107.0B'),
    ('<th>2026</th>', '<th>2025</th>'), ('<td>40</td>', '<td>40</td><td>50</td>'),
    ('Sep 30, 2026', 'not a date'), ('Oct 2, 2026', 'Oct 2, 2099')
])
def test_unsupported_or_conflicting_source_is_not_published(old, new):
    with pytest.raises(ValueError): forecasts.normalized(page().replace(old,new), 'MSFT')


@pytest.mark.parametrize('wrapper', ['<script>{}</script>', '<template>{}</template>', '<div hidden>{}</div>', '<div style="display: none">{}</div>'])
def test_hidden_content_cannot_supply_public_tables(wrapper):
    with pytest.raises(ValueError): forecasts.normalized(wrapper.format(page()), 'MSFT')


def test_one_page_populates_both_datasets_and_shared_cooldown(owner):
    iid=setup(); calls=[]
    targets.refresh(iid, lambda _: (calls.append('fetch'), page())[1], purpose='financials')
    with transaction() as c:
        assert targets.current(c,iid)['snapshot']['data']['targets']['mean']=='125.5'
        result=forecasts.current(c,iid)
        assert result['snapshot']['data']['forecasts'][0]['fiscal_year']==2026
        assert result['next_check_at']>datetime.now(timezone.utc)
    for purpose in ('targets','financials'):
        with pytest.raises(ValueError,match='24 hours'):
            targets.refresh(iid,lambda _:pytest.fail('Duplicate network'),purpose=purpose)
    assert calls==['fetch']
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with transaction() as c:c.execute('SELECT html FROM public_financial_forecasts')
    with pytest.raises(psycopg.errors.RaiseException,match='immutable'):
        with transaction(admin=True) as c:c.execute('UPDATE public_financial_forecasts SET error=error')


def test_parser_failure_retains_older_forecast_and_target_success(owner):
    iid=setup(); targets.refresh(iid,lambda _:page())
    with transaction() as c: before=forecasts.current(c,iid)['snapshot']['id']
    with transaction(admin=True) as c:c.execute("UPDATE analyst_target_state SET last_attempt_at=now()-interval '25 hours'")
    targets.refresh(iid,lambda _:target_page())
    with transaction() as c:
        result=forecasts.current(c,iid)
        assert result['snapshot']['id']==before and result['error']
        assert one(c,'SELECT count(*) n FROM public_financial_forecasts')['n']==2
        assert one(c,'SELECT count(*) n FROM analyst_target_snapshots')['n']==2


def test_financial_success_does_not_depend_on_price_target_table(owner):
    iid=setup()
    targets.refresh(iid,lambda _:page().replace('Stock Price Forecast','Missing price targets'),purpose='financials')
    with transaction() as c:
        assert forecasts.current(c,iid)['snapshot']
        assert forecasts.current(c,iid)['error'] is None
        assert targets.current(c,iid)['snapshot'] is None
        assert targets.current(c,iid)['refresh']['error']


def test_financial_failure_does_not_misreport_successful_targets(owner):
    iid=setup()
    with pytest.raises(ValueError,match='financial forecasts'):
        targets.refresh(iid,lambda _:target_page(),purpose='financials')
    with transaction() as c:
        assert targets.current(c,iid)['snapshot']
        assert targets.current(c,iid)['refresh']['error'] is None
        assert forecasts.current(c,iid)['error']


@pytest.mark.parametrize('change',['expired','replaced','withdrawn'])
def test_financial_results_fenced_after_fetch(owner,change):
    iid=setup()
    def fetch(_):
        with transaction(admin=True) as c:
            if change=='expired':c.execute("UPDATE analyst_target_state SET lease_until=now()-interval '1 second'")
            elif change=='replaced':c.execute('UPDATE analyst_target_state SET attempt_id=%s',(uuid4(),))
            else:c.execute("UPDATE sources SET entitlement='fictional' WHERE id=%s",(forecasts.SOURCE,))
        return page()
    with pytest.raises(ValueError):targets.refresh(iid,fetch,purpose='financials')
    with transaction() as c:assert one(c,'SELECT count(*) n FROM public_financial_forecasts')['n']==0


def test_permission_withholds_history_and_cached_data(owner):
    iid=setup();targets.refresh(iid,lambda _:page())
    with transaction(admin=True) as c:c.execute("UPDATE sources SET entitlement='fictional' WHERE id=%s",(forecasts.SOURCE,))
    with transaction() as c:
        result=forecasts.current(c,iid)
        assert not result['available'] and result['snapshot'] is None and result['history']==[]
    with pytest.raises(ValueError):targets.refresh(iid,lambda _:pytest.fail('Withdrawn source'),purpose='financials')


@pytest.mark.parametrize('symbol',['aapl','amzn','googl','meta','msft','nvda'])
def test_retained_pages_remain_historical_observations(symbol):
    folder=os.environ.get('THESIS_TARGET_CORPUS')
    if not folder: pytest.skip('Explicit retained source corpus not selected')
    result=forecasts.normalized((Path(folder)/(symbol+'.html')).read_text(),symbol.upper())
    assert len(result['forecasts'])==1 and result['forecasts'][0]['currency'] is None
