"""Authored outlook/date controls; no provider or model calls."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

import pytest
from thesis.db import transaction, one
from thesis.research.sec import guidance, disclosures
from thesis.research.sec.disclosure_text import parse
from thesis.research.sec.performance import normalize_performance
from thesis.research.sec.service import add_company, commit_bundle
from test_sec_fundamentals import bundle, CIK, NOW

ACCEPTED = datetime(2025, 6, 30, 20, tzinfo=timezone.utc)
AVAILABLE = datetime(2025, 7, 1, tzinfo=timezone.utc)


def release_html(revenue='Fourth quarter GAAP revenue guidance of approximately US$110 to US$125 million;', end='September 30, 2025'):
    return ('<html><body><h1>Example Company financial results</h1>'
            '<p>EXAMPLE CITY – June 30, 2025 – Example Company today announces its financial results and outlook.</p>'
            '<p>Reported revenue was $99 million in the previous quarter.</p>'
            '<h2>Fourth Quarter Fiscal Year 2025 Business Outlook</h2>'
            '<p>The outlook for the fourth quarter of fiscal year 2025, ending ' + end + ', is expected to be as follows:</p>'
            '<p>•' + revenue + '</p>'
            '<p>•Fourth quarter non-GAAP operating income guidance of approximately 66 percent of projected revenue.</p>'
            '<p>Actual results may vary materially. The company cannot reconcile this non-GAAP forecast without unreasonable effort.</p>'
            '<h2>Quarterly Dividends</h2><p>The board has declared a dividend of $0.20 per share.</p></body></html>').encode()


def record(raw=None):
    return dict(id=str(uuid4()), published_at=ACCEPTED, available_at=AVAILABLE,
                data=parse(raw or release_html(), form='earnings-release', cik=CIK))


def projection(raw=None):
    return guidance.extract(record(raw))


def report(value=120_000_000):
    normalized = normalize_performance(bundle(revenue=value), CIK, NOW)
    return dict(report=normalized['reports']['quarter'], snapshot_id='original-snapshot', payload_id='original-payload', first_recorded_at='2025-10-31T00:00:00Z')


def comparison(raw=None, actual=None, release=None):
    saved = release or record(raw)
    section = guidance.extract(saved)['sections'][0]
    return guidance.compare(section['forecasts'][0], section, saved, [actual or report()])


def seed_release(conn, iid, raw=None, *, accession='0000789019-25-000090', published=ACCEPTED, available=AVAILABLE):
    raw = raw or release_html()
    parent = dict(slot='earnings_filing', accession=accession, form='8-K', published_at=published,
                  url='https://www.sec.gov/Archives/edgar/data/789019/' + accession.replace('-', '') + '/results.htm')
    parsed = parse(raw, form='earnings-release', cik=CIK)
    disclosures.commit(conn, iid, parent, raw, parsed, available, 'Authored Company')
    item = dict(parent, slot='earnings_release_1', form='earnings-release', url=parent['url'].replace('results.htm', 'ex99.htm'))
    return disclosures.commit(conn, iid, item, raw, parsed, available, 'Authored Company')


@pytest.fixture(autouse=True)
def source_permission(owner):
    with transaction(admin=True) as conn:
        conn.execute("INSERT INTO sources VALUES('sec-disclosures','Original release test','sec-public') ON CONFLICT DO NOTHING")


def test_exact_original_section_keeps_context_and_separates_reported_results():
    saved = record()
    view = guidance.extract(saved)
    assert view['stated_release_date']['date'] == '2025-06-30'
    section = view['sections'][0]
    assert (section['period_type'], section['period_end']) == ('quarter', '2025-09-30')
    assert len(section['forecasts']) == 2
    revenue, margin = section['forecasts']
    assert (revenue['low'], revenue['high'], revenue['unit'], revenue['basis']) == ('110000000', '125000000', 'USD', 'gaap')
    assert (margin['low'], margin['unit'], margin['basis']) == ('66', 'percent', 'non-gaap')
    assert any('unreasonable effort' in p['quote'] for p in section['passages'])
    assert not any('dividend' in p['quote'] or '$99' in p['quote'] for p in section['passages'])
    for p in section['passages']:
        assert saved['data']['body'][p['start']:p['end']] == p['quote']


@pytest.mark.parametrize('text', [
    'AI semiconductor revenue guidance of US$21.7 billion;',
    'Fourth quarter revenue guidance of at least US$34.8 billion;',
    'Fourth quarter GAAP revenue guidance of US$130 to US$120 million;',
    'Fourth quarter GAAP revenue guidance of US$10 billion, up 25% year over year;',
    'Fourth quarter GAAP revenue guidance of US$10 million to EUR20 million;',
    'Fourth quarter non-GAAP operating income guidance of 166 percent of projected revenue.',
])
def test_unsupported_or_complex_prose_is_not_a_typed_whole_company_forecast(text):
    assert guidance.typed(text)['metric'] is None


def test_currency_basis_absence_and_zero_are_not_filled_or_dropped():
    value = guidance.typed('Fourth quarter revenue guidance of approximately $0 million;')
    assert value['low'] == value['high'] == '0' and value['unit'] is value['basis'] is None
    assert value['approximate']


@pytest.mark.parametrize('replacement', ['date unavailable', 'September 31, 2025'])
def test_missing_or_invalid_period_remains_unknown(replacement):
    section = projection(release_html(end=replacement))['sections'][0]
    assert section['period_end'] is None


def test_multiple_periods_and_corrupt_offsets_are_not_silently_accepted():
    raw = release_html(end='September 30, 2025 and ending December 31, 2025')
    assert projection(raw)['sections'][0]['period_end'] is None
    saved = record(); saved['data']['passages'][0]['quote'] = 'altered'
    with pytest.raises(ValueError, match='offsets'):
        guidance.extract(saved)


def test_conflicting_metric_period_and_withdrawal_context_stop_comparison():
    raw = release_html(revenue='First quarter GAAP revenue guidance of US$110 million;')
    assert projection(raw)['sections'][0]['period_end'] is None
    raw = release_html().replace(b'Actual results may vary materially.', b'The previous guidance is withdrawn. Actual results may vary materially.')
    assert projection(raw)['sections'][0]['review_status']
    assert comparison(raw)['status'] == 'uncompared'


@pytest.mark.parametrize('actual,relation', [(100_000_000, 'below'), (120_000_000, 'within'), (130_000_000, 'above')])
def test_matching_pre_period_guidance_is_compared_with_exact_filed_revenue(actual, relation):
    value = comparison(actual=report(actual))
    assert value['status'] == 'compared' and value['relation'] == relation
    assert value['actual'] == str(actual) and value['difference'] is None
    assert value['snapshot_id'] == 'original-snapshot'


def test_point_difference_is_decimal_safe_without_a_beat_miss_label():
    value = comparison(release_html(revenue='Fourth quarter GAAP revenue guidance of approximately US$119.987654 million;'))
    assert value['difference'] == '12346' and value['approximate']


@pytest.mark.parametrize('change', ['late_capture', 'late_filing', 'wrong_currency', 'non_gaap', 'missing_basis', 'wrong_period', 'year_to_date', 'amendment', 'input_date', 'input_accession', 'input_value', 'input_concept', 'missing_actual'])
def test_incomparable_forecasts_never_get_a_result_verdict(change):
    saved, actual = record(), report()
    if change == 'late_capture': saved['available_at'] = '2025-10-01T00:00:00Z'
    elif change == 'late_filing': saved['published_at'] = '2025-10-01T00:00:00Z'
    elif change in ('wrong_currency', 'non_gaap', 'missing_basis'):
        text = 'Fourth quarter GAAP revenue guidance of approximately US$110 to US$125 million;'
        text = text.replace('US$', '$') if change == 'wrong_currency' else text.replace('GAAP', 'non-GAAP') if change == 'non_gaap' else text.replace('GAAP ', '')
        saved = record(release_html(revenue=text))
    elif change == 'wrong_period': actual['report']['period_end'] = '2025-12-31'
    elif change == 'amendment': actual['report']['form'] = '10-Q/A'
    else:
        row = next(m for m in actual['report']['metrics'] if m['key'] == 'revenue')
        if change == 'year_to_date': row['start'] = row['inputs'][0]['start'] = '2025-01-01'
        elif change == 'input_date': row['inputs'][0]['end'] = '2025-08-30'
        elif change == 'input_accession': row['inputs'][0]['accession'] = 'other'
        elif change == 'input_value': row['inputs'][0]['value'] = '999'
        elif change == 'input_concept': row['inputs'][0]['concept'] = 'SegmentRevenue'
        elif change == 'missing_actual': row['value'] = None
    assert comparison(release=saved, actual=actual)['status'] == 'uncompared'


def test_same_period_later_correction_does_not_replace_first_saved_comparison():
    saved = record(); section = guidance.extract(saved)['sections'][0]
    original, later = report(), report(130_000_000)
    later['first_recorded_at'] = '2025-11-01T00:00:00Z'
    result = guidance.compare(section['forecasts'][0], section, saved, [later, original])
    assert result['actual'] == '120000000'


def test_database_history_current_parent_and_both_source_permissions(owner):
    iid = add_company('MSFT')['instrument_id']
    with transaction(source=True) as conn:
        first = seed_release(conn, iid)
        second = seed_release(conn, iid, release_html().replace(b'125 million', b'124 million'), published=ACCEPTED, available=datetime(2025, 7, 2, tzinfo=timezone.utc))
        commit_bundle(conn, iid, bundle(revenue=120_000_000), datetime.now(timezone.utc))
    with transaction(source=True) as conn:
        commit_bundle(conn, iid, bundle(revenue=130_000_000), datetime.now(timezone.utc))
    with transaction() as conn:
        view = guidance.present(conn, iid)
        assert len(view['releases']) == 2
        assert next(str(r['id']) for r in view['releases'] if r['current']) == second
        assert str(view['releases'][1]['id']) == first
        assert view['releases'][0]['sections'][0]['forecasts'][0]['comparison']['actual'] == '120000000'
    # A subsequent results filing without a corresponding current exhibit must
    # leave the older source labelled historical rather than current.
    with transaction(admin=True) as conn:
        conn.execute("DELETE FROM disclosure_current WHERE instrument_id=%s AND slot='earnings_filing'", (iid,))
        conn.execute("UPDATE sources SET entitlement='fictional' WHERE id='sec-companyfacts'")
    with transaction() as conn:
        view = guidance.present(conn, iid)
        assert all(not r['current'] for r in view['releases'])
        assert all(f['comparison']['status'] == 'uncompared' for r in view['releases'] for s in r['sections'] for f in s['forecasts'])
    with transaction(admin=True) as conn:
        conn.execute("UPDATE sources SET entitlement='fictional' WHERE id='sec-disclosures'")
    with transaction() as conn:
        assert guidance.present(conn, iid)['releases'] == []


def test_source_role_immutability_and_read_projection_do_not_write(owner):
    iid = add_company('MSFT')['instrument_id']
    with transaction(source=True) as conn:
        did = seed_release(conn, iid)
    with pytest.raises(Exception):
        with transaction(source=True) as conn:
            conn.execute('UPDATE disclosure_documents SET data=%s WHERE id=%s', ('{}', did))
    with transaction(consistent=True) as conn:
        before = one(conn, 'SELECT count(*) n FROM disclosure_documents')['n']
        for _ in range(2): guidance.present(conn, iid)
        assert one(conn, 'SELECT count(*) n FROM disclosure_documents')['n'] == before


def test_optional_actual_retained_release():
    path = Path(__file__).resolve().parents[1] / '.local/live-tests/management-outlook-20261009/original-releases.json'
    if not path.exists(): pytest.skip('Optional retained original release is absent.')
    saved = json.loads(path.read_text())[0]
    section = guidance.extract(saved)['sections'][0]
    revenue, margin = section['forecasts']
    assert section['period_end'] == '2026-11-01'
    assert revenue['low'] == '34800000000' and revenue['unit'] is revenue['basis'] is None
    assert margin['low'] == '66' and margin['basis'] == 'non-gaap'
    assert guidance.compare(revenue, section, saved, [])['status'] == 'uncompared'
    assert all('USD' not in reason for reason in guidance.compare(margin, section, saved, [])['reasons'])
