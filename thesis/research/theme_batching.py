"""Whole-source discussion batches with bounded checks and complete publication.

The size envelope is local planning data only, never a provider request.
Original source passages, saved parents, profiles and ledger limits stay intact.
"""
from collections import Counter
from copy import deepcopy
from contextlib import contextmanager
import psycopg
from thesis.config import dsn
from decimal import Decimal
import hashlib

from thesis.db import transaction, one
from thesis.providers import ledger
from . import discussion_themes as themes, discussion_theme_check as checker
from . import sentiment_context
from .citations import model_source

POLICY = "discussion-whole-source-batches-1"
MAX_SOURCES = 24
MAX_BYTES = 48000
NOTE = "Sources were read in complete batches. Topics and differing views were compared within each batch, not ranked or merged across the whole sample; similar topics may appear more than once."


def wire_size(value):
    return len(ledger.canonical(value).encode())


def _nested_size(value):
    # Source evidence is JSON inside the request's user-message JSON string.
    return wire_size(ledger.canonical(value))


def check_envelope(packet):
    """Conservative upper bound for every structurally valid rendered candidate.

    At most two themes per scope, two views, three claims per view, three own
    passages plus title context, two parent passages and three 240-char gaps.
    JSON control characters bound escaped text bytes, not estimated tokens.
    """
    claims = []
    for source in packet['sources']:
        passages = model_source(source)['passages']
        citations = [dict(source_id=source['id'], passage_id=p['id'], quote=p['quote'],
                          role='source_title' if p['id'] == 'p0' else 'selected_passage')
                     for p in passages]
        def citation_size(citation):
            return _nested_size({k: v for k, v in citation.items() if k != 'quote'} if packet.get('theme_batch_policy') else citation)
        largest = max(citations, key=citation_size)
        selected = [largest] * 3
        title = next((c for c in citations if c['passage_id'] == 'p0'), None)
        if title and themes.scope(source) not in {'hackernews', 'x'}:
            selected = [title] + selected
        claim = dict(source_id=source['id'], text='\x00' * 220, citations=selected)
        if source.get('conversation'):
            context = sentiment_context.evidence(source, [source['conversation']['passages'][0]['id']])
            choices = [dict(context['citations'][0], passage_id=p['id'], quote=p['quote'])
                       for p in source['conversation']['passages']]
            context['citations'] = [max(choices, key=citation_size)] * 2
            claim['conversation'] = context
        claims.append(claim)
    def claim_size(claim):
        reviewed = checker.review_theme(dict(reading=dict(text=claim['text'], citations=claim['citations'], claims=[claim]), differing_view=None))
        if packet.get('theme_batch_policy'):
            projected = deepcopy(reviewed['reading']['claims'][0])
            for citation in projected['citations']:
                citation.pop('quote', None)
            for citation in (projected.get('conversation') or {}).get('citations', []):
                citation.pop('quote', None)
            return _nested_size(projected)
        return _nested_size(reviewed)
    largest = max(claims, key=claim_size)
    view = dict(text='\x00' * (220 * 3 + 2), citations=largest['citations'] * 3,
                claims=[largest] * 3)
    return dict(themes=[dict(scope=scope, title='\x00' * 90, reading=view,
                            differing_view=view, unknown='\x00' * 320, source_count=6)
                       for scope in themes.SCOPES if any(themes.scope(s) == scope for s in packet['sources'])
                       for _ in range(2)], gaps=['\x00' * 240] * 3)


def bounds(packet):
    draft = themes.request_for(packet)
    check = checker.request_for(packet, check_envelope(packet), compact=bool(packet.get("theme_batch_policy")))
    return draft, check


def fits(packet):
    if len(packet['sources']) > MAX_SOURCES:
        return False
    draft, check = bounds(packet)
    return wire_size(draft) <= MAX_BYTES and wire_size(check) <= ledger.MAX_REQUEST_BYTES


