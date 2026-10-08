"""Financial invariants and persistence boundaries for explicit share-price cases."""

from copy import deepcopy
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal, localcontext
from hashlib import sha256
from uuid import uuid4
import json
import pytest
from pydantic import ValidationError
from thesis import valuation
from thesis.price_reference import PriceReference, prices
from thesis.db import transaction, one
from test_valuation import setup, request


def spec(**changes):
    return PriceReference(
        **(dict(valuation_date="2026-09-30", projected_shares_millions="0.00001",
                annual_return_percent="10", share_basis="Authored ten equivalent diluted shares, unchanged at the horizon.") | changes)
    )


def test_horizon_price_and_discount_have_correct_units_and_fractional_years():
    result = prices("3025", date(2027, 9, 30), spec())
    assert result['horizon_price'] == '302.5'
    with localcontext() as c:
        c.prec = 40
        expected = Decimal('302.5') / (Decimal('1.1') ** (Decimal(365) / Decimal('365.25')))
    assert abs(Decimal(result['entry_reference']) - expected) < Decimal('1e-23')
    assert Decimal(result['entry_reference']) < Decimal(result['horizon_price'])
    assert prices('3025', date(2027, 9, 30), spec(annual_return_percent='0'))['entry_reference'] == '302.5'


def test_split_and_dilution_scale_price_without_changing_equity():
    base = prices('3025', date(2027, 9, 30), spec())
    split = prices('3025', date(2027, 9, 30), spec(projected_shares_millions='0.00002'))
    assert Decimal(split['horizon_price']) * 2 == Decimal(base['horizon_price'])
    assert abs(Decimal(split['entry_reference']) * 2 - Decimal(base['entry_reference'])) < Decimal('1e-24')
    assert Decimal(prices('3025', date(2027, 9, 30), spec(annual_return_percent='20'))['entry_reference']) < Decimal(base['entry_reference'])


@pytest.mark.parametrize('target', [date(2026, 9, 30), date(2026, 9, 29)])
def test_expired_horizon_never_produces_a_forward_entry_reference(target):
    result = prices('3025', target, spec())
    assert result['horizon_price'] is None and result['entry_reference'] is None
    assert 'already ended' in result['reason']


def test_undefined_equity_stays_unavailable():
    result = prices(None, date(2027, 9, 30), spec())
    assert result['horizon_price'] is None and result['entry_reference'] is None


@pytest.mark.parametrize('changes', [
    {'projected_shares_millions':'0'}, {'projected_shares_millions':'-1'},
    {'projected_shares_millions':'NaN'}, {'projected_shares_millions':'Infinity'},
    {'projected_shares_millions':'10000001'}, {'projected_shares_millions':'0.0000001'},
    {'annual_return_percent':'-1'}, {'annual_return_percent':'101'},
    {'annual_return_percent':'Infinity'}, {'annual_return_percent':'NaN'},
    {'share_basis':'        '}, {'share_basis':'abc'}, {'share_class':'invented'},
])
def test_missing_or_unsafe_assumptions_rejected(changes):
    with pytest.raises(ValidationError):spec(**changes)


def test_legacy_assumptions_and_save_identity_do_not_change(owner):
    iid, data = setup(owner)
    req = valuation.SaveScenario(**data, request_id=uuid4())
    original = {k:v for k,v in req.model_dump(mode='json').items() if k not in ('price_reference','request_id')}
    expected = sha256(json.dumps(original, sort_keys=True).encode()).hexdigest()
    assert valuation.assumptions(req) == original
    result = valuation.save(owner, req)
    assert result['result']['method'] == 'equity-multiples-1'
    assert 'price_reference' not in result['result']
    with transaction(owner) as c:
        assert one(c,'SELECT request_hash FROM valuation_scenarios WHERE id=%s',(result['id'],))['request_hash']==expected


