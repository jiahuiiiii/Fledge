"""Deferred reads preserve scope; cached extraction never freezes permissions/reviews."""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from hashlib import sha256
from uuid import uuid4
import pytest

from thesis import service
from thesis.db import transaction
from thesis.research.sec import filing_facts as F, financial_recovery as R
from thesis.research.sec.disclosure_text import archive_url
from test_financial_recovery import setup, response, source
from test_disclosures import disclosure_scope
from test_model_budget import clean_model_ledger
from test_sec_fundamentals import bundle


@pytest.fixture
def clear_overlay():
    with F._overlay_lock:
        F._overlays.clear(); F._overlay_bytes = 0
    yield
    with F._overlay_lock:
        F._overlays.clear(); F._overlay_bytes = 0


def inputs():
    raw = source().replace(b'custom:CostOfRevenue', b'us-gaap:CostOfRevenue')
    document = dict(id=str(uuid4()), url=archive_url(789019, '0000789019-25-000001', 'example-20250930.htm'),
                    form='10-K', raw_html=raw, content_hash=sha256(raw).hexdigest())
    return bundle(annual=True), [document], 789019, datetime.now(timezone.utc)


def test_cache_reuses_exact_extraction_and_returns_independent_facts(clear_overlay, monkeypatch):
    args = inputs(); original = deepcopy(args)
    expected = F.attach(*args)
    first = F.cached_attach(*args)
    assert first == expected and args == original
    first['_original_facts']['CostOfRevenue'][0]['value'] = '999'
    monkeypatch.setattr(F, 'attach', lambda *_: pytest.fail('recomputed unchanged public extraction'))
    assert F.cached_attach(*args) == expected


@pytest.mark.parametrize('change', ['bytes', 'hash', 'id', 'url', 'form', 'bundle', 'time', 'cik', 'method', 'removed'])
def test_cache_invalidates_every_extraction_input(clear_overlay, monkeypatch, change):
    args = list(inputs()); F.cached_attach(*args)
    if change == 'bytes': args[1][0]['raw_html'] = args[1][0]['raw_html'].replace(b'>40<', b'>41<')
    elif change in ('hash', 'id', 'url', 'form'): args[1][0][{'hash':'content_hash'}.get(change, change)] = 'changed'
    elif change == 'bundle': args[0]['companyfacts']['entityName'] = 'Changed'
    elif change == 'time': args[3] += timedelta(days=1)
    elif change == 'cik': args[2] = 1
    elif change == 'method': monkeypatch.setattr(F, 'METHOD', 'changed')
    elif change == 'removed': args[1] = []
    calls = []
    monkeypatch.setattr(F, 'attach', lambda *a: calls.append(a) or dict(a[0], _original_facts={}))
    assert F.cached_attach(*args)['_original_facts'] == {} and len(calls) == 1


def test_core_defers_work_and_full_contract_is_unchanged(owner, disclosure_scope, monkeypatch):
    iid, _ = setup(owner)
    full = service.state(owner, iid)
    separate = service.financial_workspace(owner, iid)
    assert separate['instrument_id'] == iid
    for key in ('financial_depth', 'income_flow', 'segment_revenue', 'financials_pending'):
        assert separate[key] == full[key]
    monkeypatch.setattr(service, 'financial_sections', lambda *_: pytest.fail('eager financial calculation'))
    core = service.state(owner, iid, include_financials=False)
    assert core['financials_pending'] and core['financial_depth'] is None
    for key in ('instrument', 'performance', 'documents', 'versions', 'thesis', 'sentiment', 'management_outlook'):
        assert core[key] == full[key]


def test_warm_cache_still_checks_owner_review_revoke_and_source_access(owner, clean_model_ledger, disclosure_scope):
    iid, plan = setup(owner)
    def costs(who):
        packet = service.financial_workspace(who, iid)
        return [m['value'] for p in packet['income_flow'].get('periods', []) for m in p['metrics'] if m['key'] == 'cost']
    before = costs(owner)
    reading = R.generate(owner, iid, plan['document']['id'], plan['plan_id'], transport=response)
    accepted = R.review(owner, iid, reading['id'], ['cost'], None)
    assert '40000000' in costs(owner) and costs(owner) != before
    other = str(uuid4())
    with transaction(admin=True) as conn: conn.execute('INSERT INTO accounts VALUES(%s,%s)', (other, 'Other owner'))
    assert costs(other) == before
    R.review(owner, iid, reading['id'], [], accepted['review_id'])
    assert costs(owner) == before
    with transaction(admin=True) as conn: conn.execute("UPDATE sources SET entitlement='fictional' WHERE id='sec-companyfacts'")
    assert service.financial_workspace(owner, iid)['income_flow']['status'] == 'unavailable'


def test_cache_evicts_to_bounded_size(clear_overlay, monkeypatch):
    monkeypatch.setattr(F, '_OVERLAY_LIMIT', 1)
    assert F.cached_attach(*inputs())['_original_facts']
    assert not F._overlays and F._overlay_bytes == 0
