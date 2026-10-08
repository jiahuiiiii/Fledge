"""Read-only, source-scoped export of an explicitly selected immutable record."""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from html import escape
from urllib.parse import urlsplit

from . import service
from .monitoring.evaluator import outcome_label
from .db import transaction

NAMES = {"revenue_growth": "Revenue growth", "operating_margin": "Operating margin"}
OUTCOMES = {
    "met": "Condition met",
    "not_met": "Condition not met",
    "unknown": "Not enough evidence",
}
RELATIONS = {
    "supports": "May support the reasoning",
    "challenges": "May challenge the reasoning",
    "context": "Background context",
    "unclear": "Connection unresolved",
}


def text(value):
    return escape(str(value if value is not None else "Not recorded"), quote=True)


def stamp(value):
    if not value:
        return "Not recorded"
    parsed = (
        value
        if isinstance(value, datetime)
        else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    )
    return parsed.astimezone(timezone.utc).strftime("%d %b %Y, %H:%M:%S UTC")


def percentage(value):
    if value is None:
        return "Unknown"
    try:
        return f"{Decimal(str(value)):,.2f}%"
    except (ValueError, InvalidOperation):
        return "Unknown"


def parent_context_html(context, *, purpose="label"):
    """Separate, escaped provenance for a consumed immutable parent."""
    if not context:
        return ""
    title = purpose if purpose in {"connection", "finding"} else "label"
    boundary = (
        "not another source or independent confirmation"
        if purpose == "finding"
        else (
            "not a separate source connection"
            if purpose == "connection"
            else "not another sentiment vote"
        )
    )
    parts = [
        f"<h4>Parent context used for this {title}</h4><p>Separate message or story; {boundary}.</p>"
    ]
    if context["parent_type"] == "story":
        parts.append(f'<p>{text(context["title"])}</p>')
    parts.extend(
        f'<blockquote>{text(c["quote"])}</blockquote>' for c in context["citations"]
    )
    parts.append(
        f'<p>Published {text(stamp(context["published_at"]))} · checked {text(stamp(context["checked_at"]))}.</p><p>{text(context["limitation"])}</p>'
    )
    parsed = urlsplit(context["url"])
    if (
        parsed.scheme == "https"
        and parsed.hostname
        and not parsed.username
        and not parsed.password
    ):
        parts.append(
            f'<a href="{text(context["url"])}" rel="noopener noreferrer">Cited parent discussion</a>'
        )
    return "".join(parts)


def prepare(
    owner, version_id, *, evaluation_id=None, comparison_id=None, event_review_id=None
):
    if sum(bool(v) for v in (evaluation_id, comparison_id, event_review_id)) > 1:
        raise ValueError("Choose one assessment, comparison or event check to export.")
    # Check ownership with the actual application role before reading the company.
    with transaction(owner) as conn:
        instrument_id = service.version_instrument(conn, owner, version_id)
    state = service.state(owner, instrument_id)
    version = next(
        (v for v in state["versions"] if str(v["id"]) == str(version_id)), None
    )
    if not version:
        raise service.Missing("Saved idea not found.")
    evaluation = (
        next(
            (e for e in version["evaluations"] if str(e["id"]) == str(evaluation_id)),
            None,
        )
        if evaluation_id
        else None
    )
    comparison = (
        next(
            (
                r
                for r in version["evidence_reviews"]
                if str(r["id"]) == str(comparison_id)
            ),
            None,
        )
        if comparison_id
        else None
    )
    if (evaluation_id and not evaluation) or (comparison_id and not comparison):
        raise service.Missing(
            "This record does not belong to the selected saved revision."
        )
    if comparison and comparison.get("evaluation_id"):
        evaluation = next(
            (
                e
                for e in version["evaluations"]
                if str(e["id"]) == str(comparison["evaluation_id"])
            ),
            None,
        )
        if not evaluation:
            raise service.Missing(
                "The comparison's numerical assessment is unavailable."
            )
    event_review = next(
        (
            r
            for r in version.get("event_reviews", [])
            if str(r["id"])
            == str(
                event_review_id
                or (evaluation or {}).get("manifest", {}).get("event_review_id")
            )
        ),
        None,
    )
    if event_review_id and not event_review:
        raise service.Missing(
            "This event check does not belong to the selected saved revision."
        )
    # An assessment export deliberately does not silently choose an AI comparison.
    manifest = evaluation["manifest"] if evaluation else None
    source_ids = set(str(i) for i in (manifest or {}).get("document_ids", []))
    approved_proposals = [
        p
        for p in state.get("proposals", [])
        if p.get("accepted_version_id") == str(version["id"])
    ]
    for p in approved_proposals:
        source_ids.update(c["source_id"] for c in p["citations"])
    if comparison:
        source_ids.update(comparison["source_ids"])
    if event_review:
        source_ids.update(event_review["source_ids"])
    cutoff = (
        event_review["cutoff"]
        if event_review and not evaluation
        else comparison["cutoff"] if comparison else (manifest or {}).get("cutoff")
    )
    allowed = {d["id"]: d for d in state["documents"] if d["id"] in source_ids}
    observations = {
        str(o["id"]): o
        for o in state["observations"]
        if str(o["document_version_id"]) in allowed
    }
    return dict(
        instrument=state["instrument"],
        mode=state["demo"]["mode"],
        version=version,
        evaluation=evaluation,
        comparison=comparison,
        event_review=event_review,
        approved_proposals=approved_proposals,
        sources=allowed,
        observations=observations,
        cutoff=cutoff,
        unavailable_source_count=len(source_ids - set(allowed)),
        exported_at=datetime.now(timezone.utc),
    )


