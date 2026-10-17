"""Read-only inventory of exact saved-label candidates for a frozen news replay.

No model dispatch, source fetch, app write or noise/accuracy acceptance claim.
Later labels are explicitly separate from labels already available at a frame.
"""
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from thesis.providers import ledger  # noqa:E402
from thesis.research import (sentiment, sentiment_tasks, sentiment_reuse,
    sentiment_context, reddit_thread_context, sentiment_guards, reporting_basis,
    relevance_prefilter)  # noqa:E402
from thesis.research.citations import model_source  # noqa:E402

POLICY = 'noise-replay-readiness-1'
POLICIES = dict(reporting_policy=reporting_basis.POLICY,
    context_policy=sentiment_context.POLICY,
    reddit_thread_policy=reddit_thread_context.POLICY,
    guard_policy=sentiment_guards.POLICY)


def digest(value):
    return hashlib.sha256(ledger.canonical(value).encode()).hexdigest()


def instant(value):
    value = datetime.fromisoformat(value) if isinstance(value, str) else value
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('Replay timestamps must include their timezone.')
    return value.astimezone(timezone.utc)


def validate(capture):
    if (capture.get('policy') != 'saved-news-noise-inputs-1'
            or digest({k:v for k,v in capture.items() if k != 'fingerprint'}) != capture.get('fingerprint')):
        raise ValueError('The frozen news capture changed.')
    start, end = instant(capture['window_start']), instant(capture['window_end'])
    if end - start != timedelta(days=7):
        raise ValueError('The inventory requires the complete seven-day input window.')
    companies = {c['instrument_id']:c for c in capture['companies']}
    if len(companies) != len(capture['companies']):
        raise ValueError('Duplicate replay company.')
    for sid, source in capture['sources'].items():
        if (sid != source['id'] or source['instrument_id'] not in companies or source['channel'] != 'news'
                or model_source(source)['passages'] != source['passages']):
            raise ValueError('A replay source differs from its model-visible evidence.')
        instant(source['published_at']); instant(source['available_at'])
    prior = None
    opportunities = set()
    for frame in capture['frames']:
        cutoff = instant(frame['cutoff'])
        order = (cutoff, frame['symbol'])
        if not start <= cutoff < end or (prior is not None and order < prior):
            raise ValueError('Replay frames must be ordered and within the input window.')
        prior = order
        company = companies.get(frame['instrument_id'])
        if not company or company['symbol'] != frame['symbol'] or type(frame['initial_baseline']) is not bool:
            raise ValueError('A replay frame has inconsistent company or baseline metadata.')
        target = frame['source_ids']; previous = frame['comparison_source_ids']
        if not target or len(set(target + previous)) != len(target + previous):
            raise ValueError('Replay sources must be distinct within each frame.')
        for sid in target + previous:
            source = capture['sources'].get(sid)
            if (not source or source['instrument_id'] != frame['instrument_id']
                    or instant(source['available_at']) > cutoff
                    or not cutoff - timedelta(days=7) <= instant(source['published_at']) <= cutoff):
                raise ValueError('Replay evidence was unavailable or outside its historical window.')
        for sid in target:
            if sid in opportunities:
                raise ValueError('A source may enter the replay only once.')
            opportunities.add(sid)
    return capture


def candidate(record, source, item):
    """Conservative inventory only; preserve original model/call and policy."""
    packet, result = record['packet'], record['result']
    if (result.get('prompt_version') not in {sentiment.PROMPT, sentiment_tasks.PROMPT}
            or result.get('summary_policy') != sentiment.POLICY
            or result.get('guard_policy') != sentiment_guards.POLICY
            or any(packet.get(k) != v for k,v in POLICIES.items())):
        return False
    if (item.get('source_id') != source['id'] or item.get('channel') != 'news'
            or item.get('relevance') not in {'relevant','unrelated','unclear'}
            or item.get('sentiment') not in {'positive','negative','mixed','neutral','unclear'}
            or (item.get('relevance') != 'relevant' and item.get('sentiment') != 'unclear')):
        return False
    if item.get('prefilter'):
        return ((result.get('prefilter') or {}).get('policy') == relevance_prefilter.POLICY
                and item['relevance'] == 'unrelated')
    passages = {p['id']:p['quote'] for p in source['passages']}
    citations = item.get('citations') or []
    return bool(citations) and all(c.get('source_id') == source['id']
        and c.get('passage_id') in passages and passages[c['passage_id']] == c.get('quote') for c in citations)


