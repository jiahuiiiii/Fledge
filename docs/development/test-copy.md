# Running a separate test copy with your own AI key

Added 19 October 2026 at Ten's request, to test with his own OpenAI key without
touching the original installation (Jia Hui's laptop) or its costs. Any priced
provider works the same way.

## What changes
Paid AI used to run only from `/Users/jiahuiwong/Documents/GitHub/Thesis` with
its `.local` database. Any other copy was refused. Now another copy can opt in:

| Rule | Original installation | Test copy |
| --- | --- | --- |
| Where | Original folder and database only | Any folder except the original, with its own database |
| Opt-in | Not needed | `THESIS_TEST_COPY=true` |
| Spending | No cap (owner decision 13 Oct) | Total cap from `THESIS_TEST_COPY_CAP_USD`, above 0 and at most US$20 |
| Cost record | Its own ledger | Its own ledger, in its own database |
| Other checks | Unchanged | Same: live switch, priced models, restart after provider change, key present |

Before each new AI call a test copy adds what it has spent, what is still held,
and the new call's maximum. If that would pass the cap, the call is refused
before anything is sent. Saved answers are still shown.

## Setup (your own OpenAI key, GPT-6 Luna for sentiment)
In the test copy's own `.env`:

```
THESIS_LIVE_MODELS_ENABLED=true
THESIS_MODEL_PROVIDER=openai
OPENAI_API_KEY=<your key>
THESIS_SENTIMENT_MODEL=gpt-6-luna
THESIS_TEST_COPY=true
THESIS_TEST_COPY_CAP_USD=2
```

Restart the app. Sentiment readings use `gpt-6-luna` (Jia Hui's sentiment-only
switch, 18 Oct: 36/50 on the quality set against GPT-5.4's 40/50, at about 4% of
the cost); quick checks stay on GPT-5.4 mini and other main-model features on
GPT-5.4, all on your key and inside your cap. Leave out `THESIS_SENTIMENT_MODEL`
to use GPT-5.4 throughout. For DeepSeek or Claude instead, set
`THESIS_MODEL_PROVIDER` and that provider's key.

## What results mean
A test copy's readings, alerts and costs are its own. They do not count towards
the original installation's observation week or quality gates.
