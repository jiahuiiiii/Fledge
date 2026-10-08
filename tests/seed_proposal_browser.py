"""Only fictional fixtures and mocked provider responses in disposable storage."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from thesis.config import DATA, OWNER, INSTRUMENT

assert str(DATA).startswith("/private/tmp/thesis-browser-")
from thesis import service
from thesis.db import transaction, one
from thesis.models import SaveIdea
from thesis.research import proposals
from test_proposals import provider


def changes(packet):
    return [
        dict(
            kind="reasoning",
            operation="update",
            question="Could renewals support durable growth?",
            reasoning="I need completed renewal evidence before concluding that demand is durable.",
        ),
        dict(
            kind="event",
            operation="add",
            target_condition_id=None,
            definition=dict(
                description="Renewal agreements are completed",
                evidence_requirement="A company report explicitly names completed renewals, not plans.",
                role="required",
                window_start=None,
                deadline=None,
            ),
        ),
        dict(
            kind="numeric",
            operation="add",
            target_condition_id=None,
            definition=dict(
                role="risk",
                metric="revenue_growth",
                operator="<=",
                threshold=None,
                period_type="quarter",
                max_report_age_days=None,
            ),
        ),
    ]


with transaction() as c:
    aurora = str(one(c, "SELECT id FROM instruments WHERE symbol='AURQ'")["id"])
for iid in [INSTRUMENT, aurora]:
    saved = service.save_idea(
        OWNER,
        SaveIdea(
            instrument_id=iid,
            expected_revision=0,
            question="Can recurring demand hold up?",
            reasoning="I want evidence of recurring demand before relying on the growth story.",
            status="draft",
            conditions=[],
        ),
    )
    req = proposals.GenerateRequest(
        instrument_id=iid,
        snapshot_id=service.state(OWNER, iid)["snapshot_id"],
        base_version_id=saved["version_id"],
    )
    proposals.generate(OWNER, req, transport=provider(changes))
print("Two authored proposal cases seeded; no external requests.")
