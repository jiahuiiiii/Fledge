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
    name = re.sub(r"[,./]+", " ", name).strip()
    name = re.sub(r"\s+(?:(?:incorporated|inc|corp|corporation|limited|ltd|plc|co|company)\s*)+$", "", name, flags=re.I).strip()
    name = " ".join(name.split())
    # Common standalone words require explicit financial context instead.
    if len(name) < 6 or name.lower() in {"target", "united", "applied", "global", "energy", "public", "capital", "advance", "progress", "national", "general", "first", "digital", "international"}:
        return None
    return name


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
        return bool((company_alias(company_name) and re.search(r"(?<!\w)" + re.escape(company_alias(company_name)) + r"(?!\w)", text, re.I)) or re.search(rf"\${ticker}\b|\b(?:NASDAQ|NYSE):\s*{ticker}\b", text, re.I) or re.search(rf"\b{ticker}\s+(?i:stock|shares|earnings)\b", text))
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
