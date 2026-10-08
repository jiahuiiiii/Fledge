# Optional local sentiment comparison

Evaluation only. Never import this directory into app generation or alert dispatch.
Read [the findings](../../docs/testing/local-sentiment-models.md) before interpreting scores.

The archived run is `.local/live-tests/local-sentiment-phase76/`. Preparation reads
retained phase47 and phase74 corpora; a checkout without those private local files
cannot recreate that sample. The CSV contains source titles and is not a public dataset.

Use a separate environment (the tested installation is already present):

```sh
.venv/bin/python -m venv .local/sentiment-benchmark-venv
.local/sentiment-benchmark-venv/bin/python -m pip install -r experiments/sentiment_models/requirements.txt
.venv/bin/python -m unittest discover -s experiments/sentiment_models -p 'test_*.py' -v
```

This action sequence was exercised. Completed outputs refuse overwrites; for a
fresh experiment add the same new `--folder` path to every command. `download`
fetches official pinned weights only. `run` is offline. Neither loads `.env`,
contacts OpenAI, or writes to PostgreSQL.

```sh
.venv/bin/python experiments/sentiment_models/benchmark.py prepare
.local/sentiment-benchmark-venv/bin/python experiments/sentiment_models/benchmark.py download
.local/sentiment-benchmark-venv/bin/python experiments/sentiment_models/benchmark.py run --model prosus_finbert
.local/sentiment-benchmark-venv/bin/python experiments/sentiment_models/benchmark.py run --model hkust_finbert
.local/sentiment-benchmark-venv/bin/python experiments/sentiment_models/benchmark.py run --model cardiff_social
.local/sentiment-benchmark-venv/bin/python experiments/sentiment_models/benchmark.py run --model vader
.venv/bin/python experiments/sentiment_models/benchmark.py summarize
```

The original repositories currently supply PyTorch binary weights. Loading uses
restricted `weights_only=True`, offline files and `trust_remote_code=False`.
Class ordering is read and validated from each model's own configuration.
FinBERT-tone needs the authors' explicit BERT classes because its old config lacks
model/tokenizer metadata. No upstream executable repository code is downloaded.

`verify_inference.py` verified the archived default folder against each real
tokenizer's ordinary call; its result is `inference-verification.json`. It refuses
to overwrite that record. Failed logs remain alongside successful runs. Full
transitive versions are in `installed-requirements.txt`.