def plan(packet):
    sources = packet['sources']
    if not sources or len({s['id'] for s in sources}) != len(sources):
        raise ValueError('Discussion summaries require distinct complete sources.')
    if fits(packet):
        return [packet]
    packet = dict(packet, theme_batch_policy=POLICY)
    parts = []
    for scope in themes.SCOPES:
        selected = []
        for source in (s for s in sources if themes.scope(s) == scope):
            if selected and not fits(dict(packet, sources=selected + [source])):
                parts.append(dict(packet, sources=deepcopy(selected)))
                selected = []
            selected.append(source)
            if not fits(dict(packet, sources=selected)):
                raise ValueError('One complete source and its evidence exceed the discussion-summary limit. No new AI request was sent. The original remains readable.')
        if selected:
            parts.append(dict(packet, sources=deepcopy(selected)))
    if Counter(s['id'] for p in parts for s in p['sources']) != Counter(s['id'] for s in sources):
        raise ValueError('The discussion plan must cover every eligible source exactly once.')
    return parts


def identity(packet, parts):
    if not parts[0].get("theme_batch_policy"):
        return themes.reading_identity(parts[0])
    return 'discussion-batched:' + hashlib.sha256(ledger.canonical(dict(
        policy=POLICY, parts=[themes.reading_identity(p) for p in parts])).encode()).hexdigest()


def prior(key):
    with transaction() as conn:
        call = one(conn, 'SELECT * FROM model_calls WHERE request_key=%s', (key,))
    if call and call['status'] != 'settled':
        raise ledger.BudgetBlocked('An earlier discussion request needs charge review. No automatic retry or new batch was sent.')
    return call


def available_plan(packet):
    # A completed whole-sample draft is already paid for. Reuse it, including
    # its exact failure, instead of silently paying to redraft smaller parts.
    legacy = dict(packet, theme_legacy_request=True)
    for version in (packet, legacy):
        previous = prior(themes.identity(version))
        if previous:
            candidate = themes.render(previous, version)
            for compact in (False, True):
                check = checker.request_for(version, candidate, compact=compact)
                if wire_size(check) <= ledger.MAX_REQUEST_BYTES:
                    return [dict(version, theme_batch_policy=POLICY)] if compact else [version]
            raise ValueError('The saved draft exceeds the complete evidence-check limit. No new AI request was sent; the original paid draft remains saved.')
    # Preserve paid v8 batch identities even if the stricter v9 schema changes
    # partition sizes. Only unsent batches use the new schema; they can be split
    # further, never shortened. Reconstruct this same plan on every continuation.
    legacy_parts = plan(legacy)
    saved = [prior(themes.identity(part)) for part in legacy_parts]
    if any(saved):
        parts = []
        for part, call in zip(legacy_parts, saved):
            if call:
                themes.render(call, part)  # All paid failures block before new work.
                parts.append(part)
            else:
                parts.extend(plan({k: v for k, v in part.items() if k != 'theme_legacy_request'}))
        return parts
    return plan(packet)


def preflight(parts):
    needed = 0
    saved_drafts = 0
    normalized_titles = 0
    for part in parts:
        draft, check_bound = bounds(part)
        # Both requests must fit before ANY new dispatch. Existing paid failures
        # are also checked up front rather than billed again under a new key.
        draft_max = ledger.estimate(draft)
        previous = prior(themes.identity(part))
        if previous:
            saved_drafts += 1
            candidate = themes.render(previous, part)
            normalized_titles += len((candidate.get('citation_normalization') or {}).get('title_references', []))
            check = checker.request_for(part, candidate, compact=bool(part.get("theme_batch_policy")))
            if wire_size(check) > wire_size(check_bound):
                raise ValueError('The saved evidence exceeds the planned size. No new AI request was sent.')
            checked = prior(checker.identity(part, candidate, compact=bool(part.get("theme_batch_policy"))))
            if checked:
                checker.apply(checked, candidate)
            else:
                needed += ledger.estimate(check)
        else:
            needed += draft_max + ledger.estimate(check_bound)
    budget = ledger.snapshot()
    maximum = Decimal(needed) / ledger.NANO
    available = Decimal(budget['remaining_usd'])
    if maximum > available:
        raise ledger.BudgetBlocked(
            f'The complete discussion summary needs a maximum allowance of US${maximum:.4f}; '
            f'US${available:.4f} is available. No new AI request was sent. Saved steps remain available.')
    return dict(batches=len(parts), sources=sum(len(p['sources']) for p in parts),
                maximum_new_usd=str(maximum), available_usd=str(available),
                saved_drafts=saved_drafts, normalized_title_references=normalized_titles)


