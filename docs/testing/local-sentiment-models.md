# Local sentiment models — evaluation, 5 October 2026

**FinBERT now runs locally in an isolated experiment. It is not installed in the app's sentiment or alert pipeline.** The first comparison does not support replacing the current company-aware analysis with a generic three-label classifier. There are useful individual corrections, but losses on company attribution and changing opinions.

## What was actually run

Four classifiers processed **90 retained source cases**: 81 actual-source instances (72 distinct inputs) and 9 explicitly authored controls. Actual material covers Microsoft, NVIDIA, Amazon and Meta, across 48 news, 18 Reddit and 15 Hacker News instances. These are saved excerpts from earlier retrievals, not new scraping or complete articles. Some texts recur across the two historical cohorts; those cohorts are reported separately.

| Local classifier | Intended use and primary reference | Latest actual cases, strict labels | Earlier actual cases, strict labels | Authored controls, strict labels |
| --- | --- | ---: | ---: | ---: |
| Prosus FinBERT | Financial PhraseBank sentiment. [Model card](https://huggingface.co/ProsusAI/finbert) | 5/12 | 9/15 | 6/8 |
| HKUST FinBERT-tone | Financial communication model, fine-tuned on analyst-report sentences. [Model card](https://huggingface.co/yiyanghkust/finbert-tone) | 3/12 | 11/15 | 5/8 |
| CardiffNLP Twitter RoBERTa | English tweet sentiment, integrated in TweetNLP. [Model card](https://huggingface.co/cardiffnlp/twitter-roberta-base-sentiment-latest) | 4/12 | 10/15 | 6/8 |
| VADER | Social-text lexicon and rules. [Official repository](https://github.com/cjhutto/vaderSentiment) | 3/12 | 5/15 | 4/8 |
| Previously saved OpenAI analysis | Current v16 for latest cohort; historical v10 for earlier cases and controls | 11/12 | 14/15 | 6/8 |

These are matches against **pre-existing developer-authored criteria**, not independent accuracy measurements. The current OpenAI method was already developed using these cases and received richer company/source context. This compares direct suitability for our existing task, not general NLP quality. No new OpenAI requests were made.

“Strict labels” means one expected positive, negative or neutral answer. There are 35 such cases across the three cohorts. Another 2 allow multiple three-way labels, 12 include mixed/unclear expectations, and 41 have no frozen tone label. All 90 outputs are retained, but those other groups do not inflate the table's denominator. One older HN item has no eligible child passage and is explicitly excluded; one expected NVIDIA item was already absent from the latest input packet. Neither is scored as a pass. Mixed and unclear are never silently relabelled neutral.

For the latest strict subset, Prosus matched **3/6 news and 2/6 social** expectations; Cardiff matched **3/6 and 1/6**. For the older strict subset, HKUST matched **8/9 news**, while Cardiff matched **5/6 social**. These small, differently composed sets do not establish a reliable news/social routing policy. Confusion matrices and fixed-three-class macro-F1 are retained; absent classes score zero in that F1 definition.

## What the disagreements teach us

- **A useful correction:** the NVIDIA software-launch item has a speculative headline but descriptive source body. Prosus and Cardiff returned neutral, matching the frozen criterion; the current saved analysis returned positive.
- **Wrong company:** a Meta-versus-Microsoft comparison favours Microsoft's adoption and monetization. Both FinBERT variants returned positive for the whole text, while our Meta-specific criterion is negative. A document score cannot decide which company receives the sentiment.
- **Product experience:** positive discussion of Amazon SES being cheap and reliable was neutral under both FinBERT variants. Our source sample includes product experience, not only earnings language.
- **Changed opinion:** an authored example moves from disliking closed drivers to respecting the company. Prosus and HKUST returned neutral; Cardiff returned negative. Earlier negative wording still overwhelms the current view.
- **Mixed views:** a source can like products and dislike support. These classifiers lack mixed/unclear outputs. High softmax scores do not resolve that missing capability.

This does not validate the current OpenAI method: its retained launch error and previously documented attribution, answer and alert limitations remain open. Sentiment alone does not determine whether an event is new, material, true, or relevant to a saved idea.

## Other tools worth considering

| Tool | Potential role in Thesis | Status and limitation |
| --- | --- | --- |
| [FinTwitBERT-sentiment](https://huggingface.co/StephanAkkerman/FinTwitBERT-sentiment) | A next local candidate for informal financial posts, combining finance and social language. | Researched, not run. Uses labelled and synthetic financial tweets; Reddit/HN transfer and company attribution need testing. |
| [NewsSentiment / NewsMTSC](https://github.com/fhamborg/NewsMTSC) | Target-dependent sentiment: separate attitudes towards named entities in one sentence. | Researched, not run. Trained on political news; documentation lists tested Python versions below this app's 3.12. Keep any trial isolated. |
| [FinEntity](https://github.com/yixuantt/FinEntity) | Financial entity-level annotations and modelling approach, relevant to the Meta/Microsoft error. | Researched, not run. A dataset/research implementation with models and training code, not a verified drop-in Thesis service. |

My recommendation is to keep the current source-grounded route while evaluating **company, author and current-time attribution** on a new, independently labelled sample. FinTwitBERT is the next inexpensive local social candidate; FinEntity is the more directly relevant research direction for company attribution. Local classifiers may eventually provide a fast secondary tone signal, but this run does not justify automatic voting, discarding neutral sources, or skipping evidence checks. Neutral wording can still report an important event.

## Reproducibility and isolation

Code: `experiments/sentiment_models/`. Results: `.local/live-tests/local-sentiment-phase76/`, including frozen inputs/protocol, pinned model revisions and weight hashes, all predictions, `comparison.csv`, `summary.json`, dependency lock, verification and initial failure logs. Source passages stay on this Mac. The experiment imports no Thesis modules, opens no database and sends no hosted inference requests.

Labels, source-file hashes and input policy were frozen before inference. Each model reads the source's own selected passages, including the title once except generic HN thread titles; parents are not concatenated into a child's opinion. Whole-text models receive no separate company target. Five inputs exceed the 512-token context: all tokens are processed in disjoint chunks with token-weighted mean probabilities, never silently truncated. This untuned aggregation can dilute contrary clauses; it is not a claim that paragraph scoring is optimal for sentence-trained FinBERT.

On this Mac, each transformer took about 2.5–2.6 seconds for 81 distinct inputs after loading; VADER took about 0.02 seconds. Loading took another 2.1–2.2 seconds per transformer. These are a single local run, not concurrent service benchmarks. Softmax values are uncalibrated; VADER compound is valence, not confidence.

Eight focused code checks pass. All three neural models' chunk adapters produce exactly the same input tensors and logits as ordinary tokenizer inference on a short control; vocabulary sizes match embeddings. Output completeness, score sums, full token coverage and unchanged source hashes pass. An initial Transformers API incompatibility and HKUST's missing legacy tokenizer metadata were corrected before successful inference; failed logs remain. Cardiff reports two unused pooler tensors and no missing classification weights.

Production dependencies, UI, prompts, model profiles, schema, watches and research data are unchanged. The empty Wednesday test workspace is untouched. **Additional OpenAI cost: US$0.** The original US$30 ledger remains the only allowance; historical charge uncertainties are unchanged.
