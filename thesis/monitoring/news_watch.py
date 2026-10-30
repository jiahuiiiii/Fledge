"""Opt-in local news/social watch; immutable alerts, one shared model ledger."""

import logging
import re
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from uuid import uuid4
from psycopg.types.json import Jsonb
from thesis.db import transaction, one, rows
from thesis.research import sentiment, social, market, coverage, reporting_basis, source_observations
from thesis.research.sentiment_context import changed_common_context
from . import watch_history, watch_lanes

logger = logging.getLogger(__name__)
SGT = ZoneInfo("Asia/Singapore")
# A failed scheduled check is tried again soon instead of waiting a full
# interval: up to QUICK_RETRIES consecutive failures, then the normal schedule.
QUICK_RETRIES = 2
RETRY_MINUTES = 10
BUSY_RETRY_MINUTES = 3  # the company's reading was running elsewhere


class WatchStopped(Exception):
    pass


def configure(
    owner,
    iid,
    enabled,
    interval=60,
    now=None,
    match_idea=None,
    include_context=None,
    idea_purpose=None,
):
    if type(enabled) is not bool or interval not in (60, 240):
        raise ValueError("Choose an hourly or four-hour watch.")
    if not sentiment.market_brief.company_for(iid):
        raise ValueError("Choose a supported company.")
    now = now or datetime.now(timezone.utc)
    with transaction(owner) as c:
        old = one(
            c,
            "SELECT * FROM news_watches WHERE owner_id=%s AND instrument_id=%s FOR UPDATE",
            (owner, iid),
        )
        if match_idea is not None and type(match_idea) is not bool:
            raise ValueError("Choose company updates or saved-idea alerts.")
        if include_context is not None and type(include_context) is not bool:
            raise ValueError("Choose whether to check original reply context.")
        if idea_purpose is not None and idea_purpose not in ("reasoning", "question", "both"):
            raise ValueError(
                "Choose answers to your question or connections to your reasoning."
            )
        purpose = (
            idea_purpose
            if idea_purpose is not None
            else (old["idea_purpose"] if old else "reasoning")
        )
        context = (
            include_context
            if include_context is not None
            else bool(old and old["include_context"])
        )
        matched = (
            match_idea if match_idea is not None else bool(old and old["match_idea"])
        )
        if enabled and not (old and old["enabled"]):
            # Watches follow the five-company watchlist limit.
            from ..watchlist import LIMIT
            c.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
                (f"watch-limit:{owner}",),
            )
            active = one(
                c,
                "SELECT count(*) n FROM news_watches WHERE owner_id=%s AND enabled AND instrument_id<>%s",
                (owner, iid),
            )["n"]
            if active >= LIMIT:
                raise ValueError(
                    f"You can watch up to {LIMIT} companies. Turn off another watch first."
                )
        baseline = one(
            c,
            sentiment.LATEST_SQL,
            (iid,),
        )
        c.execute(
            "INSERT INTO news_watches(owner_id,instrument_id,enabled,interval_minutes,next_check_at,baseline_id) VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(owner_id,instrument_id) DO UPDATE SET enabled=excluded.enabled,interval_minutes=excluded.interval_minutes,next_check_at=excluded.next_check_at,baseline_id=COALESCE(news_watches.baseline_id,excluded.baseline_id),claim_token=NULL,lease_until=NULL,error=NULL",
            (
                owner,
                iid,
                enabled,
                interval,
                now + timedelta(minutes=interval),
                baseline["id"] if baseline else None,
            ),
        )
        actual = one(
            c,
            "SELECT a.* FROM news_watches w JOIN sentiment_analyses a ON a.id=w.baseline_id WHERE w.owner_id=%s AND w.instrument_id=%s",
            (owner, iid),
        )
        if actual:
            remember(c, owner, iid, actual)
        if matched and enabled:
            from thesis.research import idea_alerts

            if (
                not old
                or not old["match_idea"]
                or not old["enabled"]
                or old["idea_purpose"] != purpose
            ):
                idea_alerts.start(c, owner, iid, baseline, purpose=purpose)
        c.execute(
            "UPDATE news_watches SET match_idea=%s,include_context=%s,idea_purpose=%s WHERE owner_id=%s AND instrument_id=%s",
            (matched, context, purpose, owner, iid),
        )
        c.execute("DELETE FROM fast_watch_state WHERE owner_id=%s AND instrument_id=%s", (owner, iid))
    return dict(
        enabled=enabled,
        interval_minutes=interval,
        match_idea=matched,
        idea_purpose=purpose,
        include_context=context,
    )