def render(record):
    v, e, comparison = record["version"], record["evaluation"], record["comparison"]
    sources, observations = record["sources"], record["observations"]
    company = record["instrument"]
    event_review = record.get("event_review")
    kind = (
        "Saved AI comparison"
        if comparison
        else (
            "Monitoring assessment"
            if e
            else (
                "Saved event evidence check"
                if event_review
                else "Saved idea definition"
            )
        )
    )
    parts = [
        f"<header><p class='eyebrow'>THESIS / RESEARCH RECORD</p><h1>{text(company['name'])} <span>{text(company['symbol'])}</span></h1><p>{kind} · revision {text(v['revision'])} · {text(v['status'])} when saved</p></header>",
        "<aside class='notice'>Private research record. It contains the author's saved reasoning. Check it before sharing. This is not a recommendation to buy, sell or hold.</aside>",
        f"<section><h2>{text(v['question'])}</h2><p class='reasoning'>{text(v['reasoning'] or 'No reasoning saved in this revision.')}</p><dl><dt>Revision saved</dt><dd>{text(stamp(v['created_at']))}</dd><dt>Evidence cutoff</dt><dd>{text(stamp(record['cutoff'])) if record['cutoff'] else 'No evidence assessed in this definition export'}</dd><dt>Export created</dt><dd>{text(stamp(record['exported_at']))}</dd></dl></section>",
    ]
    if record["mode"] == "recorded":
        parts.append(
            "<p class='notice'>Recorded fictional demonstration: company, sources and results are authored test material.</p>"
        )
    else:
        parts.append(
            "<p class='muted'>Actual retrieved company records; the saved investment reasoning and thresholds are the author's assumptions. News coverage consists of provider headlines and snippets, not complete articles.</p>"
        )
    if record["unavailable_source_count"]:
        parts.append(
            f"<p class='notice'>{record['unavailable_source_count']} historical source version(s) cannot be included under the current source access. Affected results or interpretations are withheld below.</p>"
        )
    parts.append("<section><h2>Saved monitoring definition</h2>")
    if not v["conditions"]:
        parts.append("<p>No numerical conditions were defined in this revision.</p>")
    for c in v["conditions"]:
        age = (
            f"At most {c['max_report_age_days']} days after the reporting-period end"
            if c.get("max_report_age_days") is not None
            else "No reporting-age limit selected"
        )
        parts.append(
            f"<article><h3>{'Risk to watch' if c.get('role') == 'risk' else 'Requirement'} · {text(NAMES.get(c['metric'], c['metric']))}</h3><p>{'At least' if c['operator'] == '>=' else 'At most'} {text(c['threshold'])}% · reported {text(c['period_type'])}</p><p>{text(age)}</p></article>"
        )
        if c.get("expected_period_end"):
            parts.append(
                f"<p>User-chosen reporting expectation: {text(c['period_type'])} figures for a period ending on or after {text(c['expected_period_end'])}, expected by {text(c['expected_report_by'])}, inclusive UTC. This is not a verified company or legal filing deadline. Missing figures after this date make this condition unknown.</p>"
            )
    for event in v.get("events", []):
        window = (
            f"Event happened {text(event['window_start'])} through {text(event['deadline'])}, inclusive source-stated calendar dates. Later reports may qualify; missing or ambiguous event dates remain unconfirmed."
            if event.get("date_basis") == "event_occurrence"
            else f"Reports published {text(event['window_start'])} through {text(event['deadline'])}, inclusive UTC dates. This limits report publication, not the actual event date."
        )
        parts.append(
            f"<article><h3>{'Risk to watch' if event['role'] == 'risk' else 'Required event'} · {text(event['description'])}</h3><p>{text(event['evidence_requirement'])}</p><p>{window}</p></article>"
        )
        if event.get("repeat_months"):
            from .monitoring.event_windows import windows

            parts.append(
                "<p>Finite repeating schedule; each window needs separate evidence:</p><ol>"
            )
            for w in windows(event):
                parts.append(
                    f"<li>{text(w['window_start'])} through {text(w['deadline'])}</li>"
                )
            parts.append("</ol>")
    parts.append("</section>")
    if record.get("approved_proposals"):
        parts.append(
            "<section><h2>Suggestions reviewed for this revision</h2><p>The saved definition above is the approved version and may differ from the initial AI suggestion. These are research assumptions, not verified outcomes or investment recommendations.</p>"
        )
        for proposal in record["approved_proposals"]:
            if proposal["source_unavailable"] or any(
                c["source_id"] not in sources for c in proposal["citations"]
            ):
                parts.append(
                    "<article><p>Suggestion evidence withheld because a cited source is unavailable.</p></article>"
                )
                continue
            parts.append(
                f"<article><h3>{text(proposal['kind'].capitalize())} suggestion · {text(proposal['operation'])}</h3><p>{text(proposal['rationale'])}</p><p>Suggestion evidence cutoff: {text(stamp(proposal['cutoff']))}</p>"
            )
            for citation in proposal["citations"]:
                parts.append(
                    f"<blockquote>{text(citation['quote'])}</blockquote><p><a href='#source-{text(citation['source_id'])}'>Inspect suggestion source</a></p>"
                )
            parts.append("</article>")
        parts.append("</section>")
    if e:
        parts.append(
            f"<section><h2>Monitoring assessment</h2><p>Assessed {text(stamp(e['manifest'].get('assessed_at', e['manifest']['cutoff'])))} · period {text(e['manifest']['period'])}</p><p>Source freshness: {text(e['freshness'])}. Source disagreement: {'present' if e['disagreement'] else 'not detected in this assessment'}.</p><p class='notice'>Numerical checks evaluate selected figures. Event checks interpret reports against your criteria. Neither establishes whether the investment reasoning is supported.</p>"
        )
        for r in e["results"]:
            observation = observations.get(str(r.get("observation_id")))
            parts.append(
                f"<article><h3>{text(NAMES.get(r['metric'], r['metric']))}</h3>"
            )
            if r.get("observation_id") and not observation:
                parts.append(
                    "<p>Historical result withheld: its source is unavailable under the current access.</p>"
                )
            else:
                parts.append(
                    f"<p><strong>{text(outcome_label(r))}</strong> · figure {text(percentage(r.get('observed_value')))}</p><p>{text(r.get('explanation'))}</p>"
                )
                if observation:
                    parts.append(
                        f"<p><a href='#source-{text(observation['document_version_id'])}'>Inspect the historical source</a></p>"
                    )
            report = next(
                (
                    a
                    for a in e["manifest"].get("report_expectations", [])
                    if a["condition_id"] == r["condition_id"]
                ),
                None,
            )
            if (
                report
                and not record["unavailable_source_count"]
                and (not r.get("observation_id") or observation)
            ):
                from .monitoring.report_expectations import (
                    explanation as report_explanation,
                )

                parts.append(f"<p>{text(report_explanation(report))}</p>")
            parts.append("</article>")
        action = {"reviewed": "Marked reviewed", "unresolved": "Left unresolved"}.get(
            e.get("review_action"), "Not marked reviewed"
        )
        parts.append(
            f"<p>Review state at export: {action}{' · ' + text(stamp(e['reviewed_at'])) if e.get('reviewed_at') else ''}. Acknowledging a review does not confirm the investment idea.</p></section>"
        )
    event_points = (
        e.get("event_results", []) if e else (event_review or {}).get("events", [])
    )
    if event_points:
        parts.append(
            "<section><h2>Event evidence</h2><p>AI interpretation of reports, not independent verification. No report, a denial or a passed deadline cannot establish completion or safety.</p>"
        )
        definitions = {
            str(event["condition_id"]): event for event in v.get("events", [])
        }
        for point in event_points:
            definition = definitions[str(point["condition_id"])]
            citations = point.get("citations", [])
            if point.get("window"):
                w = point["window"]
                parts.append(
                    f"<p>Checked window {w['index']} of {w['count']}: {text(w['window_start'])} through {text(w['deadline'])}. Earlier confirmations do not carry forward.</p>"
                )
            parts.append(f"<article><h3>{text(definition['description'])}</h3>")
            if point.get("withheld") or any(
                c["source_id"] not in sources for c in citations
            ):
                parts.append(
                    "<p>Historical interpretation withheld: a cited source is unavailable.</p>"
                )
            else:
                parts.append(
                    f"<p>{text(point.get('state', point.get('status', 'unknown')).replace('_', ' '))}</p><p>{text(point['explanation'])}</p>"
                )
                for citation in citations:
                    for selected in citation.get("occurrence_dates", []):
                        parts.append(
                            f"<p>Selected event date: {text(selected['date_text'])} → {text(selected['date'] or 'Timing unconfirmed')} · {text(selected['state'].replace('_', ' '))}</p>"
                        )
                    parts.append(
                        f"<blockquote>{text(citation['quote'])}</blockquote><p><a href='#source-{text(citation['source_id'])}'>Inspect event source</a></p>"
                    )
            parts.append("</article>")
        if event_review:
            if event_review.get("historical_window_check"):
                parts.append(
                    "<p>This earlier-window check is saved as history; it does not replace current monitoring.</p>"
                )
            elif event_review.get("applied_to_monitoring") is False:
                parts.append(
                    "<p>This automatic check was retained in history after its watch, revision or source snapshot changed. It was not applied to monitoring.</p>"
                )
            if e and e.get("manifest", {}).get("event_review_reuse"):
                parts.append(
                    "<p>The saved event interpretation was reused for identical event definitions and eligible source inputs. No new AI call was made; the original check date remains below.</p>"
                )
            parts.append(
                f"<p>{text(event_review['limitation'])}</p><p>Evidence check saved {text(stamp(event_review['created_at']))}. Model {text(event_review['model'])}; method {text(event_review['prompt_version'])}. Omitted sources: {text(event_review['omitted_source_count'])}. Incomplete passages omitted: {text(event_review['omitted_fragment_count'])}.</p>"
            )
        parts.append("</section>")
    if comparison:
        parts.append(
            f"<section><h2>Saved AI interpretation</h2><p>Saved {text(stamp(comparison['created_at']))}. This export does not generate or update an interpretation.</p>"
        )
        for point in comparison["points"]:
            citations = point.get("citations", [])
            if not citations or any(c["source_id"] not in sources for c in citations):
                parts.append(
                    "<article><p>Interpretation withheld because a cited source is unavailable under the current access.</p></article>"
                )
                continue
            parts.append(
                f"<article><h3>{text(RELATIONS.get(point['relation'], 'Connection unresolved'))}</h3><blockquote>{text(point['reasoning_quote'])}</blockquote><p>{text(point['text'])}</p>"
            )
            for citation in citations:
                source = sources[citation["source_id"]]
                parts.append(
                    f"<blockquote>{text(citation['quote'])}</blockquote><p class='muted'><a href='#source-{text(source['id'])}'>{text(source['source'])} · {text(source['title'])}</a></p>"
                )
            parts.append("</article>")
        parts.append(
            f"<p class='notice'>{text(comparison['limitation'])}</p><p>Omitted sources: {text(comparison.get('omitted_source_count', 0))}. Omitted incomplete passages: {text(comparison.get('omitted_fragment_count', 0))}.</p><p class='muted'>Model: {text(comparison['model'])} · method: {text(comparison['prompt_version'])}</p></section>"
        )
    if sources:
        parts.append(
            "<section><h2>Historical source register</h2><p>Source versions used by the selected record. Publication and first availability are distinct; a later correction does not replace this evidence. Open publisher links for context.</p>"
        )
        for source in sorted(
            sources.values(), key=lambda s: (s["published_at"], s["id"]), reverse=True
        ):
            parts.append(
                f"<article id='source-{text(source['id'])}'><h3>{text(source['title'])}</h3><p>{text(source['source'])} · {text(source['kind'])}</p><p>Published {text(stamp(source['published_at']))}<br>Available {text(stamp(source['available_at']))}</p>"
            )
            url = source.get("url") or ""
            parsed = urlsplit(url)
            if (
                parsed.scheme in {"https", "http"}
                and parsed.netloc
                and not parsed.username
                and not parsed.password
            ):
                parts.append(
                    f"<p><a href='{text(url)}' rel='noreferrer noopener'>Open original source</a></p>"
                )
            if source["kind"] in {"recorded", "sec-calculation"}:
                parts.append(
                    f"<details><summary>Saved source / calculation</summary><p class='source-text'>{text(source['body'])}</p></details>"
                )
            parts.append(
                f"<p class='identity'>Version {text(source['id'])}<br>SHA-256 {text(source['content_hash'])}</p></article>"
            )
        parts.append("</section>")
    parts.append(
        f"<footer><h2>Reading this record</h2><p>Dates, source access and review acknowledgement are stated as of this export. Missing information is not evidence of safety. Exact quotations make an interpretation traceable; they do not prove it is correct. No new data or paid model request is made when downloading.</p><p class='identity'>Saved revision {text(v['id'])}{'<br>Assessment ' + text(e['id']) if e else ''}{'<br>Comparison ' + text(comparison['id']) if comparison else ''}</p></footer>"
    )
    style = """body{font:16px/1.55 system-ui,sans-serif;color:#18222d;background:#f3f5f7;margin:0}main{max-width:860px;margin:auto;padding:40px 24px}h1{font-size:32px;letter-spacing:-1px}h1 span,.muted,dt{color:#526071}h2{font-size:22px}h3{font-size:17px}section,footer{margin:32px 0}article{padding:18px 20px;margin:12px 0;background:white;border:1px solid #d2dae2;border-radius:8px;break-inside:avoid}.notice{padding:14px 18px;background:#fff5d8;border-left:3px solid #997114}.reasoning,.source-text{white-space:pre-wrap;overflow-wrap:anywhere}blockquote{margin:12px 0;padding-left:14px;border-left:3px solid #8a99aa}a{color:#174e93;overflow-wrap:anywhere}.identity{font-size:11px;color:#526071;overflow-wrap:anywhere}.eyebrow{font-size:12px;letter-spacing:2px}dl{display:grid;grid-template-columns:160px 1fr;gap:6px}dd{margin:0}p{overflow-wrap:anywhere}@media(max-width:480px){main{padding:20px 14px}dl{display:block}dd{margin-bottom:12px}}@media print{body{background:white;font-size:11pt}main{max-width:none;padding:0}article{border-radius:0}a{color:inherit}details{display:block}details>p{display:block}summary{font-weight:bold}h2,h3{break-after:avoid}}"""
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'\"><title>Thesis research record — "
        + text(company["symbol"])
        + "</title><style>"
        + style
        + "</style></head><body><main>"
        + "".join(parts)
        + "</main></body></html>"
    )


def download(owner, version_id, **selection):
    record = prepare(owner, version_id, **selection)
    # Symbols and IDs are validated catalogue/UUID values; no private text in filename.
    suffix = (
        selection.get("event_review_id")
        or selection.get("comparison_id")
        or selection.get("evaluation_id")
        or version_id
    )
    filename = f"thesis-{record['instrument']['symbol']}-r{record['version']['revision']}-{str(suffix)[:8]}.html"
    return filename, render(record)
