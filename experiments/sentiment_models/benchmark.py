"""Offline sentiment comparison; no Thesis imports, DB writes or hosted inference.

Prepare freezes source/label/input hashes BEFORE inference. Download fetches only
official pinned model artifacts. Run requires all weights locally and makes no
network requests. Existing run outputs are never overwritten.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import time

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / '.local/live-tests/local-sentiment-phase76'
LABELS = ('negative', 'neutral', 'positive')
MODELS = {
    'prosus_finbert': ('ProsusAI/finbert', '4556d13015211d73dccd3fdd39d39232506f3e43'),
    'cardiff_social': ('cardiffnlp/twitter-roberta-base-sentiment-latest', '3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7'),
    'hkust_finbert': ('yiyanghkust/finbert-tone', '4921590d3c0c3832c0efea24c8381ce0bda7844b'),
}
CORPORA = (
    ('phase74', 'sentiment-readiness-20261005-phase74-event-impact', ('NVDA', 'AMZN', 'META')),
    ('phase47', 'sentiment-extracts-20261003T072024Z', ('sentiment-MSFT', 'sentiment-NVDA', 'sentiment-AMZN', 'sentiment-AUTHORED')),
)


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def save(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write('\n')


def read(path):
    return json.loads(path.read_text())


def source_text(source):
    # Own selected source passages only: never duplicate the title by adding text
    # separately, never treat an HN thread title or parent as the child's speech.
    passages = source['passages']
    selected = [p['quote'] for p in passages if not (
        source.get('platform') == 'hackernews' and p['id'] == 'p0'
    )]
    text = '\n'.join(selected).strip()
    if not text or len(text) > 200_000:
        raise ValueError('Empty or unexpectedly large source; no silent truncation')
    return text


def scoring_group(expected):
    if not expected:
        return 'unlabelled'
    if len(expected) == 1 and expected[0] in LABELS:
        return 'strict_three_way'
    if all(x in LABELS for x in expected):
        return 'multiple_acceptable_three_way'
    return 'outside_three_way_contract'


def prepare(folder):
    folder.mkdir(parents=True, exist_ok=True)
    rows, files, omitted, unusable = [], {}, [], []
    for phase, directory, names in CORPORA:
        origin = ROOT / '.local/live-tests' / directory
        frozen_path = origin / 'frozen.json'
        frozen = read(frozen_path)
        files[str(frozen_path.relative_to(ROOT))] = digest(frozen_path.read_bytes())
        for name in names:
            case = frozen['cases'][name]
            packet = case['packet']
            result_path = origin / f'{name}-result.json'
            result = read(result_path)
            files[str(result_path.relative_to(ROOT))] = digest(result_path.read_bytes())
            baseline = {r['id']: r for r in result['items']}
            expectations = case.get('expected_tones', case.get('retention', {}).get('tones', {}))
            present = {s['label'] for s in packet['sources']}
            omitted.extend(f'{phase}:{name}:{key}' for key in expectations if key not in present)
            for source in packet['sources']:
                expected = expectations.get(source['label'], [])
                if source.get('platform') == 'hackernews' and not any(p['id'] != 'p0' for p in source['passages']):
                    unusable.append({'id': f'{phase}:{name}:{source["label"]}',
                                     'expected': expected, 'reason': 'No eligible child body passage; generic thread title is not evidence.'})
                    continue
                text = source_text(source)
                old = baseline.get(source['label'])
                if old and old.get('source_id') != source['id']:
                    raise ValueError('Baseline/source identity mismatch')
                rows.append({
                    'id': f'{phase}:{name}:{source["label"]}',
                    'phase': phase, 'case': name, 'company': packet['company'],
                    'kind': 'authored' if 'AUTHORED' in name else 'retained_actual',
                    'source_id': source['id'], 'channel': source['channel'],
                    'platform': source.get('platform'), 'title': source['title'],
                    'url': source.get('url'), 'published_at': source.get('published_at'),
                    'source_content_hash': source.get('content_hash'),
                    'input_text': text, 'input_sha256': digest(text),
                    'parent_supplied_to_original_model': bool(source.get('conversation')),
                    'expected': expected, 'scoring_group': scoring_group(expected),
                    'baseline_label': old.get('sentiment') if old else None,
                    'baseline_method': result.get('prompt_version'),
                })
    protocol = {
        'version': 'local-sentiment-comparison-1', 'created_at_unix': time.time(),
        'frozen_labels': 'Historical developer-authored expectations; no new labels or tuning.',
        'input': 'Own saved passages in order, including title once except HN generic thread title; no parent or comparison-source concatenation.',
        'long_input': 'Full input tokenized without truncation; disjoint chunks of 512 minus special tokens; token-count-weighted mean softmax; argmax. VADER processes full text.',
        'cardiff_preprocess': 'Official whitespace-token @mention and http URL placeholders.',
        'metric': 'Strict singleton positive/neutral/negative accuracy and macro-F1, by phase/kind/channel. Multi-acceptable and mixed/unclear separate. Unlabelled sources unscored.',
        'baseline': 'Previously saved OpenAI result, no new API call. Original model had company, source metadata and sometimes parent/comparison context; local models are untuned whole-text classifiers. Phase47 is historical v10, not current v16.',
        'limits': 'Retrospective difficult-case developer corpus; not independent, representative, calibration, alert quality or market-direction evidence. Do not pool overlapping phase corpora as independent observations.',
        'adoption': 'Evaluation only; no automatic model replacement, voting, alert filter or confidence threshold.',
        'models': MODELS, 'source_files_sha256': files,
        'expected_but_not_in_packet': omitted,
        'sources_without_eligible_body': unusable,
        'row_count': len(rows), 'unique_inputs': len({r['input_sha256'] for r in rows}),
    }
    # Refuse overwriting either artifact, including a partially existing run.
    if (folder / 'protocol.json').exists() or (folder / 'inputs.json').exists():
        raise FileExistsError('Choose a new benchmark directory')
    save(folder / 'inputs.json', rows)
    protocol['inputs_sha256'] = digest((folder / 'inputs.json').read_bytes())
    save(folder / 'protocol.json', protocol)
    print(json.dumps({k: protocol[k] for k in ['row_count', 'unique_inputs', 'expected_but_not_in_packet']}), flush=True)


def download(folder):
    from huggingface_hub import snapshot_download
    for key, (repo, revision) in MODELS.items():
        print('Downloading official pinned artifacts:', key, flush=True)
        snapshot_download(repo, revision=revision, token=False,
            local_dir=folder / 'models' / key,
            allow_patterns=['config.json', '*token*.json', 'vocab.*', 'merges.txt', 'pytorch_model.bin', 'README.md'],
            max_workers=2)


def normalized_labels(mapping):
    labels = [mapping[i].lower() for i in range(3)]
    if set(labels) != set(LABELS):
        raise ValueError(f'Unexpected model class mapping: {mapping}')
    return labels


def chunks(ids, size):
    if not ids or size < 1:
        raise ValueError('Nonempty tokens and positive chunk size required')
    return [ids[i:i + size] for i in range(0, len(ids), size)]


def weighted_scores(scores, weights):
    if not scores or len(scores) != len(weights) or any(w <= 0 for w in weights):
        raise ValueError('Invalid chunk scores/weights')
    total = sum(weights)
    return {label: sum(s[label] * w for s, w in zip(scores, weights)) / total for label in LABELS}


def preprocess_cardiff(text):
    return ' '.join('@user' if t.startswith('@') and len(t) > 1 else 'http' if t.startswith('http') else t for t in text.split(' '))


def encode_chunk(tokenizer, part):
    # All three pinned models use a single CLS/BOS and SEP/EOS. Verify this
    # against each real tokenizer before inference; no decode/re-encode loss.
    ids = [tokenizer.cls_token_id, *part, tokenizer.sep_token_id]
    result = {'input_ids': ids, 'attention_mask': [1] * len(ids)}
    if 'token_type_ids' in tokenizer.model_input_names:
        result['token_type_ids'] = [0] * len(ids)
    return result


def vader_label(compound):
    return 'positive' if compound >= .05 else 'negative' if compound <= -.05 else 'neutral'


def run(folder, name):
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    protocol, rows = read(folder / 'protocol.json'), read(folder / 'inputs.json')
    if digest((folder / 'inputs.json').read_bytes()) != protocol['inputs_sha256']:
        raise ValueError('Frozen inputs changed')
    output = folder / f'{name}-predictions.json'
    if output.exists():
        raise FileExistsError(output)
    started = time.perf_counter()
    metadata = {'model': name, 'protocol_sha256': digest((folder / 'protocol.json').read_bytes()),
                'input_sha256': protocol['inputs_sha256'], 'python': platform.python_version(),
                'machine': platform.machine(), 'device': 'cpu', 'cpu_threads': 2,
                'packages': {k: importlib.metadata.version(k) for k in ('torch', 'transformers', 'vaderSentiment')}}
    if name == 'vader':
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        analyzer = SentimentIntensityAnalyzer()
    else:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer, BertForSequenceClassification, BertTokenizer
        torch.set_num_threads(2)
        model_path = folder / 'models' / name
        metadata['repository'], metadata['revision'] = MODELS[name]
        metadata['weights_sha256'] = digest((model_path / 'pytorch_model.bin').read_bytes())
        if name == 'hkust_finbert':
            # The authors' legacy config omits model_type/tokenizer metadata.
            # Use their documented explicit BERT classes instead of path-name
            # inference; the original BertTokenizer defaults to lowercasing.
            tokenizer = BertTokenizer(vocab=str(model_path / 'vocab.txt'), do_lower_case=True)
            model_class = BertForSequenceClassification
            metadata['tokenizer_policy'] = 'Explicit BertTokenizer, original default do_lower_case=True'
        else:
            tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True, trust_remote_code=False)
            model_class = AutoModelForSequenceClassification
        # Official repos currently ship .bin weights; restricted weights-only
        # loading via current Torch, never untrusted custom model code.
        model = model_class.from_pretrained(model_path, local_files_only=True,
            trust_remote_code=False, use_safetensors=False, weights_only=True).eval()
        if len(tokenizer) != model.get_input_embeddings().num_embeddings:
            raise ValueError('Tokenizer vocabulary does not match model embeddings')
        mapping = normalized_labels(model.config.id2label)
        metadata['id2label'] = model.config.id2label
        size = 512 - tokenizer.num_special_tokens_to_add(pair=False)
        probe = 'This is a short sample.'
        probe_ids = tokenizer.encode(probe, add_special_tokens=False)
        if size != 510 or encode_chunk(tokenizer, probe_ids)['input_ids'] != tokenizer.encode(probe):
            raise ValueError('Unexpected special-token layout for pinned model')
    metadata['load_seconds'] = time.perf_counter() - started
    cache, predictions = {}, []
    inference_start = time.perf_counter()
    for row in rows:
        key = row['input_sha256']
        if key not in cache:
            text = row['input_text']
            if name == 'vader':
                scores = analyzer.polarity_scores(text)
                prediction = {'label': vader_label(scores['compound']), 'scores': scores,
                              'score_meaning': 'Lexicon valence, NOT probabilities or confidence.', 'chunks': 1, 'truncated': False}
            else:
                if name == 'cardiff_social':
                    text = preprocess_cardiff(text)
                tokens = tokenizer.encode(text, add_special_tokens=False, truncation=False)
                parts = chunks(tokens, size)
                all_scores = []
                with torch.inference_mode():
                    for part in parts:
                        encoded = encode_chunk(tokenizer, part)
                        tensors = {k: torch.tensor([v]) for k, v in encoded.items() if k in tokenizer.model_input_names}
                        probabilities = model(**tensors).logits.softmax(-1)[0].tolist()
                        all_scores.append(dict(zip(mapping, probabilities)))
                scores = weighted_scores(all_scores, [len(p) for p in parts])
                prediction = {'label': max(scores, key=scores.get), 'scores': scores,
                    'score_meaning': 'Uncalibrated weighted model softmax, NOT probability of correctness.',
                    'tokens': len(tokens), 'chunks': len(parts), 'chunk_scores': all_scores,
                    'chunk_token_counts': [len(p) for p in parts], 'truncated': False}
            cache[key] = prediction
        predictions.append({'id': row['id'], 'input_sha256': key, **cache[key]})
    metadata['inference_seconds'] = time.perf_counter() - inference_start
    metadata['rows'] = len(predictions)
    metadata['unique_inputs'] = len(cache)
    save(output, {'metadata': metadata, 'predictions': predictions})
    print(json.dumps(metadata), flush=True)


def metrics(pairs):
    confusion = {a: {b: 0 for b in (*LABELS, 'other')} for a in LABELS}
    for actual, prediction in pairs:
        confusion[actual][prediction if prediction in LABELS else 'other'] += 1
    f1s = []
    for label in LABELS:
        tp = confusion[label][label]
        fp = sum(confusion[a][label] for a in LABELS if a != label)
        fn = sum(confusion[label][b] for b in (*LABELS, 'other') if b != label)
        f1s.append(2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0)
    count = len(pairs)
    correct = sum(a == b for a, b in pairs)
    return {'n': count, 'correct': correct, 'accuracy': correct / count if count else None,
            'macro_f1_three_fixed_labels': sum(f1s) / 3 if count else None, 'confusion': confusion}


def summarize(folder):
    rows = read(folder / 'inputs.json')
    models = {name: {p['id']: p for p in read(folder / f'{name}-predictions.json')['predictions']}
              for name in (*MODELS, 'vader')}
    summary = {}
    csv_rows = []
    for phase, kind in [('phase74', 'retained_actual'), ('phase47', 'retained_actual'), ('phase47', 'authored')]:
        cohort = [r for r in rows if r['phase'] == phase and r['kind'] == kind]
        for channel in ['all', 'news', 'social']:
            group = [r for r in cohort if r['scoring_group'] == 'strict_three_way' and (channel == 'all' or r['channel'] == channel)]
            summary[f'{phase}/{kind}/{channel}'] = {
                name: metrics([(r['expected'][0], r['baseline_label'] if name == 'saved_openai' else model[r['id']]['label']) for r in group])
                for name, model in [('saved_openai', {}), *models.items()]}
    for row in rows:
        result = {k: row[k] for k in ['id', 'phase', 'kind', 'channel', 'platform', 'title', 'baseline_label', 'baseline_method', 'scoring_group', 'parent_supplied_to_original_model']}
        result['expected'] = '|'.join(row['expected'])
        for name, model in models.items():
            result[name] = model[row['id']]['label']
            result[name + '_chunks'] = model[row['id']]['chunks']
        csv_rows.append(result)
    save(folder / 'summary.json', summary)
    with (folder / 'comparison.csv').open('x', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(csv_rows[0])); writer.writeheader(); writer.writerows(csv_rows)
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'download', 'run', 'summarize'])
    parser.add_argument('--folder', type=Path, default=DEFAULT)
    parser.add_argument('--model', choices=[*MODELS, 'vader'])
    args = parser.parse_args()
    if args.action == 'run':
        if not args.model:
            parser.error('--model required for run')
        run(args.folder, args.model)
    else:
        globals()[args.action](args.folder)


if __name__ == '__main__':
    main()
