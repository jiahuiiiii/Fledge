"""Saved Reddit discussions on the model wire, without invented reply trees.

Thread membership comes from discovery, not text similarity or feed order.
Only already-permitted, dated originals are used; this module never fetches.
"""
from collections import OrderedDict
from copy import deepcopy
import hashlib
import re

from thesis.providers.ledger import canonical
from .citations import source_passages

POLICY = "saved-reddit-thread-context-1"
MAX_EXTRA_BYTES = 12000
LIMITATION = (
    "Only complete saved passages are supplied, not the complete Reddit thread. "
    "A shared topic does not establish which comment a reply answers. "
    "Unknown reply parents remain unknown; short ambiguous replies may remain unclear."
)
INSTRUCTION = (
    "Read each reddit_threads discussion together before labelling its target messages. "
    "A message with source_label refers to that exact entry in sources; other messages "
    "are context only, never extra items or votes. The root is the discussion topic, "
    "NOT necessarily a comment's immediate parent. parent_key is supplied only for a "
    "verified immediate parent; null means unknown. Never infer nesting from order, "
    "the nearest message, or similar wording. Preserve message and author boundaries; "
    "do not assign the topic author's or another commenter's stance to a reply. "
    "Use the whole supplied discussion to understand the subject and contrasting "
    "views, but an ambiguous 'yes', 'no' or sarcastic reply without its verified "
    "parent remains unclear. The comment's own body must support its attitude. "
    "These are partial saved discussions; omitted messages and unknown parents "
    "cannot be reconstructed. A large discussion may span requests with its topic "
    "repeated as context; label only the sources requested in this call."
)


def key(source):
    value = source.get("thread_key")
    if source.get("platform") == "reddit" and isinstance(value, str) and re.fullmatch(r"t3_[a-z0-9]+", value):
        return value
    return None


def ordered(sources):
    """Keep discussion targets adjacent without changing their labels or originals."""
    groups = OrderedDict()
    for index, source in enumerate(sources):
        group = ("reddit", key(source)) if key(source) else ("item", index)
        groups.setdefault(group, []).append(source)
    return [source for group in groups.values() for source in group]


def message(source):
    parent = source.get("conversation") or {}
    return dict(
        source_id=source["id"], message_key=source["post_key"],
        role="topic" if source["post_key"] == key(source) else "comment",
        parent_key=parent.get("parent_key"),
        author_key=source.get("author_hash"),
        passages=deepcopy(source["passages"]),
        published_at=source["published_at"], available_at=source["available_at"],
        url=source["url"],
        **{k: source[k] for k in ("timestamp_basis", "source_note") if k in source},
    )


def attach(sources, posts):
    """Pin the current permitted root even if exact-text deduplication removed it.

    Posts are the same cutoff/window/permission-filtered social.documents result
    used by sentiment.prepare. No older or future root is borrowed.
    """
    threads = OrderedDict()
    for source in sources:
        thread = key(source)
        if thread and source.get("post_key"):
            threads.setdefault(thread, OrderedDict())[source["post_key"]] = message(source)
    for post in posts:
        thread = post.get("post_key")
        if post.get("platform") != "reddit" or thread not in threads or thread in threads[thread]:
            continue
        passages, _ = source_passages(post["title"], post["body"])
        if not passages:
            continue
        threads[thread][thread] = dict(
            source_id=str(post["id"]), message_key=thread, role="topic", parent_key=None,
            author_key=post.get("author_hash"), passages=passages,
            published_at=post["published_at"].isoformat(),
            available_at=post["available_at"].isoformat(), url=post["url"],
        )
    result = []
    for thread, messages in threads.items():
        values = sorted(messages.values(), key=lambda m: (m["role"] != "topic", m["published_at"], m["message_key"]))
        context = dict(thread_key=thread, messages=values)
        digest = hashlib.sha256(canonical(context).encode()).hexdigest()
        for source in sources:
            if key(source) == thread:
                source["thread_context_key"] = digest
        result.append(context)
    return result


def wire(packet, sources, *, extras=True):
    """Repeat the root and preserve all targets; add whole saved siblings if they fit.

    Target text appears once, in sources. Optional siblings can be reduced before
    splitting a request. Roots and verified immediate parents are never shortened.
    """
    labels = {s["id"]: s["label"] for s in sources}
    selected = {key(s) for s in sources if key(s)}
    result = []
    for context in packet.get("reddit_thread_context", []):
        if context["thread_key"] not in selected:
            continue
        messages = context["messages"]
        authors = {author: f"author_{index + 1}" for index, author in enumerate(dict.fromkeys(m['author_key'] for m in messages if m.get('author_key')))}
        parents = {m["parent_key"] for m in messages if m["source_id"] in labels}
        required, optional = [], []
        for original in messages:
            m = deepcopy(original)
            m['author_key'] = authors.get(m.get('author_key'))
            if m["source_id"] in labels:
                m.pop("passages")
                m["source_label"] = labels[m["source_id"]]
            # URLs/storage dates are kept in the saved evidence, not repeated on wire.
            for field in ("source_id", "url", "available_at"):
                m.pop(field)
            (required if original["source_id"] in labels or m["role"] == "topic"
             or m["message_key"] in parents else optional).append(m)
        supplied = list(required)
        used = 0
        if extras:
            for m in optional:
                size = len(canonical(m).encode())
                if used + size <= MAX_EXTRA_BYTES:
                    supplied.append(m)
                    used += size
        supplied.sort(key=lambda m: (m["role"] != "topic", m["published_at"], m["message_key"]))
        result.append(dict(
            thread_key=context["thread_key"], messages=supplied,
            saved_message_count=len(messages), supplied_message_count=len(supplied),
            omitted_saved_messages=len(messages) - len(supplied),
            topic_available=any(m["role"] == "topic" for m in supplied),
            complete_thread=False, limitation=LIMITATION,
        ))
    return result


def access_allowed(packet, permitted):
    return all(m["source_id"] in permitted for c in packet.get("reddit_thread_context", []) for m in c["messages"])


def evidence(packet, source):
    thread = key(source)
    if not thread:
        return None
    context = next((c for c in wire(packet, packet["sources"], extras=packet.get("thread_extras", True)) if c["thread_key"] == thread), None)
    if not context:
        return None
    originals = next(c["messages"] for c in packet["reddit_thread_context"] if c["thread_key"] == thread)
    supplied = {m["message_key"] for m in context["messages"]}
    return dict(context, messages=[deepcopy(m) for m in originals if m["message_key"] in supplied])
