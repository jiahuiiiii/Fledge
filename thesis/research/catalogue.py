"""Supported operating-company identities and bounded lexical source matching.

CIKs preserve the existing SEC-derived instrument IDs. A textual mention is a
candidate for analysis, never proof that the source is relevant to investing.
"""

import re

COMPANIES = {
    "MSFT": (789019, "Microsoft", "Software"),
    "AAPL": (320193, "Apple", "Consumer technology"),
    "GOOGL": (1652044, "Alphabet", "Internet services"),
    "NVDA": (1045810, "NVIDIA", "Semiconductors"),
    "AMZN": (1018724, "Amazon", "Commerce and cloud"),
    "META": (1326801, "Meta Platforms", "Internet services"),
}


def company_alias(name):
    """A registered issuer name, stripped only of legal suffixes; no fuzzy match."""
    if not isinstance(name, str):
        return None
    # SEC issuer names can end in a slash-delimited incorporation code (e.g.
    # QUALCOMM INC/DE). Remove that annotation before stripping legal suffixes.
    # Do not remove ordinary final words, or a slash inside a business name.
    name = re.sub(r"(\b(?:incorporated|inc|corp|corporation|limited|ltd|plc|co|company)\.?)\s*/[A-Z]{2}/?\s*$", r"\1", name, flags=re.I).strip()
    name = re.sub(r"[,./]+", " ", name).strip()
    name = re.sub(r"\s+(?:(?:incorporated|inc|corp|corporation|limited|ltd|plc|co|company)\s*)+$", "", name, flags=re.I).strip()
    name = " ".join(name.split())
    # Common standalone words require explicit financial context instead.
    if len(name) < 6 or name.lower() in {"target", "united", "applied", "global", "energy", "public", "capital", "advance", "progress", "national", "general", "first", "digital", "international"}:
        return None
    return name


def company_search_name(symbol, name=None):
    """A bounded source-search name; canonical issuer identity stays unchanged."""
    established = dict(MSFT='Microsoft', AAPL='Apple', GOOGL='Google',
                       NVDA='Nvidia', AMZN='Amazon', META='Meta')
    if symbol in established:
        return established[symbol]
    alias = company_alias(name)
    # These shorter public names require BOTH the registered name and symbol.
    short = {('AMD', 'advanced micro devices'): 'AMD',
             ('MRVL', 'marvell technology'): 'Marvell',
             ('MU', 'micron technology'): 'Micron'}
    return short.get((symbol, (alias or '').lower()), alias) or symbol


def mentions(text, symbol, company_name=None):
    patterns = {
        "MSFT": r"\b(?:MSFT|Microsoft)\b",
        "AAPL": r"\b(?:AAPL|Apple)\b",
        "GOOGL": r"\b(?:GOOGL|GOOG|Alphabet|Google)\b",
        "NVDA": r"\b(?:NVDA|NVIDIA)\b",
        "AVGO": r"\b(?:AVGO|Broadcom)\b",
        "AMZN": r"\bAMZN\b|\bAmazon(?:\.com)?\b(?!\s+(?:rainforest|river|basin)\b)|\bAmazon Web Services\b",
        "META": r"\$META\b|\b(?:Meta Platforms|Facebook|Instagram|WhatsApp)\b|\bmeta\s+(?:stock|shares|earnings|revenue|CEO|profit)\b",
    }
    if symbol not in patterns:
        if not isinstance(symbol, str) or not re.fullmatch(r"[A-Z]{1,5}", symbol):
            return False
        # Conservative matching for new issuers: explicit financial ticker context
        # avoids classifying ordinary words (IT, ON, ALL) as company discussion.
        ticker = re.escape(symbol)
        alias = company_alias(company_name)
        search = company_search_name(symbol, company_name)
        # Micron is also a unit: the abbreviated brand needs a capital M.
        # AMD's uppercase acronym is similarly deliberate; unknown tickers
        # still require the existing explicit financial context.
        short = search != alias and search != symbol or (symbol == 'AMD' and alias and alias.lower() == 'advanced micro devices')
        flags = 0 if search in ('Micron', 'AMD') else re.I
        return bool((alias and re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", text, re.I)) or
                    (short and re.search(r"(?<!\w)" + re.escape(search) + r"(?!\w)", text, flags)) or
                    re.search(rf"\${ticker}\b|\b(?:NASDAQ|NYSE):\s*{ticker}\b", text, re.I) or
                    re.search(rf"\b{ticker}\s+(?i:stock|shares|earnings)\b", text))
    if re.search(patterns[symbol], text, re.I):
        return True
    # A generic lowercase 'meta' or 'meta-analysis' is not the company. Capitalised
    # brand/ticker mentions remain eligible; the classifier decides actual relevance.
    return symbol == "META" and bool(
        re.search(
            r"\b(?:Meta|META)\b(?![- ]+(?i:analysis|discussion|thread|question|data)\b)",
            text,
        )
    )