def remember(conn, owner, iid, analysis):
    for source in analysis["packet"]["sources"]:
        for key in coverage.observed_keys(analysis, source):
            conn.execute(
                "INSERT INTO watch_seen_sources(owner_id,instrument_id,channel,content_hash) VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (owner, iid, source["channel"], key),
            )


def changes(previous, current, seen=None):
    """Count a sample shift, not a change in the market or a verified event."""
    # Installing/changing the batch pipeline establishes a quiet baseline.
    # Historical deterministic rendering-policy changes keep their old semantics.
    if (
        previous['result'].get('batching', {}).get('policy') != current['result'].get('batching', {}).get('policy')
    ):
        return []
    old_sources = {
        (s["channel"], key)
        for s in previous["packet"]["sources"]
        for key in coverage.observed_keys(previous, s)
    }
    source_map = {s["id"]: s for s in current["packet"]["sources"]}
    fresh = [
        i
        for i in current["result"]["items"]
        if not (
            {
                (i["channel"], key)
                for key in coverage.keys(current, source_map[i["source_id"]])
            }
            & old_sources
        )
        and not any(
            (i["channel"], key) in (seen or set())
            for key in coverage.keys(current, source_map[i["source_id"]])
        )
        and i["relevance"] == "relevant"
    ]
    if not fresh:
        return []
    output = []
    old = previous["result"]["summary"]
    new = current["result"]["summary"]
    scopes = [("news", None)]
    if old.get("social_platforms") or new.get("social_platforms"):
        scopes += [("social", p) for p in ("reddit", "hackernews", "x")]
    else:
        scopes.append(("social", None))
    for channel, platform in scopes:
        before = (
            old.get("social_platforms", {}).get(platform) if platform else old[channel]
        )
        after = (
            new.get("social_platforms", {}).get(platform) if platform else new[channel]
        )
        selected = [
            i
            for i in fresh
            if i["channel"] == channel
            and (
                not platform
                or source_map[i["source_id"]].get("platform", "reddit") == platform
            )
        ]
        if (
            before
            and after
            and selected
            and not changed_common_context(
                previous["packet"], current["packet"], channel, platform
            )
            and all(
                previous["result"].get(key)
                and previous["result"].get(key) == current["result"].get(key)
                for key in ("summary_policy", "prompt_version", "model")
            )
            and before["tone"] in ("positive leaning", "negative leaning")
            and after["tone"] in ("positive leaning", "negative leaning")
            and before["tone"] != after["tone"]
        ):
            output.append(
                dict(
                    kind="sentiment",
                    channel=channel,
                    platform=platform,
                    title=(
                        "News framing"
                        if channel == "news"
                        else (
                            "Hacker News comments"
                            if platform == "hackernews"
                            else "X posts" if platform == "x" else "Reddit discussion"
                        )
                    )
                    + " changed in the selected sample",
                    before=before,
                    after=after,
                    items=selected,
                    reason="Both samples from this source contain at least three interpretable text groups and a majority changed direction. This is a sample-based review rule, not a market-wide measure.",
                )
            )
    adverse = [
        i
        for i in fresh
        if i["channel"] == "news"
        and reporting_basis.adverse(i)
    ]
    # A clarification can be neutral or favourable. Retain cited changes to a
    # report actually seen by this watch even when no tone reversal occurs.
    known = old_sources | (seen or set())
    all_sources = {
        s["id"]: s
        for s in current["packet"]["sources"]
        + current["packet"].get("comparison_sources", [])
    }
    fresh_news = {i["source_id"] for i in fresh if i["channel"] == "news"}
    changed_links = []
    unchanged_reporting_ids = set()
    by_id = {i["source_id"]: i for i in fresh}
    for link in current["result"].get("coverage_links", []):
        prior = all_sources.get(link["reference_source_id"])
        if (
            link["source_id"] in fresh_news
            and prior
            and ("news", "content:" + prior["content_hash"]) in known
            and coverage.change_for_review(link)
            and reporting_basis.eligible(by_id[link["source_id"]])
        ):
            item = by_id[link["source_id"]]
            if coverage.reporting_changed(item, prior):
                changed_links.append(link)
            else:
                unchanged_reporting_ids.add(link["source_id"])
        if (link["source_id"] in by_id and prior
            and ("news", "content:" + prior["content_hash"]) in known
            and not coverage.reporting_changed(by_id[link["source_id"]], prior)):
            unchanged_reporting_ids.add(link["source_id"])
    reporting_ids = {i["source_id"] for i in adverse if i["source_id"] not in unchanged_reporting_ids} | {
        link["source_id"] for link in changed_links
    }
    if reporting_ids:
        output.append(
            dict(
                kind="new_reporting",
                channel="news",
                title=(
                    "New reporting changes an earlier story"
                    if changed_links
                    else "New adverse or mixed company reporting"
                ),
                items=[i for i in fresh if i["source_id"] in reporting_ids],
                coverage_links=changed_links,
                reason=(
                    "A newly analysed report adds detail, conflicts with earlier reporting or contains changed numeric/status wording about a story this watch has already seen. Compare both sources: a linked change is an interpretation, not a verified correction. Any separate adverse reports in this sample are grouped here too."
                    if changed_links
                    else "Newly analysed company news describes a specific development with an adverse or mixed effect in the supplied evidence. A rumour remains unconfirmed; this does not establish that your investment idea has failed."
                ),
            )
        )
    # One grouped sentiment alert can cover both channels without duplicate delivery.
    shifts = [x for x in output if x["kind"] == "sentiment"]
    return (
        [
            dict(
                kind="sentiment",
                title="Sentiment sample changed",
                shifts=shifts,
                items=[i for x in shifts for i in x["items"]],
                reason="Compare news and social discussion separately with their previous sampled coverage.",
            )
        ]
        if shifts
        else []
    ) + [x for x in output if x["kind"] != "sentiment"]


