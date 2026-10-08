"""Three authored sentiment samples; real data and paid providers are never used."""

import seed_sentiment_browser
from thesis.db import transaction, one
from thesis.research import sentiment
from test_sentiment_history import variant

iid = seed_sentiment_browser.iid
with transaction() as c:
    current = one(c, "SELECT id FROM sentiment_analyses WHERE instrument_id=%s ORDER BY created_at DESC,id DESC LIMIT 1", (iid,))

def changed_method(packet, result):
    result['prompt_version'] = 'authored-earlier-method'

variant(iid, current['id'], changed_method)
print('Sample-history fixture: three authored samples, one explicit method change, watch remains off.')
