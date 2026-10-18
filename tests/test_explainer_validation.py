"""The paid-trial runner is exercised only with authored mock responses."""
from copy import deepcopy
from decimal import Decimal
import json
import pytest
from thesis.providers import ledger,settings
from thesis.db import transaction,one
from experiments.soclaas_replay.explainer_validation import estimate,run,verify_sources
from test_model_budget import clean_model_ledger  # noqa: F401
from test_move_explainer import answer,call,source


def manifest():
    return dict(model=settings.OPENAI_EXPLAINER_MODEL,cases=[dict(id=f'authored-{i}',origin='authored',
        move=dict(members=[dict(symbol='EXMP',change_percent='-3.2')]),sources={'a1':source()},
        expected_cause='company') for i in range(10)])


def test_default_estimate_has_no_paid_call_or_research_write():
    before=ledger.snapshot()['calls'];result=estimate(manifest())
    assert result['cases']==10 and result['paid_calls']==result['app_research_writes']==0
    assert Decimal(result['summed_reservation_maximum_usd'])>0
    assert ledger.snapshot()['calls']==before


def test_ten_mocked_calls_stay_in_ledger_and_existing_output_cannot_retry(tmp_path):
    calls=[]
    def transport(body):calls.append(True);return call(answer())['response_body']
    output=tmp_path/'once'
    result=run(manifest(),output,Decimal('2'),transport=transport)
    assert result['completed'] and result['passed']==result['attempted']==len(calls)==10
    assert ledger.snapshot()['calls']==10 and result['automatic_retries']==0
    with pytest.raises(FileExistsError):run(manifest(),output,Decimal('2'),transport=transport)
    assert len(calls)==10


@pytest.mark.parametrize('failure',['invalid','timeout'])
def test_first_paid_failure_stops_without_retry_and_preserves_charge_or_hold(tmp_path,failure):
    calls=[]
    def transport(body):
        calls.append(True)
        if failure=='timeout':raise TimeoutError('Authored private failure')
        return call(answer(quote='Invented evidence not in this headline'))['response_body']
    result=run(manifest(),tmp_path/failure,Decimal('2'),transport=transport)
    assert len(calls)==result['attempted']==1 and not result['completed']
    if failure=='timeout':assert Decimal(result['unresolved_maximum_usd'])>0
    else:assert Decimal(result['paid_usd'])>0
    assert ledger.snapshot()['calls']==1


def test_cap_refuses_before_dispatch_and_unpriced_or_changed_manifest_refused(tmp_path):
    result=run(manifest(),tmp_path/'cap',Decimal('.000001'),transport=lambda _:pytest.fail('Over-cap dispatch'))
    assert result['attempted']==0 and result['stopped']=='cap_before_dispatch'
    for changed in [dict(manifest(),model=settings.OPENAI_REASONING_MODEL),dict(manifest(),cases=[]),
                    dict(manifest(),cases=[manifest()['cases'][0]]*10)]:
        with pytest.raises(ValueError):estimate(changed)
    with pytest.raises(ValueError):run(manifest(),tmp_path/'too-large',Decimal('3'),transport=lambda _:None)


def test_frozen_source_access_is_rechecked_before_a_paid_dispatch(owner,tmp_path):
    from test_move_alerts import setup
    setup(owner)
    with transaction(owner,consistent=True) as c:
        doc=one(c,"SELECT v.* FROM document_versions v JOIN documents d ON d.id=v.document_id WHERE d.source_id='finnhub-news' LIMIT 1")
    case=manifest()['cases'][0]
    case.update(origin='saved_real',sources={'a1':dict(kind='news',id=str(doc['id']),version=doc['content_hash'])})
    with transaction(owner,consistent=True) as c:verify_sources(c,case)
    with transaction(admin=True) as c:c.execute("UPDATE sources SET entitlement='fictional' WHERE id='finnhub-news'")
    with transaction(owner,consistent=True) as c:
        with pytest.raises(ValueError):verify_sources(c,case)


def test_explicit_continuation_reuses_saved_answers_and_never_retries_attempts(tmp_path):
    first=tmp_path/'first';first.mkdir()
    frozen=manifest()
    (first/'manifest.json').write_text(json.dumps(frozen))
    (first/'validation.json').write_text(json.dumps(dict(unresolved_maximum_usd='0')))
    for case in frozen['cases'][:5]:
        (first/(case['id']+'.response.json')).write_text(json.dumps(call(answer())['response_body']))
    calls=[]
    def transport(_):calls.append(True);return call(answer())['response_body']
    result=run(frozen,tmp_path/'continued',Decimal('1'),transport=transport,remaining_after=first)
    assert result['completed'] and result['passed']==10 and result['attempted']==len(calls)==5
    assert sum(c.get('reused_saved_response',False) for c in result['calls'])==5
    (first/(frozen['cases'][5]['id']+'.request.json')).write_text('{}')
    with pytest.raises(ValueError,match='previously attempted'):
        run(frozen,tmp_path/'refused',Decimal('1'),transport=transport,remaining_after=first)
    assert len(calls)==5
    (first/'manifest.json').write_text('{}')
    with pytest.raises(ValueError,match='identical'):
        run(frozen,tmp_path/'changed',Decimal('1'),transport=transport,remaining_after=first)
