"""Read-only periodic review of saved evidence; no acquisition or model calls.

A period bounds record creation, not the publication date of underlying evidence.
Review acknowledgements and coverage are shown as read now, separately from that
period. A download is a point-in-time private report, not a frozen DB snapshot.
"""

from thesis.monitoring.evaluator import outcome_label
from datetime import datetime, timedelta, timezone
from uuid import UUID
from .db import transaction, one, rows
from . import service
from .research import idea_alerts, sentiment, social
from .monitoring import news_watch

PAGE_SIZE = 20
# Owner predicates supplement forced RLS. UNION ALL keeps distinct alert kinds.
EVENTS = """WITH events AS (
 SELECT c.id,c.owner_id,t.instrument_id,c.version_id,c.created_at,'condition'::text kind,r.action review_action,r.created_at review_at
 FROM change_events c JOIN thesis_versions v ON v.id=c.version_id AND v.owner_id=c.owner_id
 JOIN theses t ON t.id=v.thesis_id AND t.owner_id=v.owner_id
 LEFT JOIN review_events r ON r.owner_id=c.owner_id AND r.evaluation_id=c.evaluation_id WHERE c.owner_id=%(owner)s
 UNION ALL
 SELECT a.id,a.owner_id,a.instrument_id,a.version_id,a.created_at,'company',r.action,r.created_at
 FROM research_alerts a LEFT JOIN research_alert_reviews r ON r.owner_id=a.owner_id AND r.alert_id=a.id WHERE a.owner_id=%(owner)s
 UNION ALL
 SELECT a.id,a.owner_id,a.instrument_id,a.version_id,p.created_at,'idea',r.action,r.created_at
 FROM idea_alert_checks a JOIN idea_alert_publications p ON p.owner_id=a.owner_id AND p.check_id=a.id
 LEFT JOIN idea_alert_reviews r ON r.owner_id=a.owner_id AND r.check_id=a.id WHERE a.owner_id=%(owner)s
) """


def clock(value):
    parsed = (
        value
        if isinstance(value, datetime)
        else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    )
    if parsed.tzinfo is None:
        raise ValueError("The review cutoff needs a timezone.")
    return parsed.astimezone(timezone.utc)


