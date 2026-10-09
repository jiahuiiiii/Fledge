"""Conservative, deterministic checks; never a second sentiment classifier.

Arithmetic is historical context, not an inference of the author's attitude.
All inputs are pinned in the new reading. Old saved readings are never rerendered.
"""

import re
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from thesis.db import one
from . import price_history

POLICY = "sentiment-evidence-guards-1"
NY = ZoneInfo("America/New_York")
MONEY = re.compile(r"(?:US\$|USD\s*|\$)\s*(\d+(?:,\d{3})*(?:\.\d+)?)", re.I)
UP = re.compile(r"\b(?:rise|rises|rising|rally|rallies|rallying|climb|climbs|surge|surges|up|higher)\b", re.I)
DOWN = re.compile(r"\b(?:fall|falls|falling|drop|drops|dropping|decline|declines|crash|crashes|down|lower)\b", re.I)
QUALIFIED = re.compile(r"\b(?:not|never|no|might|may|could|if|unless|would|won't|wouldn't|isn't|don't|doesn't)\b|\?", re.I)


def number(text):
    match = MONEY.fullmatch(text.strip())
    if not match:
        raise ValueError("Price claim amount must be an exact dollar amount in its passage.")
    try:
        value = Decimal(match[1].replace(",", ""))
        if not value.is_finite() or not 0 < value <= Decimal("1e13"):
            raise ValueError()
        return value
    except (InvalidOperation, ValueError):
        raise ValueError("Price claim amount is outside the supported range.") from None


def aliases(company):
    return [company["symbol"], company["name"], re.sub(r"\s+(?:Inc\.?|Corporation|Corp\.?)$", "", company["name"], flags=re.I)]


def without_company(text, company):
    for name in sorted(set(aliases(company)), key=len, reverse=True):
        text = re.sub(r"(?<!\w)\$?" + re.escape(name) + r"(?!\w)", " ", text, flags=re.I)
    return text


def bare_price(text, company):
    """Deliberately narrow: a whole passage, not a dollar substring in prose."""
    clean = without_company(text.strip(), company).strip()
    return bool(re.fullmatch(
        r"(?:to\s+|(?:price\s+)?target\s*(?:of|is|:|=)?\s*|pt\s*[:=]?\s*)?"
        r"(?:US\$|USD\s*|\$)\s*\d+(?:,\d{3})*(?:\.\d+)?"
        r"(?:\s*(?:pt|price\s+target))?[.!]?", clean, re.I))


def price_only(text, company):
    clean = MONEY.sub(" ", without_company(text, company))
    clean = re.sub(r"\b(?:i|my|we|expect|expects|expecting|think|will|is|a|the|stock|shares?|"
                   r"going|headed|to|toward|towards|price|target|pt|of|at|not|never|could|may|might|would|if|unless|rise|rising|rally|"
                   r"fall|falling|drop|dropping|climb|surge|higher|lower|up|down|reach|hit)\b", " ", clean, flags=re.I)
    return bool(MONEY.search(text)) and not re.search(r"\w", clean)


def direct_target(text, company, amount):
    # Fail closed for cross-company figures and unsupported prose grammars.
    # An issuer somewhere else in a multi-company sentence is not enough.
    # A range, option unit, or company-size suffix cannot be silently reduced
    # to one point share-price target.
    tail = text.split(amount, 1)[-1]
    if re.match(r"\s*(?:(?:[-–—]|to|or|and)\s*(?:\$|US\$|USD\s*)?\d|(?:million|billion|trillion|bn|mn)\b|%)", tail, re.I):
        return False
    words = r"(?:\s+(?:stock|shares?|will|is|going|headed|to|rise|rises|rising|fall|falls|falling|drop|drops|dropping|rally|rallies|climb|surge|target|price|of|at|higher|lower|down|up|could|might|may|should|would|reach|hit|a|the|toward|towards|pt)){0,12}"
    return any(re.search(r"(?<!\w)\$?" + re.escape(name) + r"(?!\w)" + words + r"\s*[:=]?\s*" + re.escape(amount) + r"(?![\w,]|\.\d)", text, re.I) for name in aliases(company))


def reference(snapshot, source, company):
    """Only a capture already saved by the verified post time, never today."""
    if source.get("timestamp_basis") == "feed_updated":
        return dict(status="unverified_post_time")
    if not snapshot:
        return dict(status="no_saved_price_at_post_time")
    at = datetime.fromisoformat(source["published_at"])
    series = snapshot["series"]
    retrieved = snapshot["retrieved_at"]
    if isinstance(retrieved, str):
        retrieved = datetime.fromisoformat(retrieved)
    if (retrieved > at or series.get("symbol") != company["symbol"]
            or snapshot.get("symbol") != company["symbol"]
            or series.get("currency") != "USD"
            or series.get("exchange_timezone") != "America/New_York"
            or series.get("interval") != "1d"):
        return dict(status="no_compatible_saved_price")
    day = at.astimezone(NY).date()
    bars = [b for b in series.get("bars", [])
            if b.get("provisional") is False and b["date"] <= min(day, retrieved.astimezone(NY).date()).isoformat()]
    if not bars:
        return dict(status="no_completed_close")
    bar = max(bars, key=lambda b: b["date"])
    if day - datetime.fromisoformat(bar["date"]).date() > timedelta(days=7):
        return dict(status="saved_close_too_old")
    close = price_history.decimal(bar["close"])
    return dict(status="available", snapshot_id=str(snapshot["id"]),
                close=str(close), date=bar["date"], currency="USD",
                retrieved_at=retrieved.isoformat(), basis=series["basis"],
                timestamp_basis=source.get("timestamp_basis", "published"))


