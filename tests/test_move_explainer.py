"""Bounded explainer contracts; outputs are authored, never paid model results."""
from copy import deepcopy
import json
import pytest
from thesis.providers import ledger, settings as S
from thesis.research import move_explainer as E
from test_model_budget import clean_model_ledger, response  # noqa: F401

# Three real saved META headlines (fair-meta, 16 October); remaining examples
# and every response below are authored. Passing proves citation enforcement,
# not the semantic quality of a live model or evidence of actual causation.
REAL_DOW = 'Dow Sees Best Day In Over A Month As Investors Rotate Out Of AI Trade On Overspending Concerns — CRWV, META, SPCX, PEP In Focus'
REAL_CPI = '10-15-2026: Hot CPI and PPI, Yield Reversal, AI Angst + Staples Rally'
REAL_TAX = 'Senators Want to Know Why Meta Claimed $6.6 Billion in Research Tax Credits for AI Data Centers'


def source(headline='Example Company cuts its annual revenue outlook', excerpt=''):
    return dict(headline=headline,excerpt=excerpt,kind='news',id='authored-version')


def answer(text='The reported outlook cut may help explain the move.', quote='cuts its annual revenue outlook',
           source_id='a1',cause='company'):
    return dict(cause=cause,sentences=[dict(text=text,citations=[dict(source_id=source_id,quote=quote)])])


def call(result,**kw):
    body=response() | dict(model=S.OPENAI_EXPLAINER_MODEL,
        output=[dict(type='message',content=[dict(type='output_text',text=json.dumps(result))])])
    body.update(kw)
    return dict(response_body=body)


@pytest.mark.parametrize('title,output,valid', [
    ('Example Company cuts its annual revenue outlook',answer(),True),
    ('New restrictions limit semiconductor exports',answer('The reported export restrictions may affect the sector.',
         'restrictions limit semiconductor exports',cause='sector'),True),
    (REAL_DOW,answer('The headline reports a rotation out of AI amid spending concerns.',
         'Investors Rotate Out Of AI Trade On Overspending Concerns',cause='market'),True),
    (REAL_CPI,dict(cause='no_clear',sentences=[]),True),
    (REAL_TAX,answer('The reported scrutiny of the tax credits may weigh on sentiment.',
         'Senators Want to Know Why Meta Claimed $6.6 Billion',cause='company'),True),
    ('Example Company cuts its annual revenue outlook',answer(source_id='unknown'),False),
    ('Example Company cuts its annual revenue outlook',answer(quote='raised its annual revenue outlook'),False),
    ('Example Company cuts its annual revenue outlook',answer(text='You should buy the stock now.'),False),
    ('Example Company cuts its annual revenue outlook',answer(text='The stock will recover next week.'),False),
    ('Example Company cuts its annual revenue outlook',answer(text='The outlook changed. This proves what caused the move.'),False),
])
def test_ten_authored_and_real_headline_citation_cases(title,output,valid):
    if valid:
        result=E.parse(call(output),{'a1':source(title)})
        assert result['cause']==output['cause']
        if output['cause']=='no_clear':assert result['text']==E.NO_CAUSE and result['sources']==[]
    else:
        with pytest.raises(ValueError):E.parse(call(output),{'a1':source(title)})


def test_citations_cannot_join_fields_cross_sources_repeat_or_quote_instructions():
    for output in [answer(quote='revenue outlook\nThe company'),answer(quote='company',source_id='a2')]:
        with pytest.raises(ValueError):E.parse(call(output),{'a1':source(excerpt='The company did not confirm this.')})
    output=answer();output['sentences'][0]['citations']*=2
    with pytest.raises(ValueError):E.parse(call(output),{'a1':source()})
    output=answer(cause='no_clear')
    with pytest.raises(ValueError):E.parse(call(output),{'a1':source()})
    with pytest.raises(ValueError):E.parse(call(dict(cause='company',sentences=[])),{})


def test_each_of_two_sentences_needs_its_own_same_source_quote():
    output=answer()
    output['sentences'].append(answer('The company says the earlier estimate no longer applies.',
                                      'earlier estimate no longer applies',source_id='a2')['sentences'][0])
    sources={'a1':source(),'a2':source('The earlier estimate no longer applies')}
    assert len(E.parse(call(output),sources)['sources'])==2
    sources['a2']['headline']='A different report entirely'
    with pytest.raises(ValueError):E.parse(call(output),sources)


