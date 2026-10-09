"""Dataset provenance/completeness and the reported failure, not model accuracy."""
import json
from experiments.sentiment_guards.evaluate import DATASET, replay, score


def test_frozen_real_sample_has_complete_sources_and_explicit_review_status():
    value=json.loads(DATASET.read_text()); records=value['records']
    assert len(records)==50 and len({r['source']['id'] for r in records})==50
    assert 'not independent human' in value['provenance']['reference_author']
    assert all(r['source']['url'] and r['source']['passages'] and r['review_note'] for r in records)
    report=replay(value)
    assert report['original']['compared']==report['checked']['compared']==50
    assert any(c['item']=='item_68' and c['before']=='positive' and c['after']=='unclear' for c in report['changes'])
    assert not report['checked']['missing']


def test_missing_predictions_are_reported_without_inventing_labels():
    records=json.loads(DATASET.read_text())['records']
    result=score(records,{})
    assert result['compared']==0 and len(result['missing'])==50
