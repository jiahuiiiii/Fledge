"""Recorded company/idea/condition changes; no external requests."""

import seed_idea_alert_browser
from thesis.config import OWNER, DATA

assert str(DATA).startswith("/private/tmp/thesis-browser-")
from thesis import service
from test_integration import payload, drain

service.save_idea(OWNER, payload())
drain(OWNER)
service.advance(OWNER, 0)
drain(OWNER)
from thesis.models import ResearchAction

service.research_action(
    OWNER,
    ResearchAction(
        instrument_id=seed_idea_alert_browser.iid,
        question="Does customer adoption justify this story?",
        action="unresolved",
    ),
)
print(
    "Periodic review fixture: condition changes, grouped source alerts, private risk and quiet check; two companies."
)
