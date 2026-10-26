# Local sentiment models vs the owner's labels

26 October 2026. Offline only: no paid AI calls, no network, no database or `.env`. Script: [owner_comparison.py](../../experiments/sentiment_models/owner_comparison.py). Raw output stays private under `.local/live-tests/finbert-owner-comparison-20261026/`. Owner labels and scores are unchanged.

Models are the already-downloaded pinned weights from the earlier local experiment, run on each case's own selected passages: Prosus FinBERT, HKUST FinBERT-tone, Cardiff Twitter-RoBERTa and VADER.

## Tone agreement with the owner (50 cases)

| Labeller | All 50 | Relevant cases (41) | Cases a 3-way model can match (28) |
| --- | --- | --- | --- |
| App's AI (saved) | 29 (58.0%) | 20 (48.8%) | 17 (60.7%) |
| VADER | 15 (30.0%) | 15 (36.6%) | 15 (53.6%) |
| HKUST FinBERT-tone | 13 (26.0%) | 13 (31.7%) | 13 (46.4%) |
| Cardiff social | 11 (22.0%) | 11 (26.8%) | 11 (39.3%) |
| Prosus FinBERT | 10 (20.0%) | 10 (24.4%) | 10 (35.7%) |

The owner's tone labels were 16 positive, 7 negative, 5 neutral, 7 mixed and 15 unclear. The local models only output positive, negative or neutral, so they cannot match the 22 mixed/unclear cases. The right-hand column is the fairer comparison: the 28 relevant cases the owner called positive, negative or neutral.

## What this shows

- Prosus FinBERT matches the owner on 10 of 28 answerable cases, below the app's AI at 17 of 28. It mostly says "neutral" for what the owner read as positive (11) or negative (5).
- None of the local models beats the app's AI, even on the cases they can answer.
- They have no relevance or mixed output, and no context handling (the replies that need the surrounding thread).
- They are not a validation of the app's labels. They disagree with the owner more than the AI does, and agree with the AI on only 7–13 of 28 cases.

## Limits

- One owner's labels on 50 cases; the rubric was still ambiguous in places (see [owner feedback](../reviews/2026-10-18/owner-sentiment-quality.md)). 28 cases is a small base, so differences of a few cases are noise.
- The app's AI numbers come from the saved score, and the owner's exposed labels have since informed rubric 3. This is not unseen validation for either side.
- FinBERT and the other models were trained on financial news or tweets, not on this app's multi-passage cases with context. Prosus FinBERT's licence also limits commercial use; check it before any product use.
- Same-source comparison only. No claim about any provider's hosted scores, which were not accessed.