def assess(capture, records):
    validate(capture)
    wanted = capture['sources']; found = {}; mismatch = set(); rejected = set(); analysed = 0
    # No labels are exported: only exact-match eligibility and original provenance.
    for record in records:
        analysed += 1
        packet = record['packet']; sources = {s['id']:s for s in packet.get('sources',[])}
        for item in record['result'].get('items',[]):
            sid = item.get('source_id'); saved = sources.get(sid); current = wanted.get(sid)
            if not current or not saved:
                continue
            if (str(packet.get('instrument_id')) != current['instrument_id']
                    or model_source(saved)['passages'] != saved['passages']
                    or sentiment_reuse.content_key(saved) != sentiment_reuse.content_key(current)):
                mismatch.add(sid); continue
            if not candidate(record, saved, item):
                rejected.add(sid); continue
            quick = record['result'].get('prefilter') or {}
            provenance = dict(analysis_id=str(record['id']),
                analysis_created_at=instant(record['created_at']).isoformat(),
                call_id=None if item.get('prefilter') else str(item.get('call_id') or record['call_id']),
                call_ids=(item.get('call_ids') or quick.get('call_ids',[])) if item.get('prefilter') else [],
                model=item.get('model') or (quick.get('model') if item.get('prefilter') else record['result'].get('model')),
                prompt_version=item.get('prompt_version') or record['result'].get('prompt_version'),
                prefilter=bool(item.get('prefilter')))
            # Prefer the earliest exact answer so historical-availability counts
            # do not depend on query ordering or silently use a future reading.
            if sid not in found or instant(provenance['analysis_created_at']) < instant(found[sid]['analysis_created_at']):
                found[sid] = provenance
    days = {}; needed = set(); initial = 0
    for frame in capture['frames']:
        day = instant(frame['cutoff']).astimezone(timezone(timedelta(hours=8))).date().isoformat()
        stats = days.setdefault(day, Counter(frames=0, opportunities=0, saved_candidates=0,
            already_available=0, later_identical_evidence=0, missing=0))
        stats['frames'] += 1
        if frame['initial_baseline']:
            initial += 1; continue
        for sid in frame['source_ids']:
            needed.add(sid); stats['opportunities'] += 1
            if sid not in found:
                stats['missing'] += 1; continue
            stats['saved_candidates'] += 1
            key = 'already_available' if instant(found[sid]['analysis_created_at']) <= instant(frame['cutoff']) else 'later_identical_evidence'
            stats[key] += 1
    summary = Counter()
    for stats in days.values(): summary.update(stats)
    return dict(policy=POLICY, input_fingerprint=capture['fingerprint'], source_versions=len(wanted),
        analyses_examined=analysed, initial_quiet_frames=initial, by_day=days, totals=summary,
        exact_candidates={sid:found[sid] for sid in sorted(needed & found.keys())},
        unmatched_evidence_versions=len((needed-found.keys()) & mismatch),
        rejected_policy_or_evidence=len((needed-found.keys()) & rejected),
        paid_calls=0, app_writes=0, completed_noise_days=0, noise_gate_passed=False,
        limitations=['Candidate inventory only; not production reuse, event predictions, or a routing replay.',
            'Source permissions belong to the input capture; actual reuse requires fresh access checks.',
            'Later identical-evidence answers are not represented as historically available.',
            'Original models and prompt policies remain; no new-prompt accuracy is inferred.',
            'Google headline-only projection must match exactly; old cluster bodies are not substituted.',
            'Importance/duplicate evaluation and independent low-value review remain required.'])


def collect(conn, capture):
    if conn.execute('SHOW transaction_read_only').fetchone()['transaction_read_only'] != 'on':
        raise ValueError('The inventory requires a database-enforced read-only transaction.')
    return assess(capture, conn.execute('SELECT id,call_id,created_at,packet,result FROM sentiment_analyses '
        'WHERE instrument_id=ANY(%s::uuid[]) AND created_at>=%s ORDER BY created_at,id',
        ([c['instrument_id'] for c in capture['companies']], instant(capture['window_start'])-timedelta(days=7))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    capture = validate(json.loads(args.capture.read_text()))
    if args.output.exists(): raise SystemExit('Choose a new output path; prior evidence is preserved.')
    import psycopg
    from psycopg.rows import dict_row
    from thesis.config import dsn
    with psycopg.connect(dsn('thesis_local'), row_factory=dict_row,
            options='-c default_transaction_read_only=on') as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        report = collect(conn, capture)
    with args.output.open('x') as output:
        output.write(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'exact_candidates'}, indent=2))