def publish(owner, iid, analysis_id, *, claim_token=None, now=None):
    now = now or datetime.now(timezone.utc)
    with transaction(owner) as c:
        watch = one(
            c,
            "SELECT * FROM news_watches WHERE owner_id=%s AND instrument_id=%s FOR UPDATE",
            (owner, iid),
        )
        if not watch_lanes.active(c, owner, iid, claim_token, now, watch=watch):
            return 0
        current = one(
            c,
            "SELECT * FROM sentiment_analyses WHERE id=%s AND instrument_id=%s",
            (analysis_id, iid),
        )
        if not current:
            raise ValueError("Sentiment analysis does not match this company.")
        if current["packet"].get("social_lookback_days", 7) != 7:
            return 0
        # Alerts compare whole samples. A reading that left sources unread would
        # count as a sample shift, so it neither alerts nor becomes the baseline.
        if current["packet"].get("held_sources"):
            return 0
        previous = (
            one(
                c,
                "SELECT * FROM sentiment_analyses WHERE id=%s AND instrument_id=%s",
                (watch["baseline_id"], iid),
            )
            if watch["baseline_id"]
            else None
        )
        if previous and previous["packet"].get("social_lookback_days", 7) != 7:
            previous = None
        # Late/older results must never roll a watch backwards.
        if previous and datetime.fromisoformat(
            current["packet"]["cutoff"]
        ) <= datetime.fromisoformat(previous["packet"]["cutoff"]):
            return 0
        if sentiment.present(c, current).get("withheld"):
            raise ValueError("Sentiment source access changed; analysis withheld.")
        if previous and sentiment.present(c, previous).get("withheld"):
            previous = None
        seen = {
            (s["channel"], s["content_hash"])
            for s in rows(
                c,
                "SELECT channel,content_hash FROM watch_seen_sources WHERE owner_id=%s AND instrument_id=%s",
                (owner, iid),
            )
        }
        alerts = (
            changes(previous, current, seen)
            if previous and not watch["match_idea"]
            else []
        )
        from . import alert_routing
        proposals=(alert_routing.important_reporting(previous,current,seen)
                   if alert_routing.enabled() and not watch['match_idea'] else [])
        idea = one(
            c,
            "SELECT v.id,v.question,v.reasoning,v.revision FROM thesis_versions v JOIN theses t ON t.id=v.thesis_id AND t.owner_id=v.owner_id AND t.revision=v.revision WHERE t.owner_id=%s AND t.instrument_id=%s AND t.status<>'archived'",
            (owner, iid),
        )
        for alert in alerts+proposals:
            alert.update(
                cutoff=current["packet"]["cutoff"],
                previous_cutoff=previous["packet"]["cutoff"],
                saved_idea=dict(idea) if idea else None,
            )
            if idea:
                alert["saved_idea"]["id"] = str(idea["id"])
            c.execute(
                "INSERT INTO research_alerts(id,owner_id,instrument_id,kind,current_id,previous_id,version_id,payload,created_at,preview) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,now(),%s) ON CONFLICT(owner_id,instrument_id,current_id,kind) DO NOTHING",
                (
                    uuid4(),
                    owner,
                    iid,
                    alert["kind"],
                    current["id"],
                    previous["id"],
                    idea["id"] if idea else None,
                    Jsonb(alert),
                    alert['kind']=='important_reporting' and not alert_routing.live_active(now),
                ),
            )
        if claim_token is not None and watch["claim_token"] != claim_token:
            c.execute("UPDATE news_watches SET baseline_id=%s WHERE owner_id=%s AND instrument_id=%s",
                      (current["id"], owner, iid))
        else:
            c.execute(
                "UPDATE news_watches SET baseline_id=%s,last_check_at=%s,error=NULL WHERE owner_id=%s AND instrument_id=%s",
                (current["id"], now, owner, iid),
            )
        remember(c, owner, iid, current)
        return len(alerts)+len(proposals)


