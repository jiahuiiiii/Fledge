"""Opt-in local news/social watch; immutable alerts, one shared model ledger."""

from datetime import datetime, timezone, timedelta
from uuid import uuid4
from psycopg.types.json import Jsonb
from thesis.db import transaction, one, rows
from thesis.research import sentiment, social, market, coverage, reporting_basis
from thesis.research.sentiment_context import changed_common_context
from . import watch_history


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
        if idea_purpose is not None and idea_purpose not in ("reasoning", "question"):
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
        baseline = one(
            c,
            "SELECT * FROM sentiment_analyses WHERE instrument_id=%s ORDER BY (packet->>'cutoff')::timestamptz DESC,created_at DESC,id DESC LIMIT 1",
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
        if (
            not watch
            or not watch["enabled"]
            or (claim_token is not None and watch["claim_token"] != claim_token)
            or (
                claim_token is not None
                and (not watch["lease_until"] or watch["lease_until"] <= now)
            )
        ):
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
        idea = one(
            c,
            "SELECT v.id,v.question,v.reasoning,v.revision FROM thesis_versions v JOIN theses t ON t.id=v.thesis_id AND t.owner_id=v.owner_id AND t.revision=v.revision WHERE t.owner_id=%s AND t.instrument_id=%s AND t.status<>'archived'",
            (owner, iid),
        )
        for alert in alerts:
            alert.update(
                cutoff=current["packet"]["cutoff"],
                previous_cutoff=previous["packet"]["cutoff"],
                saved_idea=dict(idea) if idea else None,
            )
            if idea:
                alert["saved_idea"]["id"] = str(idea["id"])
            c.execute(
                "INSERT INTO research_alerts VALUES(%s,%s,%s,%s,%s,%s,%s,%s,now()) ON CONFLICT(owner_id,instrument_id,current_id,kind) DO NOTHING",
                (
                    uuid4(),
                    owner,
                    iid,
                    alert["kind"],
                    current["id"],
                    previous["id"],
                    idea["id"] if idea else None,
                    Jsonb(alert),
                ),
            )
        c.execute(
            "UPDATE news_watches SET baseline_id=%s,last_check_at=%s,error=NULL WHERE owner_id=%s AND instrument_id=%s",
            (current["id"], now, owner, iid),
        )
        remember(c, owner, iid, current)
        return len(alerts)


def list_alerts(conn, owner, ids=None):
    data = rows(
        conn,
        "SELECT a.*,i.symbol,i.name,r.action review_action FROM research_alerts a JOIN instruments i ON i.id=a.instrument_id LEFT JOIN research_alert_reviews r ON r.owner_id=a.owner_id AND r.alert_id=a.id WHERE a.owner_id=%s AND (%s::uuid[] IS NULL OR a.id=ANY(%s::uuid[])) ORDER BY a.created_at DESC,a.id DESC LIMIT 100",
        (owner, ids, ids),
    )
    result = []
    for a in data:
        current = one(
            conn, "SELECT * FROM sentiment_analyses WHERE id=%s", (a["current_id"],)
        )
        previous = one(
            conn, "SELECT * FROM sentiment_analyses WHERE id=%s", (a["previous_id"],)
        )
        visible = sentiment.present(conn, current)
        prior = sentiment.present(conn, previous)
        withheld = visible["withheld"] or prior["withheld"]
        result.append(
            dict(
                id=str(a["id"]),
                instrument_id=str(a["instrument_id"]),
                symbol=a["symbol"],
                name=a["name"],
                created_at=a["created_at"].isoformat(),
                review_action=a["review_action"],
                withheld=withheld,
                payload={} if withheld else a["payload"],
                sources=[] if withheld else visible["sources"],
                source_limits=(
                    {}
                    if withheld
                    else {
                        "current": visible.get("coverage", {}).get("input_limits"),
                        "previous": prior.get("coverage", {}).get("input_limits"),
                    }
                ),
                previous_items=[] if withheld else prior["items"],
                previous_sources=[] if withheld else prior["sources"],
            )
        )
    return result


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
):
    from thesis.service import Conflict
    from . import watch_context

    supplied_clock = now
    now = now or datetime.now(timezone.utc)
    token = uuid4()
    with transaction(owner) as c:
        watch = one(
            c,
            "SELECT * FROM news_watches WHERE owner_id=%s AND enabled AND next_check_at<=%s AND (lease_until IS NULL OR lease_until<=%s) ORDER BY next_check_at FOR UPDATE SKIP LOCKED LIMIT 1",
            (owner, now, now),
        )
        if not watch:
            return False
        iid = str(watch["instrument_id"])
        c.execute(
            "UPDATE news_watches SET claim_token=%s,lease_until=%s,next_check_at=%s WHERE owner_id=%s AND instrument_id=%s",
            (
                token,
                now + timedelta(minutes=15),
                now + timedelta(minutes=watch["interval_minutes"]),
                owner,
                iid,
            ),
        )
        watch_history.start(c, owner, watch, token, now, now + timedelta(minutes=15))
    message = None
    status = "completed"
    stage = "company news"
    analysis_id = idea_check_id = None
    details = {
        "market": "not_run",
        "social": "not_run",
        "analysis": "not_run",
        "private": "not_run",
        "company_alerts": 0,
        "idea_alerts": 0,
    }
    try:
        watch_context.require_active(owner, iid, token, supplied_clock)
        try:
            (market_refresh or market.refresh)(iid)
            details["market"] = "checked"
        except Conflict:
            details["market"] = "shared_recent_check"
        except ValueError:
            details["market"] = "failed"
        if market_refresh is None:
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
        try:
            social_result = social_refresh() if social_refresh else social.refresh_company(iid)
            details["social"] = "checked"
            if isinstance(social_result,dict) and social_result.get("x"):
                details["x"] = social_result["x"]
        except Conflict:
            details["social"] = "shared_recent_check"
        with transaction(owner) as c:
            active = one(
                c,
                "SELECT enabled,claim_token,match_idea FROM news_watches WHERE owner_id=%s AND instrument_id=%s",
                (owner, iid),
            )
        if active["enabled"] and active["claim_token"] == token:
            if watch.get("include_context"):
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
                    still_active = one(
                        c,
                        "SELECT enabled,claim_token,lease_until FROM news_watches WHERE owner_id=%s AND instrument_id=%s",
                        (owner, iid),
                    )
                if (
                    not still_active["enabled"]
                    or still_active["claim_token"] != token
                    or not still_active["lease_until"]
                    or still_active["lease_until"] <= datetime.now(timezone.utc)
                ):
                    raise WatchStopped()
            stage = "sentiment analysis"
            watch_context.require_active(owner, iid, token, supplied_clock)
            record = analyzer(iid) if analyzer else sentiment.generate(
                iid, progress=lambda _: watch_context.require_active(owner, iid, token, supplied_clock)
            )
            analysis_id = record["id"]
            details["analysis"] = "completed"
            stage = "company alert publication"
            watch_context.require_active(owner, iid, token, supplied_clock)
            details["company_alerts"] = publish(
                owner, iid, record["id"], claim_token=token, now=supplied_clock
            )
            if active["match_idea"]:
                from thesis.research import idea_alerts

                stage = "saved-reasoning analysis"
                watch_context.require_active(owner, iid, token, supplied_clock)
                checked = (idea_analyzer or idea_alerts.generate)(
                    owner, iid, record["id"], automatic=True, claim_token=token
                )
                details["private"] = "completed"
                details["idea_status"] = checked["status"]
                idea_check_id = checked.get("id")
        else:
            status = "stopped"
    except WatchStopped:
        status = "stopped"
    except Exception:
        status = "failed"
        details["failed_stage"] = stage
        message = "The scheduled source check or analysis did not complete. Check source coverage and the shared AI budget. No automatic paid retry was made."
    with transaction(owner) as c:
        active = one(
            c,
            "SELECT enabled,claim_token FROM news_watches WHERE owner_id=%s AND instrument_id=%s",
            (owner, iid),
        )
        if status == "completed" and (
            not active["enabled"] or active["claim_token"] != token
        ):
            status = "stopped"
        watch_history.finish(
            c, owner, token, status, details, analysis_id, idea_check_id, supplied_clock
        )
        c.execute(
            "UPDATE news_watches SET lease_until=NULL,last_check_at=%s,error=%s WHERE owner_id=%s AND instrument_id=%s AND claim_token=%s",
            (supplied_clock or datetime.now(timezone.utc), message, owner, iid, token),
        )
    return True
