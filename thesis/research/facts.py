"""One explicit period/basis/unit resolution contract for briefs and monitoring."""

from decimal import Decimal

METRICS = {
    "revenue_growth": {
        "label": "Revenue growth",
        "meaning": "Revenue change versus the comparable period last year",
    },
    "operating_margin": {
        "label": "Operating margin",
        "meaning": "Operating income as a share of revenue",
    },
}


def resolve_fact(
    observations,
    metric,
    period,
    unit="percent",
    basis="reported",
    period_type="quarter",
):
    candidates = [
        o
        for o in observations
        if o["metric"] == metric
        and o["period"] == period
        and o["unit"] == unit
        and o["basis"] == basis
        and o.get("period_type", "quarter") == period_type
    ]
    superseded = {str(o["supersedes_id"]) for o in candidates if o.get("supersedes_id")}
    current = [o for o in candidates if str(o["id"]) not in superseded]
    values = {Decimal(str(o["value"])) for o in current}
    # Equivalent values may have multiple records; retain them as provenance,
    # selecting the most recently available exact version for the numeric result.
    current.sort(key=lambda o: (str(o.get("available_at", "")), str(o["id"])))
    observation = current[-1] if len(values) == 1 else None
    reason = (
        "Conflicting observations"
        if len(values) > 1
        else f"No compatible {period} observation" if not current else None
    )
    if not current and any(
        o["metric"] == metric
        and o["period"] == period
        and o.get("period_type", "quarter") != period_type
        for o in observations
    ):
        reason = f"No {period_type} observation: available figures cover a different reporting period type"
    return dict(
        observation=observation,
        candidates=current,
        disagreement=len(values) > 1,
        reason=reason,
    )


def fundamentals(observations, period, period_type="quarter"):
    result = []
    for metric, definition in METRICS.items():
        resolution = resolve_fact(observations, metric, period, period_type=period_type)
        observation = resolution["observation"]
        result.append(
            dict(
                metric=metric,
                **definition,
                period=period,
                period_type=period_type,
                period_end=observation.get("period_end") if observation else None,
                unit="percent",
                basis="reported",
                value=observation["value"] if observation else None,
                document_version_id=(
                    str(observation["document_version_id"]) if observation else None
                ),
                status=(
                    "conflicting"
                    if resolution["disagreement"]
                    else "available" if observation else "unavailable"
                ),
                reason=resolution["reason"],
                evidence_ids=[
                    str(o["document_version_id"]) for o in resolution["candidates"]
                ],
            )
        )
    return result


def coverage(checks, expected_sources):
    by_source = {c["source_id"]: c for c in checks}
    if any(c["outcome"] != "success" for c in checks):
        return "stale"
    if not set(expected_sources).issubset(by_source):
        return "unknown"
    return "fresh"


def active_facts(observations, documents, active_id=None):
    """One current SEC accession; a missing amended fact cannot resurrect old data."""
    public = [d for d in documents if d.get("entitlement") == "sec-public"]
    if not public:
        return observations
    latest = next((d for d in public if str(d["id"]) == active_id), None) or max(
        public, key=lambda d: (d["available_at"], str(d["id"]))
    )
    return [
        f for f in observations if str(f["document_version_id"]) == str(latest["id"])
    ]