def cited(sources, items, links=()):
    """Only the sources an alert can display: its items, their citations and links.

    Alert cards, the inbox and exports look sources up by these ids alone.
    """
    wanted = {i.get("source_id") for i in items}
    wanted |= {c.get("source_id") for i in items for c in i.get("citations") or []}
    wanted |= {l.get(k) for l in links for k in ("source_id", "reference_source_id")}
    return [s for s in sources if s["id"] in wanted]


def _shown_sample(reading, channel, platform):
    return (platform or channel) not in reading.get("withheld_summaries", [])


def visible_payload(payload, current, previous):
    """The alert parts both readings still show, or None to withhold the alert.

    An item stays only while the current reading still shows its own
    interpretation; a tone shift also needs both of its saved totals.
    """
    if current["withheld"] or previous["withheld"]:
        return None
    shown = {i["source_id"] for i in current["items"]}
    links = {(l["source_id"], l["reference_source_id"], l["relation"]) for l in current.get("coverage_links", [])}
    items = payload.get("items", [])
    if any((l["source_id"], l["reference_source_id"], l["relation"]) not in links
           for l in payload.get("coverage_links", [])):
        # A linked report change is one claim; it is not shown half-evidenced.
        return None
    if payload.get("kind") == "sentiment":
        shifts = [
            shift for shift in payload.get("shifts", [])
            if _shown_sample(current, shift["channel"], shift.get("platform"))
            and _shown_sample(previous, shift["channel"], shift.get("platform"))
            and all(i["source_id"] in shown for i in shift["items"])
        ]
        if len(shifts) == len(payload.get("shifts", [])) and all(i["source_id"] in shown for i in items):
            return payload
        kept = [i for shift in shifts for i in shift["items"]]
        if not shifts or not kept:
            return None
        return dict(payload, shifts=shifts, items=kept, withheld_items=len(items) - len(kept))
    kept = [i for i in items if i["source_id"] in shown]
    if len(kept) == len(items):
        return payload
    if not kept:
        return None
    return dict(payload, items=kept, withheld_items=len(items) - len(kept))