def coverage(conn, owner, company, now):
    """Current source health, never inferred from the absence of alerts."""
    iid = company["id"]
    watch = one(
        conn,
        "SELECT enabled,interval_minutes,match_idea,idea_purpose,last_check_at,next_check_at,error FROM news_watches WHERE owner_id=%s AND instrument_id=%s",
        (owner, iid),
    )
    if company["mode"] == "recorded":
        return dict(
            mode="recorded",
            watch=watch,
            concerns=["Recorded fictional sources; no external coverage."],
            news_checked_at=None,
            sentiment_cutoff=None,
            social_feeds=[],
        )
    refresh = one(
        conn, "SELECT * FROM market_refresh_state WHERE instrument_id=%s", (iid,)
    )
    analysis = idea_alerts.latest_analysis(conn, iid)
    concerns = []
    sec = one(
        conn,
        "SELECT last_attempt_at,last_error FROM sec_refresh_state WHERE instrument_id=%s",
        (iid,),
    )
    if not sec or not sec["last_attempt_at"]:
        concerns.append("Filings have not been checked by this installation.")
    elif sec["last_error"]:
        concerns.append(
            "The latest filing check failed; prior filings may still be displayed."
        )
    elif now - sec["last_attempt_at"] > timedelta(hours=24):
        concerns.append(
            "Filings were last checked more than 24 hours ago; newer reports may be missing."
        )
    if not one(
        conn,
        "SELECT id FROM sources WHERE id='finnhub-news' AND entitlement='finnhub-pitch'",
    ):
        concerns.append("Finnhub news source access is unavailable.")
    checked = refresh["completed_at"] if refresh else None
    if not checked:
        concerns.append("Finnhub news has not completed a source check.")
    elif refresh["news_error"]:
        concerns.append(
            "The latest Finnhub news check failed; older sources may still be displayed."
        )
    elif now - checked > timedelta(hours=24):
        concerns.append("The Finnhub news check is more than 24 hours old.")
    if refresh and refresh["lease_until"] and refresh["lease_until"] > now:
        concerns.append("A Finnhub news refresh is still in progress.")
    cutoff = analysis["packet"]["cutoff"] if analysis else None
    if not analysis:
        concerns.append("No news/social sentiment sample has been analysed.")
    elif sentiment.present(conn, analysis)["withheld"]:
        concerns.append("Source access changed; sentiment interpretation is withheld.")
    elif now - clock(cutoff) > timedelta(hours=24):
        concerns.append("The analysed news/social sample is more than 24 hours old.")
    feed_rows = social.status(conn, iid)
    for f in feed_rows:
        if not f["enabled"]:
            concerns.append(f["label"] + " is disabled.")
        elif f["error"]:
            concerns.append(f["label"] + " could not be checked.")
        elif not f["completed_at"]:
            concerns.append(f["label"] + " has not been checked.")
        elif now - f["completed_at"] > timedelta(hours=24):
            concerns.append(f["label"] + " was last checked more than 24 hours ago.")
    from thesis.research import source_hub
    for source in source_hub.status(conn, iid):
        if source["checked_at"] and source["status"] == "failed":
            concerns.append(source["label"] + " could not be checked.")
    if watch and watch["error"]:
        concerns.append(
            "The local watch reported an error; open its settings to inspect it."
        )
    return dict(
        mode="live",
        watch=watch,
        filing_watch=one(
            conn,
            "SELECT enabled,next_check_at FROM filing_watches WHERE owner_id=%s AND instrument_id=%s",
            (owner, iid),
        )
        or dict(enabled=False),
        concerns=concerns,
        news_checked_at=checked,
        sentiment_cutoff=cutoff,
        social_feeds=feed_rows,
    )


def change_detail(conn, owner, event):
    row = one(
        conn,
        """SELECT c.*,v.revision,v.question,v.reasoning,i.symbol,i.name,t.instrument_id
        FROM change_events c JOIN thesis_versions v ON v.id=c.version_id AND v.owner_id=c.owner_id
        JOIN theses t ON t.id=v.thesis_id AND t.owner_id=v.owner_id JOIN instruments i ON i.id=t.instrument_id
        WHERE c.id=%s AND c.owner_id=%s""",
        (event["id"], owner),
    )
    allowed = {
        str(d["id"])
        for d in service.permitted_documents(
            conn, datetime.now(timezone.utc), row["instrument_id"]
        )
    }
    manifests = rows(
        conn,
        "SELECT manifest FROM evaluations WHERE owner_id=%s AND id=ANY(%s::uuid[])",
        (owner, [row["evaluation_id"], row["previous_evaluation_id"]]),
    )
    needed = {str(i) for m in manifests for i in m["manifest"].get("document_ids", [])}
    withheld = len(manifests) != 2 or not needed.issubset(allowed)
    row["withheld"] = withheld
    row["review_action"] = event["review_action"]
    if withheld:
        row["summary"] = "Source access changed"
        row["details"] = dict(affected_conditions=[], affected_events=[], withheld=True)
    return row


def details(conn, owner, events):
    result = []
    for event in events:
        if event["kind"] == "idea":
            record = one(
                conn,
                "SELECT * FROM idea_alert_checks WHERE owner_id=%s AND id=%s",
                (owner, event["id"]),
            )
            detail = idea_alerts.present(conn, owner, record)
            title = "Connections to saved reasoning"
        elif event["kind"] == "company":
            detail = news_watch.list_alerts(conn, owner, ids=[event["id"]])[0]
            title = detail["payload"].get("title", "Company source alert")
        else:
            detail = change_detail(conn, owner, event)
            title = detail["summary"]
        if detail.get("withheld"):
            title = "Source access changed — details withheld"
        result.append(dict(event, title=title, detail=detail))
    return result


