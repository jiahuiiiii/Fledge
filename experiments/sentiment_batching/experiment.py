"""Evaluation-only source batching. No app publication, acquisition or retries."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import argparse
import hashlib
import json
import time

from thesis.providers import ledger
from thesis.research import sentiment, sentiment_context
from thesis.config import OWNER
from thesis.db import transaction


def digest(value):
    return hashlib.sha256(ledger.canonical(value).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    # Evidence is append-only; a rerun must inspect, not replace, earlier output.
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2, default=str, ensure_ascii=False)


def batches(packet, size):
    """Whole sources plus their own parents; retain all news comparison context."""
    if not isinstance(size, int) or size < 1 or not packet['sources']:
        raise ValueError('A positive batch size and nonempty sample are required')
    sources = packet['sources']
    if len({s['id'] for s in sources}) != len(sources):
        raise ValueError('Duplicate source identity')
    output = []
    for start in range(0, len(sources), size):
        part = deepcopy(packet)
        part['sources'] = deepcopy(sources[start:start + size])
        target_ids = {s['id'] for s in part['sources']}
        part['comparison_sources'] = deepcopy(packet.get('comparison_sources', [])) + [
            deepcopy(s) for s in sources
            if s['channel'] == 'news' and s['id'] not in target_ids
        ]
        output.append(part)
    return output


def raw_result(call):
    raw = call['response_body']
    texts = [p['text'] for item in raw.get('output', []) if item.get('type') == 'message'
             for p in item.get('content', []) if p.get('type') == 'output_text']
    if raw.get('status') != 'completed' or len(texts) != 1:
        raise ValueError('Provider response incomplete: ' + str(raw.get('incomplete_details')))
    return sentiment.Classification.model_validate_json(texts[0]).model_dump()


def combine(packet, parts, calls):
    if len(parts) != len(calls):
        raise ValueError('Every batch needs a result')
    expected = Counter(s['id'] for s in packet['sources'])
    if Counter(s['id'] for p in parts for s in p['sources']) != expected:
        raise ValueError('Batch partition dropped or duplicated a source')
    combined = {'items': [], 'coverage_links': []}
    for part, call in zip(parts, calls):
        sentiment.render(call, part)
        raw = raw_result(call)
        combined['items'].extend(raw['items'])
        combined['coverage_links'].extend(raw['coverage_links'])
    # Revalidate relationships with ALL source classifications present, and
    # count/deduplicate once globally. Never average batch percentages.
    synthetic = {'response_body': {'status': 'completed', 'output': [
        {'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(combined)}]}
    ]}}
    return sentiment.render(synthetic, packet)


def check_access(packet):
    if packet.get('experiment_authored'):
        return
    with transaction() as conn:
        allowed = sentiment.permitted_ids(conn, {'packet': packet, 'instrument_id': packet['instrument_id']})
        if any(s['id'] not in allowed or not sentiment_context.allowed(conn, s)
               for s in packet['sources'] + packet.get('comparison_sources', [])):
            raise ValueError('Frozen source permission or parent access changed')


def run(folder, live=False):
    folder = Path(folder)
    protocol = read(folder / 'protocol.json')
    if not live:
        raise ValueError('Paid experiment requires explicit --live')
    if digest(read(folder / 'criteria.json')) != protocol['criteria_hash']:
        raise ValueError('Predeclared evaluation criteria changed')
    starting_budget = read(folder / 'budget-before.json')
    starting_spend = float(starting_budget['spent_usd'])
    starting_reserve = float(starting_budget['reserved_usd'])
    for trial in protocol['trials']:
        target = folder / 'runs' / trial['name']
        target.mkdir(parents=True, exist_ok=True)
        if any((target / name).exists() for name in ('result.json','failure.json','interruption.json')):
            continue
        packet = read(folder / (trial['cohort'] + '-packet.json'))
        if digest(packet) != protocol['packets'][trial['cohort']]:
            raise ValueError('Frozen packet changed')
        parts = batches(packet, trial['batch_size'])
        calls, metrics = [], []
        for index, part in enumerate(parts):
            body = sentiment.request_for(part)
            if digest(body) != trial['request_hashes'][index]:
                raise ValueError('Frozen instructions/request changed')
            check_access(packet)
            budget = ledger.snapshot()
            maximum = ledger.estimate(body) / ledger.NANO
            committed = (float(budget['spent_usd']) - starting_spend
                         + float(budget['reserved_usd']) - starting_reserve)
            if committed + maximum > protocol['maximum_incremental_usd']:
                raise ValueError('Experiment ceiling reached; no dispatch')
            prefix = target / str(index + 1)
            key = 'sentiment-batching-eval:' + protocol['id'] + ':' + trial['name'] + ':' + str(index)
            if not prefix.with_suffix('.request.json').exists():
                save(prefix.with_suffix('.request.json'), body)
            print(json.dumps({'starting': trial['name'], 'part': index + 1, 'of': len(parts),
                              'max_usd': maximum}), flush=True)
            started = time.monotonic()
            # Serial, same original ledger/profile, a distinct predeclared trial
            # identity. Unknown charges stop the entire experiment immediately.
            call = ledger.execute(key, 'experiment:sentiment-batching-v1:' + trial['name'], body, owner=OWNER)
            elapsed = time.monotonic() - started
            calls.append(call)
            if not prefix.with_suffix('.call.json').exists():
                save(prefix.with_suffix('.call.json'), call)
            metric = {'part': index + 1, 'seconds': elapsed, 'call_id': str(call['id']),
                      'cost_usd': call['charged_nano_usd'] / ledger.NANO,
                      'input_tokens': call['input_tokens'], 'cached_tokens': call['cached_tokens'],
                      'output_tokens': call['output_tokens'],
                      'reasoning_tokens': call['response_body'].get('usage', {}).get('output_tokens_details', {}).get('reasoning_tokens'),
                      'status': call['response_body'].get('status'),
                      'incomplete_details': call['response_body'].get('incomplete_details')}
            if prefix.with_suffix('.metrics.json').exists():
                metric = read(prefix.with_suffix('.metrics.json'))
            metrics.append(metric)
            if not prefix.with_suffix('.metrics.json').exists():
                save(prefix.with_suffix('.metrics.json'), metric)
            print(json.dumps({'finished': trial['name'], **metric}), flush=True)
        check_access(packet)
        save(target / 'metrics.json', metrics)
        try:
            result = combine(packet, parts, calls)
            save(target / 'result.json', result)
            print(json.dumps({'trial': trial['name'], 'valid': True}), flush=True)
        except ValueError as exc:
            save(target / 'failure.json', {'error': str(exc)})
            print(json.dumps({'trial': trial['name'], 'valid': False, 'error': str(exc)}), flush=True)
    save(folder / 'budget-after.json', ledger.snapshot())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--folder', required=True)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    run(args.folder, args.live)
