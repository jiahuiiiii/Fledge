"""Shape the company read for the wire, without changing what the page sees.

share_texts: the same article or post text often appears in up to three
lists of one company read (saved documents, the saved AI reading's sources
and the current source selection). Text that repeats is sent once, in
`source_texts`, and each place that had it carries `body_ref` instead; the
browser puts the text back before anything reads it
(frontend/src/lib/sharedTexts.js). Only text already in the answer moves, so
source access and withdrawals are unchanged.

revision: a short hash of the answer, so a re-read can say "I already have
this" and get `unchanged` instead of the whole company again.
"""
from collections import Counter
import hashlib
import json

# Short texts are not worth a reference.
MIN_SHARED = 200
# Lists whose items may carry a source text under `body`.
SOURCE_LISTS = (
    ("documents",),
    ("sentiment", "sources"),
    ("sentiment", "comparison_sources"),
    ("sentiment_inputs", "sources"),
    ("sentiment_inputs", "comparison_sources"),
)
# Fields that change on every read without the data changing; left out of
# the revision. A field missed here only means a full answer where an
# `unchanged` one would have done, never a stale page.
VOLATILE = (("sentiment_inputs", "as_of"),)


def _lists(result):
    for path in SOURCE_LISTS:
        value = result
        for key in path:
            value = value.get(key) if isinstance(value, dict) else None
        if isinstance(value, list):
            yield value


def share_texts(result):
    """Move texts that occur more than once into result['source_texts']."""
    holders = [
        item
        for items in _lists(result)
        for item in items
        if isinstance(item, dict)
        and isinstance(item.get("body"), str)
        and len(item["body"]) >= MIN_SHARED
    ]
    counts = Counter(item["body"] for item in holders)
    texts = {}
    for item in holders:
        body = item["body"]
        if counts[body] < 2:
            continue
        ref = hashlib.blake2b(body.encode(), digest_size=8).hexdigest()
        texts[ref] = body
        del item["body"]
        item["body_ref"] = ref
    if texts:
        result["source_texts"] = texts
    return result


def revision(result):
    """Stable hash of a JSON-ready answer, leaving out VOLATILE fields."""
    removed = []
    for parent, key in VOLATILE:
        block = result.get(parent)
        if isinstance(block, dict) and key in block:
            removed.append((block, key, block.pop(key)))
    try:
        text = json.dumps(result, sort_keys=True, separators=(",", ":"), default=str)
    finally:
        for block, key, value in removed:
            block[key] = value
    return hashlib.blake2b(text.encode(), digest_size=12).hexdigest()