def test_price_preview_save_history_export_and_sensitivity(owner):
    iid, data = setup(owner)
    data['price_reference'] = spec().model_dump(mode='json')
    req = valuation.ScenarioRequest(**data)
    preview = valuation.preview(owner, req)
    result=preview['result'];case=result['cases'][0]
    assert result['method']=='equity-multiples-per-share-1'
    assert case['price_reference']['horizon_price']=='302.5'
    assert case['sensitivity']['rows'][1]['cells'][1]['price_reference']==case['price_reference']
    saved=valuation.save(owner,valuation.SaveScenario(**data,request_id=uuid4()))
    reopened=valuation.get(owner,saved['id'])
    assert reopened['result']==result and reopened['assumptions']['price_reference']==data['price_reference']
    html=valuation.download(owner,saved['id'])[1]
    assert 'Scenario horizon price' in html and 'Entry reference' in html
    assert 'Per-share sensitivity in USD' in html and '302.5' in html
    assert 'default-src' in html and '<script' not in html
    # A new assumption belongs to a new immutable saved comparison.
    changed=deepcopy(data);changed['price_reference']['projected_shares_millions']='0.00002'
    second=valuation.save(owner,valuation.SaveScenario(**changed,request_id=uuid4()))
    assert second['result']['cases'][0]['price_reference']['horizon_price']=='151.25'
    assert valuation.get(owner,saved['id'])['result']==result
    with transaction(admin=True) as c:c.execute("UPDATE sources SET entitlement='fictional' WHERE id='sec-companyfacts'")
    hidden=valuation.get(owner,saved['id'])
    assert hidden['withheld'] and hidden['result'] is None and hidden['packet'] is None
    assert '302.5' not in valuation.download(owner,saved['id'])[1]


def test_dates_reject_future_and_pre_filing_bases(owner):
    _,data=setup(owner)
    for as_of in ['2025-01-01',(datetime.now(timezone.utc).date()+timedelta(days=1)).isoformat()]:
        data['price_reference']=spec(valuation_date=as_of).model_dump(mode='json')
        with pytest.raises(ValueError,match='valuation date'):
            valuation.preview(owner,valuation.ScenarioRequest(**data))


def test_loss_case_and_sales_case_use_the_existing_model(owner):
    _,data=setup(owner);data['price_reference']=spec().model_dump(mode='json')
    data['cases'][0]['margin']='-5'
    result=valuation.preview(owner,valuation.ScenarioRequest(**data))['result']['cases'][0]
    assert result['price_reference']['entry_reference'] is None
    data['method']='sales';data['cases'][0].update(margin=None,multiple='4')
    result=valuation.preview(owner,valuation.ScenarioRequest(**data))['result']['cases'][0]
    assert result['equity_value']=='2420' and result['price_reference']['horizon_price']=='242'


@pytest.mark.parametrize('symbol', ['MSFT','AAPL','GOOGL','NVDA','AMZN','META'])
def test_six_actual_filing_bases_with_authored_share_assumptions(owner,symbol):
    """Actual saved filing revenue, explicitly fictional share/growth/return inputs."""
    import os
    import math
    from pathlib import Path
    from thesis.research.sec.service import add_company
    from thesis import service
    from test_sec_fundamentals import apply
    original=symbol in ['MSFT','AAPL','GOOGL']
    directory=os.environ.get('THESIS_REAL_CORPUS' if original else 'THESIS_EXPANDED_CORPUS')
    if not directory:pytest.skip('Opt-in retained SEC corpus, never fetch in tests')
    raw=json.loads((Path(directory)/(symbol+'.json' if original else symbol+'-bundle.json')).read_text())
    iid=add_company(symbol)['instrument_id'];apply(iid,raw['payload'] if original else raw)
    performance=service.state(owner,iid)['performance']
    data=request(iid,str(performance['snapshot_id']));data['years']=3
    data['price_reference']=spec(projected_shares_millions='1000',annual_return_percent='12').model_dump(mode='json')
    for method in ['earnings','sales']:
        data['method']=method;data['cases'][0].update(margin='20' if method=='earnings' else None,multiple='25' if method=='earnings' else '4')
        calculation=valuation.preview(owner,valuation.ScenarioRequest(**data));result=calculation['result']
        base=float(calculation['packet']['base']['value']);target=date.fromisoformat(result['target_period_end'])
        years=(target-date(2026,9,30)).days/365.25
        for row in result['cases'][0]['sensitivity']['rows']:
            for column,cell in zip(result['cases'][0]['sensitivity']['columns'],row['cells']):
                # Separate float implementation at loose financial precision checks unit/scale errors.
                value=base*(1+float(row['growth'])/100)**3
                value*=float(column)/100*25 if method=='earnings' else float(column)
                assert math.isclose(float(cell['price_reference']['horizon_price']),value/1e9,rel_tol=1e-12)
                assert math.isclose(float(cell['price_reference']['entry_reference']),value/1e9/(1.12**years),rel_tol=1e-12)
