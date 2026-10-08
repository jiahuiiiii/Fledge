"""Fit complete sources to the existing paid-request ceiling before dispatch."""

from collections import Counter
from copy import deepcopy

from thesis.providers import ledger

POLICY = "sentiment-complete-inputs-1"


def scope(source):
    return "news" if source["channel"] == "news" else source.get("platform") or "reddit"


def notice(omitted, comparisons):
    parts = []
    if comparisons:
        parts.append(
            f"{comparisons} additional comparison report{'s' if comparisons != 1 else ''}"
        )
    for key, label in (
        ("news", "news report"),
        ("reddit", "Reddit post"),
        ("hackernews", "Hacker News comment"),
        ("x", "X post"),
    ):
        if omitted.get(key):
            parts.append(f"{omitted[key]} {label}{'s' if omitted[key] != 1 else ''}")
    return (
        "To fit this analysis, the selection leaves out "
        + ", ".join(parts)
        + ". Selected text and its supplied parent context are not shortened "
        "to meet this limit. Omitted material may change the reading."
    )


def fit(packet, request_for, *, max_bytes=None):
    """Retain selected originals first, then the highest-ranked comparisons.

    If originals alone exceed the bound, remove the last selected original in
    the more populated channel (then platform). Ties use total serialized size.
    No model judgments, partial passages, parent detachment or extra requests.
    """
    ceiling = ledger.MAX_REQUEST_BYTES if max_bytes is None else max_bytes
    if not packet["sources"]:
        return packet

    def size(value):
        return len(ledger.canonical(request_for(value)).encode())

    initial = size(packet)
    if initial <= ceiling:
        return packet
    fitted = deepcopy(packet)
    comparisons = fitted.get("comparison_sources", [])
    before_comparisons = len(comparisons)
    # Find the longest prefix that fits. Comparison order is already ranked.
    lower, upper = 0, len(comparisons)
    while lower < upper:
        middle = (lower + upper + 1) // 2
        fitted["comparison_sources"] = comparisons[:middle]
        if size(fitted) <= ceiling:
            lower = middle
        else:
            upper = middle - 1
    fitted["comparison_sources"] = comparisons[:lower]
    omitted = Counter()

    def largest_group(sources, key):
        groups = {}
        for source in sources:
            groups.setdefault(key(source), []).append(source)
        return max(
            groups.values(),
            key=lambda group: (
                len(group),
                sum(len(ledger.canonical(s).encode()) for s in group),
                scope(group[-1]),
            ),
        )

    final = size(fitted)
    while fitted["sources"] and final > ceiling:
        channel = largest_group(fitted["sources"], lambda s: s["channel"])
        platform = largest_group(channel, scope)
        dropped = platform[-1]
        omitted[scope(dropped)] += 1
        fitted["sources"].remove(dropped)
        if not fitted["sources"]:
            final = None  # No valid model request is constructed or dispatched.
            break
        final = size(fitted)
    fitted["omitted_fragment_count"] = sum(
        s.get("omitted_fragment_count", 0) for s in fitted["sources"]
    )
    omitted_comparisons = before_comparisons - len(fitted["comparison_sources"])
    fitted["input_limits"] = dict(
        policy=POLICY,
        original_request_bytes=initial,
        request_bytes=final,
        max_request_bytes=ceiling,
        omitted_sources=dict(omitted),
        omitted_comparisons=omitted_comparisons,
        notice=notice(omitted, omitted_comparisons),
    )
    return fitted
