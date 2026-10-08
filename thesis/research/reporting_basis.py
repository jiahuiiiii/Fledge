"""A news-development decision separate from sentiment; no extra model call."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

POLICY = "source-development-2"
class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    passages: list[str] = Field(max_length=3)
    impact: Literal["adverse", "mixed", "favourable", "not_stated"]
    kind: Literal["reported_event", "unconfirmed_event", "opinion_only", "conditional_only", "question_only", "insufficient_detail", "not_applicable"]

INSTRUCTION = """For each NEWS item also select reporting evidence independently of its sentiment. First select exact passages stating a specific target-company development, then choose its kind. reported_event requires a concrete reported action, result, announcement, decision or change with an identifiable actor and what happened. An announced plan is an announcement, not completion. unconfirmed_event requires a specific attributed allegation or rumour with its actual substance, never confirmation. Opinion about valuation, predictions, general concern and third-party commentary do not by themselves report a business event: opinion_only. A hypothetical possible outcome without an actual action/result is conditional_only. Questions without an answer are question_only. An invitation to read/listen/watch someone discuss concerns, without stating the actual allegation or development, is insufficient_detail. Unclear target or unrelated items are not_applicable. All non-event kinds must return passages=[]. Event kinds must select 1–3 own-source passages preserving the target actor, substantive action/result, attribution and conditional/announced status; never cite just a generic introduction. Social posts cannot supply this field or become news confirmation. A negative or positive opinion can retain directional sentiment while being ineligible for a reporting alert. For reported_event and unconfirmed_event, impact refers ONLY to the stated impact of that specific development on the target, supported by the selected reporting passages. Use adverse for an explicitly stated harmful outcome (for example a breach exposing data, missed guidance, declining revenue or a loss); favourable for an explicit benefit; mixed only if that same development has both explicitly stated favourable and adverse effects; otherwise not_stated. Do not borrow valuation opinions, worries about possible future demand, stock trading signals or a conditional moat/catalyst headline to assign impact to a descriptive launch, pledge, financing or agreement. The amount of money spent or raised is not itself benefit or harm. Non-event kinds require impact=not_stated. This is still an interpretation of supplied text, not fact verification."""

LABELS = {
    "reported_event": "Specific development reported",
    "unconfirmed_event": "Specific unconfirmed claim",
    "opinion_only": "Opinion, not an event update",
    "conditional_only": "Hypothetical outcome",
    "question_only": "Question without a reported answer",
    "insufficient_detail": "Not enough detail for an event alert",
    "not_applicable": "No clear company development",
}

def render(value, source, relevance):
    if value is None:
        raise ValueError("News reporting evidence is missing.")
    eligible = value.kind in {"reported_event", "unconfirmed_event"}
    if bool(value.passages) != eligible:
        raise ValueError("Only a specific reported or unconfirmed event has reporting passages.")
    if not eligible and value.impact != "not_stated":
        raise ValueError("Non-events cannot carry a reported event impact.")
    if eligible and relevance != "relevant":
        raise ValueError("Reporting evidence must concern the selected company.")
    own = {p["id"]: p["quote"] for p in source["passages"]}
    if len(set(value.passages)) != len(value.passages) or any(p not in own for p in value.passages):
        raise ValueError("Reporting passages must belong to the original report.")
    return dict(policy=POLICY, kind=value.kind, impact=value.impact, eligible=eligible, label=LABELS[value.kind], citations=[dict(source_id=source["id"], passage_id=p, quote=own[p]) for p in value.passages])

def eligible(item):
    basis = item.get("reporting_basis")
    if basis is not None:
        return basis.get("policy") == POLICY and basis.get("eligible") is True and bool(basis.get("citations"))
    # Historical outputs retain their contract; new outputs require evidence.
    return item.get("statement") in {"reported_development", "rumour"}


def adverse(item):
    basis = item.get("reporting_basis")
    if basis is not None:
        return eligible(item) and basis.get("impact") in {"adverse", "mixed"}
    return eligible(item) and item.get("sentiment") in {"negative", "mixed"}
