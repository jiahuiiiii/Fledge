"""Deterministic, bounded alert cards; presentation never invokes a model."""
from thesis.display_time import stamp
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


TONES = {"favourable": "Good news", "adverse": "Bad news", "mixed": "Mixed news"}
SENTIMENTS = {"positive": "Good news", "negative": "Bad news", "mixed": "Mixed news", "neutral": "Neutral news"}
LEANINGS = {"positive leaning": "Good news", "negative leaning": "Bad news"}
CATEGORIES = {"earnings_guidance": "earnings or guidance", "legal_regulatory": "legal or regulatory",
              "deal": "deal", "management": "management", "product": "product",
              "analyst_opinion": "analyst", "market_commentary": "market commentary"}


def item_tone(item):
    """The saved reading's label; an effect stated in the report outranks tone."""
    impact = (item.get("reporting_basis") or {}).get("impact")
    return TONES.get(impact) or SENTIMENTS.get(item.get("sentiment"), "Unclear news")


def news_tone(payload, items):
    shifts = payload.get("shifts") or []
    if shifts:
        after = {LEANINGS.get(s["after"]["tone"], "Mixed news") for s in shifts}
        return after.pop() if len(after) == 1 else "Mixed news"
    tones = {item_tone(i) for i in items}
    return tones.pop() if len(tones) == 1 else "Mixed news"


def why_notified(payload, items):
    """One plain sentence from saved labels only; no new interpretation."""
    shifts = payload.get("shifts") or []
    if shifts:
        s = shifts[0]
        return f"Why: news tone changed from {plain(s['before']['tone'], 30)} to {plain(s['after']['tone'], 30)}."
    if payload.get("kind") == "new_reporting":
        if payload.get("coverage_links"):
            return "Why: a new report changes details of a story seen earlier."
        return "Why: a new report describes a development with a bad or mixed effect for the company."
    importance = (items[0].get("importance") or {}) if items else {}
    if importance.get("level"):
        kind = CATEGORIES.get(importance.get("category"), "company")
        return f"Why: new {kind} news, rated {plain(importance['level'], 10)} importance."
    return "Why: " + plain(payload.get("title") or "new company news", 160) + "."


def render(record,*,shown=None):
    d = record["detail"]
    kind = record["kind"]
    if d.get("withheld") or (d.get("payload") or {}).get("withheld_items"):
        raise ValueError("Source access changed; do not forward this alert.")
    if d.get('preview'):
        raise ValueError('Preview alerts must never be sent.')
    if kind in {'digest','cost'}:
        from .daily_telegram import render as daily_render
        return daily_render(record)
    symbol = plain(d.get("symbol"), 18)
    label = {"company": "Company update", "idea": "Saved idea", "condition": "Monitored condition", "move": "Price move"}[kind]
    parts = [f"<b>{escape(symbol)} · {label}</b>", f"<b>{escape(plain(record['title'], 180))}</b>"]
    if d.get("fictional"):
        parts.insert(0, "<b>Fictional demo · not actual company news</b>")
    source_ids = []
    primary_parts = {}
    if kind == "move":
        if d.get('preview'):
            raise ValueError('Preview price events must never be sent.')
        from .move_alerts import percent, numbers as move_numbers
        numbers=move_numbers(d['members'])
        index=d['members'][0]['indexes'].get('QQQ')
        numbers+=(f" · Nasdaq {percent(index['change_percent'])}" if index else ' · Nasdaq unavailable')
        if visible_units(escape(numbers))>3000:
            raise ValueError('The full market-event member list exceeds the message bound.')
        parts=[f'<b>{escape(numbers)}</b>']
        context=[m['symbol'] for m in d['members'] if m['context_only']]
        if context:
            parts.append('Market context only; no individual threshold crossed: '+escape(', '.join(context)))
        explanation=d.get('explanation') or {}
        cause={'market':'Possible market connection','sector':'Possible sector connection',
               'company':'Possible company connection','no_clear':'No clear cause found'}.get(explanation.get('cause'),'No clear cause found')
        parts.append('<b>'+cause+'</b>\n'+escape(plain(explanation.get('text') or 'No verified explanation is saved.',800)))
        source_ids.extend(s['id'] for s in d.get('sources',[]))
    elif kind == "company":
        # Owner feedback 20 Oct 2026: say good, bad or neutral up front, one short
        # line on why, then the excerpt. The rule's explanation stays in the app.
        payload = d["payload"]
        items = payload.get("items", [])[:2]
        titles = {str(s["id"]): s.get("title") for s in d.get("sources", [])}
        parts = [f"<b>{escape(symbol)} · {escape(news_tone(payload, items))}</b>",
                 f"<b>{escape(plain(titles.get(str(items[0]['source_id'])) if items else None, 180) or plain(record['title'], 180))}</b>"]
        if d.get("fictional"):
            parts.insert(0, "<b>Fictional demo · not actual company news</b>")
        parts.append(escape(why_notified(payload, items)))
        for index, item in enumerate(items):
            source_ids.append(item["source_id"])
            basis = item.get("reporting_basis") or {}
            quotes = basis.get("citations") or item.get("citations") or []
            if quotes:
                prefix = "Unconfirmed report" if basis.get("kind") == "unconfirmed_event" else "Source excerpt"
                also = titles.get(str(item["source_id"])) if index else None
                head = f"<b>Also: {escape(plain(also, 150))}</b>\n" if also else ""
                parts.append(f"{head}<b>{prefix}</b>\n“{escape(plain(quotes[0].get('quote'), 320))}”")
                primary_parts[len(parts)-1]=item['source_id']
    elif kind == "idea":
        parts.append("<b>Your question</b>\n" + escape(plain(d.get("question"), 240)))
        for item in [i for i in d["items"] if i["relation"] in RELATIONS][:2]:
            source_ids.append(item["source_id"])
            parts.append("<b>" + RELATIONS[item["relation"]] + "</b>\n" + escape(plain(item.get("explanation"), 350)))
            primary_parts[len(parts)-1]=item['source_id']
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
        parts.append("A saved comparison changed. Check its reporting period, evidence and coverage in Fledge.")
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
    parts.append(f"Open Fledge on your Mac → Updates → {escape(symbol)}.\nResearch alert · not a buy/sell instruction.")
    # Telegram counts parsed text; UTF-16 units are a conservative bound even
    # with emoji. Drop whole optional sections, never split tags or entities.
    footer = parts[-2:]
    selected = []
    for index,part in enumerate(parts[:-2]):
        candidate = "\n\n".join(selected + [part] + footer)
        if visible_units(candidate) <= 3800:
            selected.append(part)
            if shown is not None and index in primary_parts:shown.append(primary_parts[index])
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




TEST_MESSAGE = "<b>Fledge · Connection test</b>\n\nYour private Telegram chat is connected.\n\nWhen delivery is enabled, new company, saved-idea and monitored-condition alerts will arrive here with evidence and context.\n\nThis is a test message, not a market event. Your research watches are unchanged."