def prepare(
    owner,
    *,
    days=7,
    cutoff=None,
    instrument_id=None,
    review="all",
    page=0,
    now=None,
    exporting=False,
    window_start=None,
):
    now = clock(now or datetime.now(timezone.utc))
    end = clock(cutoff) if cutoff else now
    if type(days) is not int or days not in (0, 1, 7, 30):
        raise ValueError("Choose one day, seven days, thirty days or all records.")
    if end > now or type(page) is not int or not 0 <= page <= 100000:
        raise ValueError("Choose a past review cutoff and a valid page.")
    if review not in ("all", "pending", "unresolved", "reviewed"):
        raise ValueError("Choose a supported review status.")
    iid = str(UUID(str(instrument_id))) if instrument_id else None
    start = (
        end - timedelta(days=days)
        if days
        else datetime.min.replace(tzinfo=timezone.utc)
    )
    if window_start is not None:
        start = clock(window_start)
        if not start < end or end - start > timedelta(days=9):
            raise ValueError("Choose valid weekly review boundaries.")
    lower = ">" if window_start is not None else ">="
    older = "<=" if window_start is not None else "<"
    args = dict(
        owner=owner,
        start=start,
        end=end,
        iid=iid,
        review=review,
        limit=1000 if exporting else PAGE_SIZE,
        offset=0 if exporting else page * PAGE_SIZE,
    )
    with transaction(owner, consistent=True) as conn:
        companies = rows(
            conn,
            """SELECT i.*,s.mode,t.status,t.revision,v.question,v.reasoning
            FROM instruments i JOIN instrument_state s ON s.instrument_id=i.id
            LEFT JOIN theses t ON t.instrument_id=i.id AND t.owner_id=%s
            LEFT JOIN thesis_versions v ON v.thesis_id=t.id AND v.owner_id=t.owner_id AND v.revision=t.revision
            WHERE t.id IS NOT NULL OR EXISTS(SELECT 1 FROM news_watches w WHERE w.owner_id=%s AND w.instrument_id=i.id)
            ORDER BY i.symbol""",
            (owner, owner),
        )
        if iid and iid not in {str(c["id"]) for c in companies}:
            raise service.Missing(
                "No saved idea or watch exists for this company in your account."
            )
        summary = rows(
            conn,
            EVENTS
            + f"""SELECT instrument_id,
            count(*) FILTER(WHERE created_at {lower} %(start)s) new_count,
            count(*) FILTER(WHERE review_action IS NULL) pending_count,
            count(*) FILTER(WHERE review_action='unresolved') unresolved_count,
            count(*) FILTER(WHERE created_at {older} %(start)s AND review_action IS NULL) older_pending_count,
            max(created_at) latest_alert_at,max(review_at) latest_review_at FROM events WHERE created_at<=%(end)s GROUP BY instrument_id""",
            args,
        )
        by_id = {str(r["instrument_id"]): r for r in summary}
        for company in companies:
            counts = by_id.get(str(company["id"]), {})
            company.update(
                {
                    k: counts.get(k, 0)
                    for k in (
                        "new_count",
                        "pending_count",
                        "unresolved_count",
                        "older_pending_count",
                    )
                }
            )
            company["latest_alert_at"] = counts.get("latest_alert_at")
            company["latest_review_at"] = counts.get("latest_review_at")
            quiet = one(
                conn,
                f"""SELECT count(*) n FROM idea_alert_checks c WHERE c.owner_id=%s AND c.instrument_id=%s
                AND c.created_at {lower} %s AND c.created_at<=%s AND (c.result->>'noteworthy_count')::int=0
                AND NOT EXISTS(SELECT 1 FROM idea_alert_publications p WHERE p.owner_id=c.owner_id AND p.check_id=c.id)""",
                (owner, company["id"], start, end),
            )
            company["quiet_checks"] = quiet["n"]
            action = one(
                conn,
                "SELECT action,question,created_at FROM research_actions WHERE owner_id=%s AND instrument_id=%s AND created_at<=%s ORDER BY created_at DESC,id DESC LIMIT 1",
                (owner, company["id"], end),
            )
            company["research_action"] = action
            company["coverage"] = coverage(conn, owner, company, now)
        # Displayed records are paginated independently of exact all-record counts.
        where = f""" WHERE created_at {lower} %(start)s AND created_at<=%(end)s
            AND (%(iid)s::uuid IS NULL OR instrument_id=%(iid)s::uuid)
            AND (%(review)s='all' OR (%(review)s='pending' AND review_action IS NULL) OR review_action=%(review)s)"""
        total = one(conn, EVENTS + "SELECT count(*) n FROM events" + where, args)["n"]
        if exporting and total > 1000:
            raise ValueError(
                "This report exceeds 1,000 records. Choose a shorter period or one company before downloading."
            )
        page_rows = rows(
            conn,
            EVENTS
            + "SELECT * FROM events"
            + where
            + " ORDER BY created_at DESC,kind,id DESC LIMIT %(limit)s OFFSET %(offset)s",
            args,
        )
        records = details(conn, owner, page_rows)
        scoped = [c for c in companies if iid is None or str(c["id"]) == iid]
        return dict(
            generated_at=now,
            cutoff=end,
            window_start=start if days else None,
            days=days,
            instrument_id=iid,
            review=review,
            page=page,
            page_size=PAGE_SIZE,
            total=total,
            totals={
                k: sum(c[k] for c in scoped)
                for k in (
                    "new_count",
                    "pending_count",
                    "unresolved_count",
                    "older_pending_count",
                    "quiet_checks",
                )
            },
            companies=companies,
            records=records,
            limitation="This review uses saved records. It does not fetch sources or call AI. Record dates are when this app recorded an update, not when the underlying event happened. Review status and source coverage are read now; a quiet list does not establish that nothing important happened.",
        )