def attach(conn, iid, sources, company):
    """Read only. No fetch, new clock, model input, or price-vintage stitching."""
    permitted = price_history.allowed(conn)
    for source in sources:
        if source["channel"] != "social" or not any(MONEY.search(p["quote"]) for p in source["passages"]):
            continue
        snapshot = None
        if permitted and source.get("timestamp_basis") != "feed_updated":
            snapshot = one(conn, "SELECT id,symbol,series,retrieved_at FROM price_history_snapshots WHERE instrument_id=%s AND retrieved_at<=%s ORDER BY retrieved_at DESC,id DESC LIMIT 1", (iid, source["published_at"]))
        source["price_reference"] = (reference(snapshot, source, company) if permitted
                                     else dict(status="price_access_unavailable"))


def allowed(conn, packet):
    return (not any(s.get("price_reference", {}).get("status") == "available"
                    for s in packet["sources"]) or price_history.allowed(conn))


def price_details(item, source, company):
    passages = {p["id"]: p["quote"] for p in source["passages"]}
    details = []
    for claim in item.price_claims:
        text = passages.get(claim.passage_id, "")
        if not text or claim.amount_text not in text:
            raise ValueError("Price claim does not match its own original passage.")
        value = number(claim.amount_text)
        direction = "not_stated"
        if claim.direction_text is not None:
            if claim.direction_text not in text:
                raise ValueError("Price direction wording does not match its original passage.")
            # Isolated 'rise' inside 'will not rise' cannot establish direction.
            if not QUALIFIED.search(text):
                up, down = bool(UP.search(claim.direction_text)), bool(DOWN.search(claim.direction_text))
                if up != down:
                    direction = "up" if up else "down"
        issuer = direct_target(text, company, claim.amount_text)
        ref = source.get("price_reference") or reference(None, source, company)
        if source.get("timestamp_basis") == "feed_updated":
            ref = dict(status="unverified_post_time")
        detail = dict(passage_id=claim.passage_id, quote=text, amount=str(value),
                      kind=claim.kind, author_direction=direction, reference=ref)
        if claim.kind != "price_target" or not issuer:
            detail["status"] = "not_comparable_target"
        elif ref["status"] != "available":
            detail["status"] = ref["status"]
        else:
            close = Decimal(ref["close"])
            difference = (value - close) / close * 100
            detail.update(status="compared", difference_percent=str(difference),
                          relation="above" if difference > 0 else "below" if difference < 0 else "equal")
        details.append(detail)
    # The simplest failure must be caught even if extraction misses the target.
    for pid in item.passages:
        text = passages[pid]
        match = MONEY.search(text)
        if match and price_only(text, company) and not any(d["passage_id"] == pid for d in details):
            from types import SimpleNamespace
            fallback = SimpleNamespace(price_claims=[SimpleNamespace(passage_id=pid, amount_text=match[0], kind="price_target" if re.search(r"\b(?:to|target|pt)\b", text, re.I) else "other", direction_text=text)], passages=[])
            details.extend(price_details(fallback, source, company))
    return details


def apply(item, source, company):
    quotes = [p["quote"] for p in source["passages"] if p["id"] in item.passages]
    prices = price_details(item, source, company) if source["channel"] == "social" else []
    reason = None
    if item.relevance == "relevant" and item.sentiment != "unclear":
        if all(bare_price(q, company) for q in quotes):
            reason = "bare_price_target"
        elif all(price_only(q, company) for q in quotes) and prices:
            if any(d["author_direction"] == "not_stated" for d in prices):
                reason = "price_direction_unstated"
            elif any(d["status"] != "compared" for d in prices):
                reason = "price_reference_unavailable"
            elif any((d["author_direction"], d["relation"]) not in {("up", "above"), ("down", "below")} for d in prices):
                reason = "price_direction_conflict"
            elif any((item.sentiment, d["author_direction"]) not in {("positive", "up"), ("negative", "down")} for d in prices):
                reason = "price_label_conflict"
        elif all(not re.search(r"[A-Za-z]", MONEY.sub("", without_company(q, company))) for q in quotes):
            reason = "bare_ticker_or_number"
        elif all(q.rstrip().endswith("?") for q in quotes):
            reason = "question_only"
    notes = {
        "bare_price_target": "A price target alone does not state whether the author expects a rise or a fall.",
        "price_direction_unstated": "The price wording does not establish the author's direction.",
        "price_reference_unavailable": "This price-only view has no compatible saved close from the time of the post.",
        "price_direction_conflict": "The stated direction conflicts with the saved-close comparison. The intended reference is unclear.",
        "price_label_conflict": "The AI label conflicts with the explicit price direction. The item needs review.",
        "bare_ticker_or_number": "The selected wording contains only a company name, ticker or number.",
        "question_only": "The selected wording asks a question without a separate stated view.",
    }
    guard = dict(policy=POLICY, applied=bool(reason), rule=reason,
                 model_sentiment=item.sentiment, model_basis=item.basis,
                 explanation=notes.get(reason))
    return dict(guard=guard, price_comparisons=prices,
                **(dict(sentiment="unclear", basis="unclear", explanation=notes[reason]) if reason else {}))