def test_two_distinct_exact_quotes_from_one_source_are_valid():
    output=answer()
    output['sentences'][0]['citations'].append(dict(source_id='a1',quote='Earlier estimates no longer apply'))
    result=E.parse(call(output),{'a1':source(excerpt='Earlier estimates no longer apply.')})
    assert len(result['sentences'][0]['citations'])==2
    assert len(result['sources'])==1
    output['sentences'][0]['citations'][1]['quote']='Earlier estimates remain unchanged'
    with pytest.raises(ValueError):E.parse(call(output),{'a1':source(excerpt='Earlier estimates no longer apply.')})


@pytest.mark.parametrize('change', [
    dict(status='incomplete'),dict(output=[]),
    dict(output=[dict(type='message',content=[dict(type='output_text',text='{}'),dict(type='output_text',text='{}')])]),
])
def test_incomplete_and_ambiguous_responses_are_not_published(change):
    with pytest.raises(ValueError):E.parse(call(answer(),**change),{'a1':source()})


def test_named_request_role_has_its_own_finite_price_profile():
    for model,prices in [(S.OPENAI_EXPLAINER_MODEL,(5000,500,30000)),('claude-opus-5-5',(4000,200,20000))]:
        body=E.request_for(dict(event={},headlines=[]),model=model)
        profile=ledger.request_profile(body)
        assert (profile.input_price,profile.cached_price,profile.output_price)==prices
        assert profile.max_output==2000 and profile.effort=='low'
        assert ledger.estimate(body)>0 and len(E.INSTRUCTIONS)<6000
        broken=deepcopy(body);broken['text']['format']['name']='unpriced_role'
        with pytest.raises(ValueError):ledger.estimate(broken)
        broken=deepcopy(body);broken['max_output_tokens']=12000
        with pytest.raises(ValueError):ledger.estimate(broken)
    with pytest.raises(ValueError):E.request_for({},model=S.OPENAI_REASONING_MODEL)
    body=E.request_for({},model=S.OPENAI_EXPLAINER_MODEL);body['model']=S.OPENAI_REASONING_MODEL
    with pytest.raises(ValueError):ledger.estimate(body)


def test_explainer_disabled_by_default_and_does_not_change_bulk_selection(monkeypatch):
    monkeypatch.setattr(S,'EXPLAINER_MODEL',None)
    with pytest.raises(ValueError,match='disabled'):E.request_for({})
    assert S.explainer_choice({}) is None
    with pytest.raises(S.ProviderConfigError):S.explainer_choice({'THESIS_MOVE_EXPLAINER_MODEL':'unpriced'})
    selected=S.select({'THESIS_MODEL_PROVIDER':'openai'})
    assert S.select({'THESIS_MODEL_PROVIDER':'openai','THESIS_MOVE_EXPLAINER_MODEL':'claude-opus-5-5'})==selected


def test_mixed_provider_role_uses_own_key_and_requires_restart_for_change(monkeypatch):
    monkeypatch.setattr(S,'ROOT',S.APPROVED_ROOT)
    monkeypatch.setattr(S,'DATA',S.APPROVED_ROOT/'.local')
    monkeypatch.setattr(S,'PROVIDER','openai')
    monkeypatch.setattr(S,'MODEL',S.OPENAI_MODEL)
    monkeypatch.setattr(S,'REASONING_MODEL',S.OPENAI_REASONING_MODEL)
    monkeypatch.setattr(S,'EXPLAINER_MODEL','claude-opus-5-5')
    values=dict(THESIS_MODEL_PROVIDER='openai',THESIS_LIVE_MODELS_ENABLED='true',
                THESIS_MOVE_EXPLAINER_MODEL='claude-opus-5-5',OPENAI_API_KEY='authored-openai',
                ANTHROPIC_API_KEY='authored-anthropic')
    monkeypatch.setattr(S,'settings',lambda:values)
    assert S.live_key('claude-opus-5-5')=='authored-anthropic'
    assert S.live_key(S.MODEL)=='authored-openai'
    values['THESIS_MOVE_EXPLAINER_MODEL']=S.OPENAI_EXPLAINER_MODEL
    with pytest.raises(S.ProviderConfigError,match='restart'):S.live_key('claude-opus-5-5')


def test_mocked_explainer_usage_is_charged_once_with_its_exact_profile():
    body=E.request_for({},model=S.OPENAI_EXPLAINER_MODEL);calls=[]
    def transport(_):
        calls.append(True)
        return call(answer())['response_body']
    first=ledger.execute('authored-explainer','test',body,transport=transport)
    second=ledger.execute('authored-explainer','test',body,transport=transport)
    assert calls==[True] and first['id']==second['id']
    assert first['charged_nano_usd']==90*5000+10*500+20*30000
