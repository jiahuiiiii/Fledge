"""Conservative item repairs and phase-one rollback; never rewrite paid responses."""
import os

POLICY = "sentiment-item-repair-1"


def enabled():
    value = os.environ.get("THESIS_SENTIMENT_RELIABILITY")
    if value is None and os.environ.get("THESIS_TEST_OFFLINE") != "true":
        from thesis.providers.settings import settings
        value = settings().get("THESIS_SENTIMENT_RELIABILITY")
    return str(value or "true").lower() not in {"false", "0", "off"}


def counts(items):
    return dict(policy=POLICY, repaired=sum(bool(i.get("repair")) for i in items),
                total=len(items))


def repair(item, source):
    """Only consistency repairs. Callers validate all citations before dropping fields."""
    original = item.model_dump()
    reasons = []
    mismatch = (
        (item.sentiment == "neutral" and item.basis != "descriptive")
        or (item.sentiment == "unclear" and item.basis != "unclear")
        or (item.sentiment in {"positive", "negative", "mixed"}
            and item.basis not in {"expressed_evaluation", "stated_outcome"})
    )
    if item.relevance != "relevant" and item.sentiment != "unclear":
        reasons.append("non_relevant_direction")
    if mismatch:
        reasons.append("tone_basis_disagree")
    if reasons:
        item.sentiment = item.basis = "unclear"
    if item.previous_passages and (source["channel"] != "social" or item.relevance != "relevant"):
        reasons.append("previous_attitude_outside_relevant_social")
        item.previous_passages = []
    if source["channel"] == "news" and item.price_claims:
        reasons.append("price_claims_on_news")
        item.price_claims = []
    if source["channel"] != "news" and item.reporting is not None:
        reasons.append("reporting_on_social")
        item.reporting = None
    return original, reasons
