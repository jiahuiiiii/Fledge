"""Current permitted source selection, independent of any generated labels."""

from datetime import datetime, timezone
from thesis.db import one
from . import sentiment, social

SCOPES = ("news", "reddit", "hackernews", "x")


def scope(source):
    return "news" if source["channel"] == "news" else source.get("platform") or "reddit"


def identity(source):
    return (scope(source), source["id"])


def context_key(source):
    return (source.get("conversation") or {}).get("content_key")


def current(conn, iid, now=None):
    now = now or datetime.now(timezone.utc)
    if not sentiment.market_brief.company_for(iid):
        return None
    latest = one(
        conn,
        "SELECT * FROM sentiment_analyses WHERE instrument_id=%s ORDER BY (packet->>'cutoff')::timestamptz DESC,created_at DESC,id DESC LIMIT 1",
        (iid,),
    )
    visible = sentiment.present(conn, latest)
    baseline = latest if visible and not visible["withheld"] else None
    days = latest["packet"].get("social_lookback_days", 7) if latest else 7
    packet = sentiment.prepare(conn, iid, now, allow_empty=True, lookback_days=days)
    old = {identity(s): s for s in baseline["packet"]["sources"]} if baseline else {}
    new = {identity(s): s for s in packet["sources"]}
    scopes = {}
    for name in SCOPES:
        selected = {key for key in new if key[0] == name}
        prior = {key for key in old if key[0] == name}
        scopes[name] = dict(
            selected=len(selected),
            available=(
                packet["available_news_count"]
                if name == "news"
                else packet.get("available_social_platforms", {}).get(name, 0)
            ),
            added=len(selected - prior) if baseline else None,
            no_longer_selected=len(prior - selected) if baseline else None,
            retained=len(selected & prior) if baseline else None,
        )
    parents_changed = (
        sum(context_key(old[k]) != context_key(new[k]) for k in old.keys() & new.keys())
        if baseline
        else None
    )
    compared_before = (
        {identity(s) for s in baseline["packet"].get("comparison_sources", [])}
        if baseline
        else None
    )
    compared_now = {identity(s) for s in packet.get("comparison_sources", [])}
    comparisons_changed = compared_before != compared_now if baseline else None
    if not packet["sources"]:
        status = "empty"
    elif latest and not baseline:
        status = "saved_reading_withheld"
    elif not baseline:
        status = "no_saved_reading"
    elif set(old) != set(new) or parents_changed or comparisons_changed:
        status = "changed"
    else:
        status = "same"
    return dict(
        status=status,
        social_lookback_days=days,
        input_limits=packet.get("input_limits"),
        as_of=now.isoformat(),
        saved_cutoff=visible["cutoff"] if visible else None,
        saved_reading_available=bool(baseline),
        scopes=scopes,
        parents_changed=parents_changed,
        comparison_sources_changed=comparisons_changed,
        comparison_news=len(compared_now),
        parent_contexts=sum(bool(s.get("conversation")) for s in new.values()),
        sources=[
            dict(
                id=s["id"],
                title=s["title"],
                body=s["text"],
                source=s["publisher"],
                kind=s["channel"],
                platform=s.get("platform")
                or ("reddit" if s["channel"] == "social" else None),
                **social.source_metadata(s),
                published_at=s["published_at"],
                available_at=s["available_at"],
                url=s["url"],
                in_saved_sample=(identity(s) in old) if baseline else None,
                has_parent_context=bool(s.get("conversation")),
            )
            for s in packet["sources"]
        ],
    )
