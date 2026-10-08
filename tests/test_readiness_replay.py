"""Offline replay of the retained real-source and authored readiness evaluation."""
import json
import os
from pathlib import Path
import pytest
from thesis.research import sentiment, reporting_basis
from thesis.monitoring.news_watch import changes

@pytest.mark.parametrize('name',['NVDA','AMZN','META','CONTROLS'])
def test_retained_development_criteria_and_exact_input_quietness(name):
 folder=os.environ.get('THESIS_READINESS_CORPUS')
 if not folder:pytest.skip('Set THESIS_READINESS_CORPUS to the retained private evaluation folder')
 root=Path(folder)
 case=json.loads((root/'frozen.json').read_text())['cases'][name]
 call=json.loads((root/(name+'-call.json')).read_text())
 rendered=sentiment.render(call,case['packet'])
 assert rendered==json.loads((root/(name+'-result.json')).read_text())
 items={i['id']:i for i in rendered['items']}
 for label,expected in case['expected_events'].items():assert reporting_basis.eligible(items[label])==expected
 # Preserve the known frozen-label mismatch; replay is not a new accuracy claim.
 missed={label for label,expected in case['expected_adverse'].items() if reporting_basis.adverse(items[label])!=expected}
 assert missed==({'item_5'} if name=='CONTROLS' else set())
 analysis=dict(packet=case['packet'],result=rendered)
 assert changes(analysis,analysis)==[]
