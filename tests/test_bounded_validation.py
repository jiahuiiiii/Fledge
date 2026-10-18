"""Experiment guardrails use mocks and a disposable ledger, never paid providers."""
from decimal import Decimal
import json
import os
from unittest.mock import patch

import pytest

from experiments.soclaas_replay.bounded_validation import run
from thesis.providers import ledger
from thesis.research import sentiment
from test_sentiment_reliability import sample
from test_model_budget import clean_model_ledger  # noqa: F401


def inputs(folder):
    source=folder/'source';source.mkdir()
    body=sentiment.request_for(sample())
    (source/'b00.request.json').write_text(json.dumps(body))
    return source


def test_cap_stops_before_any_dispatch_and_preserves_offline_mode(tmp_path):
    source=inputs(tmp_path)
    with patch.object(ledger,'estimate',return_value=ledger.NANO),patch.object(ledger,'execute') as execute:
        report=run(source,tmp_path/'output',sentiment.SENTIMENT_MODEL,Decimal('.5'))
    execute.assert_not_called()
    assert report['stopped'] == 'script_cap_before_dispatch' and report['paid_usd'] == '0'
    assert os.environ['THESIS_TEST_OFFLINE'] == 'true'


def test_existing_run_directory_refuses_another_attempt(tmp_path):
    source=inputs(tmp_path); output=tmp_path/'output'; output.mkdir()
    with patch.object(ledger,'execute') as execute:
        with pytest.raises(FileExistsError): run(source,output,sentiment.SENTIMENT_MODEL,Decimal('1'))
    execute.assert_not_called()


def test_uncertain_paid_call_stops_once_and_records_its_retained_maximum(owner,tmp_path):
    source=inputs(tmp_path)
    execute=ledger.execute
    def interrupted(key,purpose,body):
        return execute(key,purpose,body,transport=lambda _:(_ for _ in ()).throw(TimeoutError()))
    with patch.object(ledger,'execute',side_effect=interrupted) as send:
        report=run(source,tmp_path/'output',sentiment.SENTIMENT_MODEL,Decimal('2'))
    assert send.call_count == 1 and report['stopped'] == 'BudgetBlocked'
    assert Decimal(report['unresolved_maximum_usd']) > 0
    assert report['failure_code'] == 'interrupted_or_invalid_usage'
    assert ledger.snapshot()['calls'] == 1 and ledger.snapshot()['unresolved'] == 1
