"""Deterministic, bounded alert cards; presentation never invokes a model."""
from datetime import datetime, timezone
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlsplit
import ipaddress

RELATIONS = {
    "supports": "May support your reasoning", "challenges": "May challenge your reasoning",
    "risk": "Risk to investigate", "answers": "Evidence toward your question",
}


def plain(value, limit=400):
    value = " ".join(str(value or "").split())
    return value[:limit] + ("…" if len(value) > limit else "")


def safe_url(value):
    try:
        u = urlsplit(value or "")
        if u.scheme != "https" or not u.hostname or u.username or u.password or u.port not in (None, 443):
            return None
        if u.hostname == "localhost" or u.hostname.endswith((".local", ".localhost")):
            return None
        try:
            if not ipaddress.ip_address(u.hostname).is_global:
                return None
        except ValueError:
            pass
        return value if len(value) <= 1800 else None
    except ValueError:
        return None


def render(record):
    d = record["detail"]
    kind = record["kind"]
    if d.get("withheld"):
        raise ValueError("Source access changed; do not forward this alert.")
    symbol = plain(d.get("symbol"), 18)
    label = {"company": "Company update", "idea": "Saved idea", "condition": "Monitored condition"}[kind]
    parts = [f"<b>{escape(symbol)} · {label}</b>", f"<b>{escape(plain(record['title'], 180))}</b>"]
    if d.get("fictional"):
        parts.insert(0, "<b>Fictional demo · not actual company news</b>")
    source_ids = []
    if kind == "company":
        payload = d["payload"]
        for shift in payload.get("shifts", [])[:3]:
            parts.append(escape(plain(shift.get("title"), 120)) + ": " + escape(plain(shift["before"]["tone"], 30)) + " → " + escape(plain(shift["after"]["tone"], 30)))
        parts.append(escape(plain(payload.get("reason"), 450)))
        for item in payload.get("items", [])[:2]:
            source_ids.append(item["source_id"])
            basis = item.get("reporting_basis") or {}
            quotes = basis.get("citations") or item.get("citations") or []
            if quotes:
                prefix = "Unconfirmed report" if basis.get("kind") == "unconfirmed_event" else "Source excerpt"
                parts.append(f"<b>{prefix}</b>\n“{escape(plain(quotes[0].get('quote'), 320))}”")
        if payload.get("cutoff"):
            parts.append("Sample cutoff: " + stamp(payload["cutoff"]))
    elif kind == "idea":
        parts.append("<b>Your question</b>\n" + escape(plain(d.get("question"), 240)))
        for item in [i for i in d["items"] if i["relation"] in RELATIONS][:2]:
            source_ids.append(item["source_id"])
            parts.append("<b>" + RELATIONS[item["relation"]] + "</b>\n" + escape(plain(item.get("explanation"), 350)))
        parts.append("Source interpretation; it does not resolve your idea or verify a social claim.")
    else:
        source_ids.extend(s["id"] for s in d.get("sources", [])[:2])
        parts.append("<b>Your question</b>\n" + escape(plain(d.get("question"), 240)))
        change = d.get("details", {})
        for item in change.get("affected_conditions", [])[:3]:
            metric = plain(item.get("metric", "Condition").replace("_", " ").capitalize(), 60)
            before = "Unknown" if item.get("before") is None else plain(item["before"], 60) + "%"
            after = "Unknown" if item.get("after") is None else plain(item["after"], 60) + "%"
            parts.append(escape(metric) + ": " + escape(before) + " → " + escape(after))
        for item in change.get("affected_events", [])[:2]:
            parts.append(escape(plain(item.get("description"), 150)) + ": " + escape(plain(item.get("before"), 40)) + " → " + escape(plain(item.get("after"), 40)))
        parts.append("A saved comparison changed. Check its reporting period, evidence and coverage in Thesis.")
    sources = {str(s["id"]): s for s in d.get("sources", [])}
    links = []
    for sid in dict.fromkeys(map(str, source_ids)):
        source = sources.get(sid, {})
        url = safe_url(source.get("url"))
        if url:
            name = plain(source.get("source") or source.get("title") or "Read source", 75)
            platform = source.get("platform")
            if platform:
                name = plain(platform, 25) + " · " + name
            links.append(f'<a href="{escape(url, quote=True)}">{escape(name)}</a>')
    if links:
        parts.append("<b>Sources</b>\n" + "\n".join(links[:2]))
    parts.append("Flagged " + stamp(record["created_at"]))
    parts.append(f"Open Thesis on your Mac → Updates → {escape(symbol)}.\nResearch alert · not a buy/sell instruction.")
    # Telegram counts parsed text; UTF-16 units are a conservative bound even
    # with emoji. Drop whole optional sections, never split tags or entities.
    footer = parts[-2:]
    selected = []
    for part in parts[:-2]:
        candidate = "\n\n".join(selected + [part] + footer)
        if visible_units(candidate) <= 3800:
            selected.append(part)
    return "\n\n".join(selected + footer)


def visible_units(html):
    class Text(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.value = ""
        def handle_data(self, data):
            self.value += data
    parser = Text()
    parser.feed(html)
    return len(parser.value.encode("utf-16-le")) // 2


def stamp(value):
    value = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return value.astimezone(timezone.utc).strftime("%d %b %Y, %H:%M UTC")


TEST_MESSAGE = "<b>Thesis · Connection test</b>\n\nYour private Telegram chat is connected.\n\nWhen delivery is enabled, new company, saved-idea and monitored-condition alerts will arrive here with evidence and context.\n\nThis is a test message, not a market event. Your research watches are unchanged."