def download(owner, **filters):
    return render_report(prepare(owner, exporting=True, **filters))


def render_report(report):
    from .review_export import text, stamp, parent_context_html
    from urllib.parse import urlsplit

    parts = [
        "<h1>Research review</h1>",
        "<p><strong>Private research record.</strong> Includes saved reasoning.</p>",
        f'<p>Recorded updates: {text(stamp(report["window_start"])) if report["window_start"] else "All retained dates"} through {text(stamp(report["cutoff"]))}.</p>',
        f'<p>Generated {text(stamp(report["generated_at"]))}. Review status and coverage are read at generation time.</p>',
        f'<p>{text(report["limitation"])}</p><p>Selected review status: {text(report["review"])} · {report["total"]} records.</p>',
    ]
    if report.get("saved_review_id"):
        parts.append(
            f'<p>Scheduled review for {text(stamp(report["scheduled_at"]))} · schedule zone {text(report["schedule_time_zone"])}. Source access checked {text(stamp(report["access_checked_at"]))}.</p>'
        )
        if report["skipped_occurrences"]:
            parts.append(
                f'<p>{report["skipped_occurrences"]} earlier scheduled weeks were skipped while the app was unavailable. This saved review covers the latest scheduled week; older unread updates remain in its overview.</p>'
            )
    selected = [
        c
        for c in report["companies"]
        if not report["instrument_id"] or str(c["id"]) == report["instrument_id"]
    ]
    for c in selected:
        parts += [
            f'<h2>{text(c["symbol"])} — {text(c["name"])}</h2>',
            f'<p>Current idea: {text(c["question"] or "Watch without a saved idea")}</p>',
            f'<p>{c["new_count"]} updates in period · {c["pending_count"]} awaiting review through cutoff · {c["older_pending_count"]} awaiting review before this period · {c["unresolved_count"]} left unresolved through cutoff · {c["quiet_checks"]} quiet private checks in period.</p>',
        ]
        watch = c["coverage"]["watch"]
        parts.append(
            "<p>Local watch: "
            + ("On" if watch and watch["enabled"] else "Off")
            + ". Filing checks: "
            + (
                "daily while the local app runs"
                if c["coverage"].get("filing_watch", {}).get("enabled")
                else "manual; daily checks are off"
            )
            + ".</p>"
        )
        for concern in c["coverage"]["concerns"]:
            parts.append(f"<p>Coverage: {text(concern)}</p>")
    for event in report["records"]:
        d = event["detail"]
        parts.append(
            f'<section><h2>{text(d["symbol"])} · {text(event["title"])}</h2><p>{text(stamp(event["created_at"]))} · {text(event["review_action"] or "Awaiting review")}</p>'
        )
        if d.get("withheld"):
            parts.append(
                "<p>Source access changed. Interpretation, figures and source excerpts are withheld.</p></section>"
            )
            continue
        if event["kind"] == "idea":
            parts += [
                f'<p>Saved revision {d["revision"]}: {text(d["question"])}</p>',
                f'<blockquote>{text(d["reasoning"])}</blockquote>',
                f'<p>Source cutoff {text(stamp(d["cutoff"]))} · {text(d["model"])} · {text(d["prompt_version"])}</p>',
                f'<p>Check focus: {text(d["purpose_label"])}</p>',
                f'<p>{text(d["selection_summary"])}</p>',
            ]
            if d.get("earlier_method"):
                parts.append(
                    "<p>Saved with an earlier method. Original interpretation and evidence are unchanged; later conversation context was not added to this check.</p>"
                )
            items = d["items"]
            sources = {s["id"]: s for s in d["sources"]}
        elif event["kind"] == "company":
            parts.append(f'<p>{text(d["payload"]["reason"])}</p>')
            for label, limits in d.get("source_limits", {}).items():
                if limits:
                    parts.append(
                        f'<p>{text(label.title())} sample: {text(limits["notice"])}</p>'
                    )
            items = d["payload"].get("items", [])
            sources = {s["id"]: s for s in d["sources"]}
        else:
            parts += [
                f'<p>Saved revision {d["revision"]}: {text(d["question"])}</p>',
                f'<blockquote>{text(d["reasoning"])}</blockquote>',
            ]
            for item in d["details"].get("affected_conditions", []):
                parts.append(
                    f'<p>{text(item["metric"].replace("_"," "))}: {text(item["before"])} → {text(item["after"])} percent · {text(outcome_label(item))}</p>'
                )
            for item in d["details"].get("affected_reports", []):
                from .monitoring.report_expectations import (
                    explanation as report_explanation,
                )

                parts.append(f"<p>{text(report_explanation(item))}</p>")
            for item in d["details"].get("affected_events", []):
                parts.append(
                    f'<p>{text(item["description"])}: {text(item.get("before") or "Not checked")} → {text(item["after"])}</p>'
                )
            parts.append(
                "<p>Open this exact assessment in the local app to inspect the full source register.</p>"
            )
            parts.append(
                f'<a href="http://127.0.0.1:8841/?company={text(event["instrument_id"])}&amp;view=history&amp;evaluation={text(d["evaluation_id"])}">Open saved assessment</a>'
            )
            items = []
            sources = {}
        for item in items:
            source = sources.get(item["source_id"])
            if not source:
                continue
            label = item.get("relation", item.get("sentiment", "Source connection"))
            if label == "risk":
                label = "Risk to investigate"
            elif label == "answers":
                label = "Evidence toward your question (research remains open)"
            elif label == "possible_link":
                label = "Possible connection (no alert)"
            parts.append(
                f'<h3>{text(label)} · {text(source["title"])}</h3><p>{text(item.get("explanation", ""))}</p>'
            )
            if item.get("connection_basis_label"):
                parts.append(f'<p>{text(item["connection_basis_label"])}</p>')
            if item.get("answer_excerpt"):
                parts.append(
                    f'<p>{text(item["answer_kind_label"])}</p><p>Question addressed: {text(item["answer_target"])}</p><p>Answer evidence · original wording:</p><blockquote>{text(item["answer_excerpt"])}</blockquote>'
                )
            if item.get("missing_evidence"):
                parts.append(
                    f'<p>What would establish the link: {text(item["missing_evidence"])}</p>'
                )
            if item.get("question_quote"):
                parts.append(
                    f'<p>Your saved question:</p><blockquote>{text(item["question_quote"])}</blockquote>'
                )
            if item.get("evidence_policy"):
                parts.append(
                    "<p>Wording used for this label (AI-selected original excerpts):</p>"
                )
            for citation in item.get("citations", []):
                parts.append(f'<blockquote>{text(citation["quote"])}</blockquote>')
            if item.get("previous_citations"):
                parts.append("<p>Earlier view identified in the same post:</p>")
                for citation in item["previous_citations"]:
                    parts.append(f'<blockquote>{text(citation["quote"])}</blockquote>')
                parts.append(
                    "<p>The earlier/current distinction is an AI interpretation.</p>"
                )
            parts.append(
                parent_context_html(
                    item.get("conversation"),
                    purpose="connection" if event["kind"] == "idea" else "label",
                )
            )
            if event["kind"] == "company":
                for comparison in d["payload"].get("coverage_links", []):
                    if comparison["source_id"] != item["source_id"]:
                        continue
                    earlier = sources.get(comparison["reference_source_id"])
                    label = {
                        "contradicts": "Conflicting reports",
                        "adds_detail": "Added detail",
                    }.get(comparison["relation"], "Changed wording")
                    parts.append(
                        f'<h4>{text(label)} · compared reporting</h4><p>{text(comparison["explanation"])}</p>'
                    )
                    if not comparison.get("explanation_policy"):
                        parts.append(
                            "<p>Earlier AI-written summary. Check each report for the details it supports.</p>"
                        )
                    if comparison.get("review_note"):
                        parts.append(f'<p>{text(comparison["review_note"])}</p>')
                    parts.append(
                        "<p>This comparison does not establish which claim is true or whether the earlier report was formally corrected.</p><p>New report:</p>"
                    )
                    for citation in comparison["citations"]:
                        parts.append(
                            f'<blockquote>{text(citation["quote"])}</blockquote>'
                        )
                    if earlier:
                        parts.append(
                            f'<p>Earlier report: {text(earlier["title"])} · {text(stamp(earlier["published_at"]))}</p>'
                        )
                    for citation in comparison["reference_citations"]:
                        parts.append(
                            f'<blockquote>{text(citation["quote"])}</blockquote>'
                        )
                    if earlier:
                        prior_url = earlier["url"]
                        parsed_prior = urlsplit(prior_url)
                        if (
                            parsed_prior.scheme == "https"
                            and parsed_prior.hostname
                            and not parsed_prior.username
                            and not parsed_prior.password
                        ):
                            parts.append(
                                f'<p><a href="{text(prior_url)}" rel="noopener noreferrer">Earlier source</a></p>'
                            )
            url = source["url"]
            parsed = urlsplit(url)
            if (
                parsed.scheme == "https"
                and parsed.hostname
                and not parsed.username
                and not parsed.password
            ):
                parts.append(
                    f'<p><a href="{text(url)}" rel="noopener noreferrer">Original source</a></p>'
                )
        parts.append("</section>")
    html = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\';style-src \'unsafe-inline\';base-uri \'none\';form-action \'none\'"><title>Private research review</title><style>body{font:16px/1.55 system-ui;max-width:900px;margin:36px auto;padding:0 20px;color:#19211f}section{border-top:1px solid #aaa;margin-top:24px;padding-top:12px}blockquote{border-left:3px solid #6a8565;padding:8px 16px;margin:10px 0;white-space:pre-wrap}p,h2,h3{overflow-wrap:anywhere}</style></head><body>'
        + "".join(parts)
        + "</body></html>"
    )
    return (
        "thesis-research-review-" + report["cutoff"].strftime("%Y%m%d") + ".html",
        html,
    )
