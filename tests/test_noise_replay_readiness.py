"""Pure, invented replay inputs: no provider or live database access."""
from copy import deepcopy
import pytest
from experiments.soclaas_replay import noise_replay_readiness as N
from thesis.research.citations import source_passages


def signed(capture):
    capture['fingerprint'] = N.digest({k:v for k,v in capture.items() if k != 'fingerprint'})
    return capture


def fixture():
    title, text = 'Example Co announces a service', 'Example Co announced its new service.'
    passages,_ = source_passages(title,text)
    source = dict(id='source-1',instrument_id='company-1',channel='news',title=title,text=text,
        passages=passages,publisher='Authored example',published_at='2026-10-10T00:00:00+00:00',
        available_at='2026-10-10T01:00:00+00:00')
    capture = signed(dict(policy='saved-news-noise-inputs-1',
        window_start='2026-10-09T16:00:00+00:00',window_end='2026-10-16T16:00:00+00:00',
        companies=[dict(instrument_id='company-1',symbol='EX',name='Example Co')],
        sources={source['id']:source},frames=[dict(instrument_id='company-1',symbol='EX',
            cutoff='2026-10-10T01:00:00+00:00',initial_baseline=False,
            source_ids=[source['id']],comparison_source_ids=[])]))
    record = dict(id='analysis-1',call_id='original-bulk-call',created_at='2026-10-10T02:00:00+00:00',
        packet=dict(instrument_id='company-1',sources=[deepcopy(source)],**N.POLICIES),
        result=dict(prompt_version=N.sentiment.PROMPT,summary_policy=N.sentiment.POLICY,
            guard_policy=N.sentiment_guards.POLICY,model='original-bulk-model',items=[dict(
                source_id='source-1',channel='news',relevance='relevant',sentiment='neutral',
                citations=[dict(source_id='source-1',passage_id='p1',quote=text)])]))
    return capture,record


def test_inventory_does_not_turn_later_labels_into_historical_availability_or_acceptance():
    c,r = fixture();before = deepcopy((c,r));report = N.assess(c,[r])
    assert report['totals']['opportunities'] == report['totals']['saved_candidates'] == 1
    assert report['totals']['later_identical_evidence'] == 1
    assert report['totals']['already_available'] == 0
    assert report['paid_calls'] == report['app_writes'] == report['completed_noise_days'] == 0
    assert not report['noise_gate_passed']
    assert 'sentiment' not in report['exact_candidates']['source-1']
    assert report['exact_candidates']['source-1']['model'] == 'original-bulk-model'
    assert before == (c,r)


def test_earliest_matching_label_is_selected_independent_of_input_order():
    c,r = fixture();earlier = deepcopy(r);earlier.update(id='earlier',created_at=c['frames'][0]['cutoff'])
    for records in ([r,earlier],[earlier,r]):
        result = N.assess(c,records)
        assert result['totals']['already_available'] == 1
        assert result['totals']['later_identical_evidence'] == 0
        assert result['exact_candidates']['source-1']['analysis_id'] == 'earlier'


@pytest.mark.parametrize('change',['text','metadata','company','prompt','policy','citation','direction'])
def test_changed_evidence_company_contract_or_fabricated_quote_cannot_supply_a_candidate(change):
    c,r = fixture();item = r['result']['items'][0]
    if change == 'text': r['packet']['sources'][0]['text'] += ' Changed evidence.'
    elif change == 'metadata': r['packet']['sources'][0]['publisher'] = 'Different attribution'
    elif change == 'company': r['packet']['instrument_id'] = 'different-company'
    elif change == 'prompt': r['result']['prompt_version'] = 'old-unsupported-prompt'
    elif change == 'policy': r['packet']['reporting_policy'] = 'old-reporting'
    elif change == 'citation': item['citations'][0]['quote'] = 'Invented citation'
    else: item.update(relevance='unrelated',sentiment='negative')
    result = N.assess(c,[r])
    assert result['totals']['missing'] == 1 and not result['exact_candidates']