def list_alerts(conn, owner, ids=None, *, previous=True, detail_instrument=None, details=True):
    data = rows(
        conn,
        "SELECT a.*,i.symbol,i.name,r.action review_action FROM research_alerts a JOIN instruments i ON i.id=a.instrument_id LEFT JOIN research_alert_reviews r ON r.owner_id=a.owner_id AND r.alert_id=a.id WHERE a.owner_id=%s AND (%s::uuid[] IS NULL OR a.id=ANY(%s::uuid[])) ORDER BY a.created_at DESC,a.id DESC LIMIT 100",
        (owner, ids, ids),
    )
    result = []
    # A company page details only its own alerts. Others need only their
    # review status for the updates badge; no evidence is sent for them.
    # details=False sends review status only, for every alert (no readings load).
    def status_only(a):
        return not details or (detail_instrument is not None and str(a["instrument_id"]) != str(detail_instrument))

    detailed = [a for a in data if not status_only(a)]
    # Consecutive alerts share readings; build each one once for this request.
    wanted = list({str(a[k]) for a in detailed for k in ("current_id", "previous_id")})
    records = {str(r["id"]): r for r in rows(conn, "SELECT * FROM sentiment_analyses WHERE id=ANY(%s::uuid[])", (wanted,))} if wanted else {}
    presented = {}

    def shown(identity):
        identity = str(identity)
        if identity not in presented:
            presented[identity] = sentiment.present(conn, records.get(identity), partial=True)
        return presented[identity]

    for a in data:
        if status_only(a):
            result.append(dict(id=str(a["id"]), instrument_id=str(a["instrument_id"]), symbol=a["symbol"], name=a["name"],
                               created_at=a["created_at"].isoformat(), review_action=a["review_action"],
                               preview=a.get("preview", False), status_only=True))
            continue
        visible = shown(a["current_id"])
        prior = shown(a["previous_id"])
        payload = visible_payload(a["payload"], visible, prior) if visible and prior else None
        withheld = payload is None
        result.append(
            dict(
                id=str(a["id"]),
                instrument_id=str(a["instrument_id"]),
                symbol=a["symbol"],
                name=a["name"],
                created_at=a["created_at"].isoformat(),
                review_action=a["review_action"],
                withheld=withheld,
                preview=a.get('preview',False),
                payload={} if withheld else payload,
                sources=[] if withheld else cited(visible["sources"], payload.get("items", []), payload.get("coverage_links", [])),
                source_limits=(
                    {}
                    if withheld
                    else {
                        "current": visible.get("coverage", {}).get("input_limits"),
                        "previous": prior.get("coverage", {}).get("input_limits"),
                    }
                ),
                # Lists omit the large earlier sample; previous_sample() returns it
                # on request through these same access and withdrawal checks.
                previous_items=None if not previous else [] if withheld else prior["items"],
                previous_sources=None if not previous else [] if withheld else cited(prior["sources"], prior["items"]),
            )
        )
    return result


def previous_sample(owner, alert_id):
    from thesis.service import Missing
    with transaction(owner, consistent=True) as conn:
        found = list_alerts(conn, owner, ids=[str(alert_id)])
    if not found:
        raise Missing("This alert is unavailable.")
    alert = found[0]
    return dict(id=alert["id"], withheld=alert["withheld"],
                previous_items=alert["previous_items"], previous_sources=alert["previous_sources"])


