"""Blind annotation/scoring tests use invented text and no model calls."""
from collections import Counter
from copy import deepcopy
import json
import pytest
from experiments.soclaas_replay import owner_quality_set as Q
from thesis.db import transaction


def packets():
    return [dict(company=dict(symbol=symbol,name=symbol+' Example'),sources=[
        dict(id=f'{symbol}-{channel}-{n}',label=f'item_{n}',channel=channel,
             title=f'Invented {symbol} report {n}',passages=[dict(id='p0',quote='Title'),dict(id='p1',quote='Invented source text.')],
             published_at='2026-10-16T12:00:00+00:00',sentiment='hidden-model-answer')
        for channel in ('news','social') for n in range(20)]) for symbol in ('EXA','EXB')]


def labels(manifest):
    return dict(fingerprint=manifest['fingerprint'],independently_labelled_by_owner=True,
                answers={c['id']:dict(relevance='relevant',sentiment='neutral') for c in manifest['cases']})


def test_sample_is_fixed_balanced_and_blind_to_model_answers():
    original=packets();m=Q.build(original)
    assert m['count']==len(m['cases'])==50 and not m['ai_suggestions']
    assert Counter(c['channel'] for c in m['cases'])==dict(news=25,social=25)
    assert sorted(Counter((c['company'],c['channel']) for c in m['cases']).values())==[12,12,13,13]
    changed=deepcopy(original)
    for packet in changed:
        packet['sources'].reverse()
        for source in packet['sources']:source['sentiment']='a different hidden answer'
    assert Q.build(changed)['cases']==m['cases']
    assert 'hidden-model-answer' not in json.dumps(m)
    assert all('sentiment' not in c and 'publisher' not in c for c in m['cases'])


def test_underfilled_sample_refuses_instead_of_changing_strata():
    with pytest.raises(ValueError,match='Insufficient'):Q.build([dict(packets()[0],sources=packets()[0]['sources'][:21])])


def test_exact_80_percent_gate_requires_all_fifty_real_owner_labels():
    m=Q.build(packets());human=labels(m);pred=deepcopy(human['answers'])
    for case in m['cases'][:10]:pred[case['id']]['sentiment']='negative'
    result=Q.score(m,human,pred)
    assert result['exact_matches']==40 and result['exact_percent']==80 and result['owner_50_gate_passed']
    pred[m['cases'][10]['id']]['sentiment']='unclear'
    assert not Q.score(m,human,pred)['owner_50_gate_passed']
    for bad in [dict(human,independently_labelled_by_owner=False),dict(human,fingerprint='another sample')]:
        with pytest.raises(ValueError):Q.score(m,bad,pred)
    human['answers'].pop(m['cases'][0]['id'])
    with pytest.raises(ValueError,match='All 50'):Q.score(m,human,pred)


def test_changed_or_invalid_labels_and_predictions_cannot_shrink_denominator():
    m=Q.build(packets());human=labels(m);pred=deepcopy(human['answers'])
    pred[m['cases'][0]['id']]['sentiment']=''
    with pytest.raises(ValueError,match='explicit'):Q.score(m,human,pred)
    m['cases'][0]['title']='Changed after annotation'
    with pytest.raises(ValueError,match='manifest changed'):Q.score(m,human,pred)


def test_runner_predictions_retain_their_sample_fingerprint():
    m=Q.build(packets());human=labels(m)
    wrapped=dict(fingerprint=m['fingerprint'],predictions=deepcopy(human['answers']))
    assert Q.score(m,human,wrapped)['exact_matches']==50
    wrapped['fingerprint']='another sample'
    with pytest.raises(ValueError,match='different frozen'):Q.score(m,human,wrapped)


def test_html_has_no_external_dependencies_or_executable_source_text():
    m=Q.build(packets());m['cases'][0]['title']='</script><img src=x onerror=alert(1)>'
    m['fingerprint']=Q.digest(m['cases']);html=Q.render(m)
    assert '</script><img' not in html and '\\u003c/script>' in html
    assert "connect-src 'none'" in html and 'fetch(' not in html
    assert '<option value="">Choose tone</option>' in html
    assert 'I labelled these sources myself without AI suggestions.' in html
    assert 'textContent' in html and 'innerHTML' not in html


def test_export_reads_database_in_read_only_transaction_and_never_overwrites(owner,tmp_path,monkeypatch):
    from thesis.research import sentiment
    from thesis.db import rows
    with transaction(owner,consistent=True) as conn:
        symbols=[r['symbol'] for r in rows(conn,'SELECT symbol FROM instruments ORDER BY symbol LIMIT 2')]
    sample=packets();calls=[]
    def prepare(conn,iid,now):
        assert conn.execute('SHOW transaction_read_only').fetchone()['transaction_read_only']=='on'
        calls.append(iid)
        return sample[len(calls)%2]
    monkeypatch.setattr(sentiment,'prepare',prepare)
    result=Q.export(symbols,tmp_path/'once')
    assert result['paid_calls']==result['research_writes']==0 and len(calls)==2
    assert (tmp_path/'once/review.html').exists()
    with pytest.raises(FileExistsError):Q.export(symbols,tmp_path/'once')
