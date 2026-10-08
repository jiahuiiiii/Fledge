"""Mixed-stream, multi-page authored inbox; disposable browser database only."""
import seed_digest_browser
from thesis.config import DATA, OWNER
assert str(DATA).startswith('/private/tmp/thesis-browser-')
from thesis import service, review_digest
from thesis.models import SaveIdea
from thesis.research import idea_alerts
from thesis.db import transaction, one
from test_idea_alerts import provider

iid=seed_digest_browser.seed_idea_alert_browser.iid
with transaction(OWNER) as conn:
    analysis=idea_alerts.latest_analysis(conn,iid)
for index in range(21):
    current=service.state(OWNER,iid)['versions'][0]
    service.save_idea(OWNER,SaveIdea(instrument_id=iid,expected_revision=current['revision'],question=f'Authored follow-up question {index+1}',reasoning=f'I want to investigate Microsoft margins in authored review case {index+1}.',status='draft',conditions=[]))
    idea_alerts.generate(OWNER,iid,str(analysis['id']),transport=provider('risk'))
report=review_digest.prepare(OWNER,days=0,review='pending')
assert report['total']>20
print('Authored inbox fixture:',report['total'],'published updates across all three types, two companies, more than one page; no external calls.')