def review(owner, alert_id, action):
    from thesis.service import Missing, Conflict

    if action not in ("reviewed", "unresolved"):
        raise ValueError("Choose a review action.")
    with transaction(owner) as c:
        if not one(
            c,
            "SELECT id FROM research_alerts WHERE owner_id=%s AND id=%s",
            (owner, alert_id),
        ):
            raise Missing("Alert not found.")
        c.execute(
            "INSERT INTO research_alert_reviews VALUES(%s,%s,%s,now()) ON CONFLICT DO NOTHING",
            (owner, alert_id, action),
        )
        record = one(
            c,
            "SELECT action FROM research_alert_reviews WHERE owner_id=%s AND alert_id=%s",
            (owner, alert_id),
        )
        if record["action"] != action:
            raise Conflict("This alert already has a different recorded review.")
    return {"action": action}


# App-authored sentiment stops, matched whole so no model or source text can
# pass. Before 20 Oct 2026 these showed as "an unexpected error (ValueError)".
APP_STOPS = tuple(re.compile(p) for p in (
    r"A saved (tone|event|duplicate) task did not pass its evidence checks\. No automatic paid retry\.",
    r"The (tone|event|duplicate) task stopped\. Paid results remain saved; no combined reading or automatic retry\.",
    r"One complete source and (required context|its topic) exceed the (task|quick-check) limit\. No (task|quick check) was sent\.",
    r"Every source must be read or reused exactly once\.",
    r"No saved failed task is ready for smaller-batch recovery\. No new task was sent\.",
))


def app_stop(exc):
    """A plain ValueError whose whole text is one of the app's own stop messages."""
    return type(exc) is ValueError and any(p.fullmatch(str(exc)) for p in APP_STOPS)


def failure_reason(exc):
    """A short, readable reason that never echoes raw provider or exception text.

    Only app-authored messages (spending blocks, conflicts) are shown verbatim.
    """
    from thesis.providers.ledger import BudgetBlocked
    from thesis.providers.settings import ProviderConfigError
    from thesis.service import Conflict

    # Sentiment batching raises app-authored ValueErrors that say which batch
    # stopped and why; pydantic ValidationError (also a ValueError) can echo
    # model text, so only these known prefixes are shown verbatim.
    batch = isinstance(exc, ValueError) and type(exc) is ValueError and str(exc).startswith(
        ("Batch ", "A saved batch ")
    )
    if (isinstance(exc, (BudgetBlocked, Conflict, ProviderConfigError)) or batch or app_stop(exc)) and str(exc).strip():
        text = " ".join(str(exc).split())[:400]
        return text if text.endswith((".", "!", "?")) else text + "."
    if "timeout" in type(exc).__name__.lower():
        return "a source or AI request timed out."
    return f"an unexpected error ({type(exc).__name__})."


