"""Offline comparison of local sentiment models against the owner's 50 labels.

No Thesis imports, database, .env, hosted inference or network. Reads the
frozen owner manifest and answers read-only, runs the already-downloaded pinned
weights from benchmark.py, and writes a new output folder (never overwrites).
The app's own labels come from the saved disagreement list: every case not in
it matched the owner exactly.
"""
from __future__ import annotations

import collections
import json
import os
from pathlib import Path
import sys

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
sys.path.insert(0, str(Path(__file__).resolve().parent))
import benchmark as b  # noqa: E402

ROOT = b.ROOT
MANIFEST = ROOT / '.local/live-tests/redesign-phase-5-20261017/owner-quality-50/manifest.json'
SCORED = ROOT / '.local/live-tests/redesign-phase-5-20261018/owner-score-v1'
OUT = ROOT / '.local/live-tests/finbert-owner-comparison-20261026'
MODELS = ('prosus_finbert', 'hkust_finbert', 'cardiff_social', 'vader')
THREE = ('positive', 'negative', 'neutral')


def predict(name, texts):
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, BertForSequenceClassification, BertTokenizer
    torch.set_num_threads(2)
    if name == 'vader':
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        an = SentimentIntensityAnalyzer()
        return [b.vader_label(an.polarity_scores(t)['compound']) for t in texts]
    path = ROOT / '.local/live-tests/local-sentiment-phase76/models' / name
    if name == 'hkust_finbert':
        tok = BertTokenizer(vocab=str(path / 'vocab.txt'), do_lower_case=True)
        cls = BertForSequenceClassification
    else:
        tok = AutoTokenizer.from_pretrained(path, local_files_only=True)
        cls = AutoModelForSequenceClassification
    model = cls.from_pretrained(path, local_files_only=True, use_safetensors=False, weights_only=True).eval()
    mapping = b.normalized_labels(model.config.id2label)
    out = []
    for text in texts:
        if name == 'cardiff_social':
            text = b.preprocess_cardiff(text)
        parts = b.chunks(tok.encode(text, add_special_tokens=False), 510)
        scores = []
        with torch.inference_mode():
            for part in parts:
                enc = b.encode_chunk(tok, part)
                t = {k: torch.tensor([v]) for k, v in enc.items() if k in tok.model_input_names}
                scores.append(dict(zip(mapping, model(**t).logits.softmax(-1)[0].tolist())))
        w = b.weighted_scores(scores, [len(p) for p in parts])
        out.append(max(w, key=w.get))
    return out


def main():
    cases = json.loads(MANIFEST.read_text())['cases']
    owner = json.loads((SCORED / 'answers.received.json').read_text())['answers']
    wrong = {x['case']['id']: x['prediction'] for x in json.loads((SCORED / 'disagreements.json').read_text())}
    ids = [c['id'] for c in cases]
    app = {i: (wrong[i]['sentiment'] if i in wrong else owner[i]['sentiment']) for i in ids}
    texts = [b.source_text(c) for c in cases]
    result = {'cases': len(ids), 'paid_calls': 0, 'network': False, 'models': {}}
    rows = {i: {'owner': owner[i], 'app': app[i], 'channel': c['channel']} for i, c in zip(ids, cases)}
    answerable = [i for i in ids if owner[i]['relevance'] == 'relevant' and owner[i]['sentiment'] in THREE]
    allowed = [i for i in ids if owner[i]['relevance'] == 'relevant']
    def acc(label_of, subset):
        hit = sum(label_of(i) == owner[i]['sentiment'] for i in subset)
        return {'matches': hit, 'of': len(subset), 'percent': round(100 * hit / len(subset), 1) if subset else None}
    result['app_ai'] = {'all_50': acc(app.get, ids), 'relevant_only': acc(app.get, allowed), 'three_way_answerable': acc(app.get, answerable)}
    for name in MODELS:
        labels = dict(zip(ids, predict(name, texts)))
        for i in ids:
            rows[i][name] = labels[i]
        result['models'][name] = {
            'all_50': acc(labels.get, ids), 'relevant_only': acc(labels.get, allowed),
            'three_way_answerable': acc(labels.get, answerable),
            'confusion_on_answerable': dict(collections.Counter(f"owner {owner[i]['sentiment']} -> model {labels[i]}" for i in answerable)),
            'agrees_with_app_on_answerable': sum(labels[i] == app[i] for i in answerable)}
    result['owner_distribution'] = dict(collections.Counter(owner[i]['sentiment'] for i in ids))
    result['answerable_count'] = len(answerable)
    OUT.mkdir(parents=True)
    (OUT / 'results.json').write_text(json.dumps(result, indent=2))
    (OUT / 'rows.json').write_text(json.dumps(rows, indent=2))
    print(json.dumps(result, indent=2))


main()