def test_google_old_cluster_text_cannot_replace_headline_only_projection():
    c,r = fixture();source = c['sources']['source-1'];source['text'] = ''
    source['passages'],_ = source_passages(source['title'],'');signed(c)
    result = N.assess(c,[r])
    assert result['unmatched_evidence_versions'] == result['totals']['missing'] == 1


def test_quick_skip_requires_current_policy_and_keeps_quick_model_and_call_provenance():
    c,r = fixture();item = r['result']['items'][0]
    item.update(prefilter=True,relevance='unrelated',sentiment='unclear',citations=[])
    r['result']['prefilter'] = dict(policy='outdated',model='original-quick-model',call_ids=['quick-call'])
    assert N.assess(c,[r])['totals']['missing'] == 1
    r['result']['prefilter']['policy'] = N.relevance_prefilter.POLICY
    saved = N.assess(c,[r])['exact_candidates']['source-1']
    assert saved['model'] == 'original-quick-model' and saved['call_ids'] == ['quick-call']
    assert saved['call_id'] is None


@pytest.mark.parametrize('change',['fingerprint','future','outside','order','duplicate','passages','window','timezone'])
def test_invalid_or_future_replay_inputs_fail_closed(change):
    c,r = fixture()
    if change == 'fingerprint': c['fingerprint'] = 'changed'
    elif change == 'future': c['sources']['source-1']['available_at'] = '2026-10-10T02:00:00+00:00'
    elif change == 'outside': c['frames'][0]['cutoff'] = c['window_end']
    elif change == 'order':
        frame = deepcopy(c['frames'][0]);frame['cutoff'] = '2026-10-10T03:00:00+00:00'
        c['frames'].insert(0,frame)
    elif change == 'duplicate': c['frames'][0]['comparison_source_ids'] = ['source-1']
    elif change == 'passages': c['sources']['source-1']['passages'][1]['quote'] = 'Altered evidence'
    elif change == 'window': c['window_end'] = '2026-10-15T16:00:00+00:00'
    else: c['frames'][0]['cutoff'] = '2026-10-10T01:00:00'
    if change != 'fingerprint': signed(c)
    with pytest.raises(ValueError): N.assess(c,[r])


def test_initial_company_sample_is_quiet_and_not_a_missing_paid_opportunity():
    c,r = fixture();c['frames'][0]['initial_baseline'] = True;signed(c)
    result = N.assess(c,[])
    assert result['initial_quiet_frames'] == 1
    assert result['totals']['opportunities'] == result['totals']['missing'] == 0


def test_writable_connection_is_rejected_before_querying_any_saved_analysis():
    class Writable:
        def execute(self,sql):
            assert sql == 'SHOW transaction_read_only';return self
        def fetchone(self):return dict(transaction_read_only='off')
    c,_ = fixture()
    with pytest.raises(ValueError,match='read-only'):N.collect(Writable(),c)


def test_read_only_collection_uses_frozen_companies_and_retains_the_prior_week():
    c,r = fixture()
    class ReadOnly:
        def execute(self,sql,params=None):
            if sql == 'SHOW transaction_read_only':return self
            assert sql.startswith('SELECT id,call_id,created_at,packet,result FROM sentiment_analyses')
            assert params[0] == ['company-1']
            assert params[1] == N.instant(c['window_start'])-N.timedelta(days=7)
            return iter([r])
        def fetchone(self):return dict(transaction_read_only='on')
    assert N.collect(ReadOnly(),c)['totals']['saved_candidates'] == 1


def test_a_second_frame_cannot_count_the_same_source_as_another_new_opportunity():
    c,r = fixture();second = deepcopy(c['frames'][0]);second['cutoff'] = '2026-10-10T02:00:00+00:00'
    c['frames'].append(second);signed(c)
    with pytest.raises(ValueError,match='only once'):N.assess(c,[r])