def run(packet, parts, *, transport=None):
    preflight(parts)
    completed, calls, checks = [], [], []
    for index, part in enumerate(parts, 1):
        try:
            with transaction() as conn:
                themes.prepare(conn, packet['instrument_id'], packet['analysis_id'])
            call = prior(themes.identity(part))
            if not call:
                assert not part.get('theme_legacy_request'), 'Legacy requests are read-only cache identities.'
                call = ledger.execute(themes.identity(part), themes.PROMPT,
                                      themes.request_for(part), transport=transport)
            candidate = themes.render(call, part)
            with transaction() as conn:
                themes.prepare(conn, packet['instrument_id'], packet['analysis_id'])
            check = checker.request_for(part, candidate, compact=bool(part.get("theme_batch_policy")))
            if wire_size(check) > wire_size(bounds(part)[1]):
                raise ValueError('The generated evidence exceeds the planned size. No checking request was sent.')
            checked = ledger.execute(checker.identity(part, candidate, compact=bool(part.get("theme_batch_policy"))), checker.POLICY,
                                     check, transport=transport)
            completed.append(checker.apply(checked, candidate))
            calls.append(call); checks.append(checked)
        except ValueError as exc:
            if len(parts) == 1:
                raise
            raise ValueError(f'Discussion batch {index} of {len(parts)} stopped. {exc} '
                             'Completed steps remain saved. No combined summary was published and no automatic retry was made.') from None
    if not parts[0].get("theme_batch_policy"):
        return completed[0], calls[0]['id']
    result = deepcopy(completed[0])
    result.update(
        themes=[dict(t, batch=index) for index, r in enumerate(completed, 1) for t in r['themes']],
        gaps=[f'Batch {index}: {gap}' for index, r in enumerate(completed, 1) for gap in r['gaps']],
        limitation=themes.LIMITATION + ' ' + NOTE,
        batching=dict(policy=POLICY, completed=len(parts), sources=len(packet['sources']),
                      parts=[dict(index=index, source_ids=[s['id'] for s in p['sources']],
                                  scopes=list(dict.fromkeys(themes.scope(s) for s in p['sources'])),
                                  synthesis_call_id=str(c['id']), checking_call_id=str(k['id']),
                                  prompt_version=r['prompt_version'],
                                  citation_normalization=r.get('citation_normalization'))
                             for index, (p,c,k,r) in enumerate(zip(parts,calls,checks,completed), 1)]),
        evidence_check=dict(policy=checker.POLICY, call_id=str(checks[0]['id']),
                            call_ids=[str(c['id']) for c in checks], limitation=checker.NOTE,
                            withheld_themes=sum(r['evidence_check']['withheld_themes'] for r in completed),
                            withheld_gaps=sum(r['evidence_check']['withheld_gaps'] for r in completed)))
    return result, calls[0]['id']


@contextmanager
def reading_lock(iid):
    with psycopg.connect(dsn(), autocommit=True) as conn:
        acquired = conn.execute("SELECT pg_try_advisory_lock(hashtextextended(%s,0))", ("discussion-company:" + str(iid),)).fetchone()[0]
        if not acquired:
            raise ValueError("A discussion summary is already running for this company.")
        yield


def preview(conn, iid, aid):
    try:
        packet = themes.prepare(conn, iid, aid)
        parts = available_plan(packet)
        old = one(conn, "SELECT * FROM discussion_theme_reviews WHERE request_key=ANY(%s)",
                  ([themes.reading_identity(packet), identity(packet, parts)],))
        if old:
            return dict(batches=len(parts), sources=len(packet['sources']), maximum_new_usd='0', cached=True)
        return preflight(parts)
    except ValueError as exc:
        return dict(blocked_reason=str(exc))