@source_observations.scoped
def run_once(
    owner,
    *,
    now=None,
    market_refresh=None,
    social_refresh=None,
    analyzer=None,
    idea_analyzer=None,
    event_analyzer=None,
    context_fetcher=None,
    lane=None,
):
    from thesis.service import Conflict
    from . import watch_context

    supplied_clock = now
    now = now or datetime.now(timezone.utc)
    split_lanes = watch_lanes.enabled()
    if lane == "fast" and not split_lanes:
        return False
    lane = "fast" if lane == "fast" else "slow" if split_lanes else "combined"
    token = uuid4()
    with transaction(owner) as c:
        watch = watch_lanes.claim_fast(c, owner, now, token) if lane == "fast" else one(
            c,
            "SELECT * FROM news_watches WHERE owner_id=%s AND enabled AND next_check_at<=%s AND (lease_until IS NULL OR lease_until<=%s) ORDER BY next_check_at FOR UPDATE SKIP LOCKED LIMIT 1",
            (owner, now, now),
        )
        if not watch:
            return False
        iid = str(watch["instrument_id"])
        if lane != "fast":
            c.execute(
                "UPDATE news_watches SET claim_token=%s,lease_until=%s,next_check_at=%s WHERE owner_id=%s AND instrument_id=%s",
                (token, now + timedelta(minutes=15),
                 now + timedelta(minutes=watch["interval_minutes"]), owner, iid),
            )
        watch_history.start(c, owner, dict(watch, lane=lane), token, now, now + timedelta(minutes=15))
    source_observations.CHECK.set(token)
    message = None
    status = "completed"
    skipped = None
    stage = "company news"
    analysis_id = idea_check_id = None
    details = {
        "lane": lane,
        "market": "not_run",
        "social": "not_run",
        "analysis": "not_run",
        "private": "not_run",
        "company_alerts": 0,
        "idea_alerts": 0,
    }
    try:
        watch_context.require_active(owner, iid, token, supplied_clock)
        if lane == "slow":
            details["market"] = "separate_fast_lane"
        else:
            try:
                (market_refresh or market.refresh)(iid)
                details["market"] = "checked"
            except Conflict:
                details["market"] = "shared_recent_check"
            except ValueError:
                details["market"] = "failed"
        if market_refresh is None and lane != "slow":
            from thesis.research import source_hub
            watch_context.require_active(owner, iid, token, supplied_clock)
            details["publisher_feeds"] = source_hub.refresh_rss(iid)
            watch_context.require_active(owner, iid, token, supplied_clock)
            try:
                details["alpha_vantage"] = source_hub.refresh(iid, "alpha_vantage")
            except Conflict:
                details["alpha_vantage"] = {"status": "cached"}
        stage = "social sources"
        watch_context.require_active(owner, iid, token, supplied_clock)
        if lane != "fast":
            try:
                social_result = social_refresh() if social_refresh else social.refresh_company(iid)
                details["social"] = "checked"
                if isinstance(social_result,dict) and social_result.get("x"):
                    details["x"] = social_result["x"]
            except Conflict:
                details["social"] = "shared_recent_check"
        else:
            details["social"] = "separate_slow_lane"
        with transaction(owner) as c:
            active = watch_lanes.active(c, owner, iid, token, supplied_clock or datetime.now(timezone.utc))
        if active:
            if watch.get("include_context") and lane != "fast":
                stage = "original reply context"
                watch_context.collect(
                    owner,
                    iid,
                    token,
                    details,
                    fetcher=context_fetcher,
                    now=supplied_clock,
                )
            watch_context.require_active(owner, iid, token, supplied_clock)
            if watch.get("event_version_id"):
                from thesis.monitoring import event_watch

                stage = "approved event analysis"
                checked_event = (event_analyzer or event_watch.run)(
                    owner, iid, watch["event_version_id"], token
                )
                details["events"] = checked_event["status"]
                details["event_review_id"] = checked_event.get("id")
                details["event_snapshot_id"] = checked_event.get("applied_snapshot_id")
                with transaction(owner) as c:
                    still_active = watch_lanes.active(c, owner, iid, token, supplied_clock or datetime.now(timezone.utc))
                if not still_active:
                    raise WatchStopped()
            stage = "sentiment analysis"
            watch_context.require_active(owner, iid, token, supplied_clock)
            # Recheck saved responses for free; paid retries require a manual action.
            record = analyzer(iid) if analyzer else sentiment.generate(
                iid, progress=lambda _: watch_context.require_active(owner, iid, token, supplied_clock, renew=True),
                retry_failed=False,
            )
            analysis_id = record["id"]
            details["analysis"] = "completed"
            if record.get("held_sources"):
                details["held_sources"] = record["held_sources"]["count"]
            stage = "company alert publication"
            watch_context.require_active(owner, iid, token, supplied_clock)
            details["company_alerts"] = publish(
                owner, iid, record["id"], claim_token=token, now=supplied_clock
            )
            if watch["match_idea"]:
                from thesis.research import idea_alerts

                stage = "saved-reasoning analysis"
                watch_context.require_active(owner, iid, token, supplied_clock)
                run_idea = idea_analyzer or idea_alerts.generate
                if watch.get("idea_purpose") == "both":
                    # One private check per focus, on the same new sources: the
                    # first leaves them unseen until the second has read them.
                    statuses = {}
                    for focus in ("reasoning", "question"):
                        watch_context.require_active(owner, iid, token, supplied_clock)
                        try:
                            checked = run_idea(
                                owner,
                                iid,
                                record["id"],
                                automatic=True,
                                claim_token=token,
                                purpose=focus,
                                keep_unseen=focus == "reasoning",
                            )
                        except ValueError:
                            if focus != "reasoning":
                                raise
                            statuses[focus] = "skipped"
                            continue
                        statuses[focus] = checked["status"]
                        idea_check_id = checked.get("id") or idea_check_id
                    details["private"] = "completed"
                    details["idea_statuses"] = statuses
                    details["idea_status"] = statuses["question"]
                else:
                    checked = run_idea(
                        owner, iid, record["id"], automatic=True, claim_token=token
                    )
                    details["private"] = "completed"
                    details["idea_status"] = checked["status"]
                    idea_check_id = checked.get("id")
        else:
            status = "stopped"
    except WatchStopped:
        status = "stopped"
    except Exception as exc:
        from thesis.providers.ledger import BudgetBlocked, WakePaused
        status = "failed"
        busy = isinstance(exc, Conflict) and "already running" in str(exc)
        # Neither is a failure: the other lane is reading this company, or the
        # computer has just woken and nothing was sent. Both try again shortly.
        skipped = "other_lane_busy" if busy else "computer_woke" if isinstance(exc, WakePaused) else None
        details["failed_stage"] = stage
        # Keep the actual reason: a generic message hid a two-day AI block
        # (12-13 Oct 2026) behind hourly "did not complete" results.
        details["failure_reason"] = failure_reason(exc)
        if skipped:
            status = "stopped"
            details["skip_reason"] = skipped
        if skipped or isinstance(exc, BudgetBlocked) or app_stop(exc):
            # An app-authored reason says it all; a traceback per check only hides it.
            logger.warning("Scheduled %s check stopped at %s: %s", lane, stage, details["failure_reason"])
        else:
            logger.exception("Scheduled watch check failed at %s", stage)
        message = (
            f"The scheduled update stopped at {stage}: {details['failure_reason']} "
            "Saved research is still available. No automatic paid retry was made."
        )
    with transaction(owner) as c:
        active = watch_lanes.active(c, owner, iid, token, supplied_clock or datetime.now(timezone.utc))
        if status == "completed" and not active:
            status = "stopped"
        watch_history.finish(
            c, owner, token, status, details, analysis_id, idea_check_id, supplied_clock
        )
        finished = supplied_clock or datetime.now(timezone.utc)
        retry_at = None
        if (status == "failed" or skipped) and active:
            recent = rows(
                c,
                "SELECT r.status,r.details->>'skip_reason' skip FROM watch_check_results r JOIN watch_checks w ON w.id=r.check_id WHERE w.owner_id=%s AND w.instrument_id=%s AND w.lane=%s ORDER BY w.started_at DESC LIMIT %s",
                (owner, iid, lane, QUICK_RETRIES + 1),
            )
            # Skips count too: each retry fetches sources again, which have daily limits.
            failures = next((n for n, r in enumerate(recent) if r["status"] != "failed" and not r["skip"]), len(recent))
            if failures <= QUICK_RETRIES:
                retry_at = finished + timedelta(minutes=BUSY_RETRY_MINUTES if skipped else RETRY_MINUTES)
                message = message.replace(
                    "No automatic paid retry was made.",
                    f"Trying again automatically at {retry_at.astimezone(SGT):%H:%M} SGT "
                    "(saved batches are reused).",
                )
        table = "fast_watch_state" if lane == "fast" else "news_watches"
        c.execute(
            f"UPDATE {table} SET lease_until=NULL,last_check_at=%s,error=%s,next_check_at=LEAST(next_check_at,COALESCE(%s,next_check_at)) WHERE owner_id=%s AND instrument_id=%s AND claim_token=%s",
            (finished, message, retry_at, owner, iid, token),
        )
    return True
