# Direct OpenAI controls

Current installation contract, checked 8 October 2026: the user increased the entire building-period allowance to **US$30 on 5 October 2026**, recorded by migration 033. Thesis enforces that single cumulative limit, including every earlier call and held maximum. `THESIS_LIVE_TEST_BUDGET_USD=30` must match it. This is not a per-run or per-clone allowance and does not purchase credits. It does not use Fork's keys, ledger or approvals. Dated sections below preserve earlier decisions and price/profile checkpoints; their US$10/US$20 amounts are historical, not the current ceiling.

## Sentiment classification tuning — 9 October 2026

The owner authorized lower reasoning effort and a larger response ceiling after
two eight-source requests exhausted their 9,000-token limits. Production source
classification retains `gpt-5.4-2026-03-05`, now with low effort and exactly 12,000
total output tokens under `openai-gpt-5.4-sentiment-low-12000-20261009`. Standard
rates remain $2.50 input, $0.25 cached input and $15 output per million tokens.
Only the `source_sentiment` format can use this new profile. Briefings, optional
discussion synthesis and private evidence checks retain their existing settings.

Old pricing versions remain unchanged for reservation and settlement. Requests
still reserve their full maximum against the original cumulative US$30 cap and
settle actual usage once. The prompt/cache and batching method versions advance;
existing failed attempts remain immutable, and no automatic retry is introduced.
The exact failed source packet is retained for the explicit changed-settings
trial. See [the actual test and accounting](../reviews/2026-10-09/sentiment-low-reasoning.md).

## Cloning and relocation

[`live_key()`](../../thesis/providers/settings.py) checks the resolved project root against the fixed `APPROVED_ROOT` and the resolved data directory against that root's `.local` directory. This is a path check, not hardware identification. A clone at another location or a separate `THESIS_DATA_DIR` cannot make paid model requests simply by adding an API key or enabling the live-model setting.

The local fictional workflow and offline tests can run in a clone; source collectors have their own configuration and do not depend on the paid-model path guard. Paid features also require the approved provider/model settings, explicit opt-in, the original cumulative ledger and sufficient unreserved budget. An unresolved charge can block new requests even in the approved folder. The UI does not automatically confirm provider charges.

There is no supported self-service rebind or independent per-installation budget flow yet. A deliberate relocation must preserve the original database with all requests, charges, reservations and accounting decisions, then update the approved location through a reviewed code/configuration change. Do not reset the ledger or copy credentials into Git. `.env` and `.local/` are excluded from the repository; cloning or pushing does not transfer either. See [setup and the exact required locations](../../README.md#paid-ai-installation-restriction).

## Implemented boundary

- One PostgreSQL budget row and durable call ledger shared by app and explicit CLI smoke checks. Live use is bound to `/Users/jiahuiwong/Documents/GitHub/Thesis` and that installation's `.local` database. A copied checkout or separate test database cannot start live calls. Relocation must carry the original ledger and deliberately rebind the approved installation; never initialize a fresh allowance.
- Exact requests are fingerprinted and reserved before HTTP. The unique dispatch record prevents reuse of a network attempt. Repeated completed requests reuse the stored response without charge.
- Requests run serially. An interrupted, timed-out or otherwise ambiguous request retains its entire reservation and blocks all new spending until reconciled, except a separately recorded explicit owner decision retaining its full maximum against the cap. There are no automatic paid retries, redirects, tools, hidden conversation context, image/file inputs or streaming.
- Only two bounded text messages and a strict JSON output schema are permitted. Full UTF-8 request bytes plus an 8,192-token framing allowance conservatively bound input; output is capped at 2,000 tokens for original fictional passage selection and 6,000 tokens including reasoning for company briefings/private comparisons. Actual input, cached input and output usage reconcile the reservation in integer nanodollars. A usage/model/tier mismatch blocks further calls.
- Settled charges cannot be changed through the restricted application role. Budget rows and call deletion are also protected. The OS-local database administrator remains a trusted operator, as elsewhere in this prototype.
- The API key stays in `.env`, is never sent to the frontend, and is omitted from source copies, snapshots and output. Only the fixed direct OpenAI endpoint is used. Provider errors are recorded as short codes without response bodies.

Original fictional passage selection uses `gpt-5.4-mini-2026-03-17`, with standard-tier prices checked on 1 October 2026: $0.75 input, $0.075 cached input and $4.50 output per million tokens. No regional endpoint is selected or region independently verified. [Official model and pricing](https://developers.openai.com/api/docs/models/gpt-5.4-mini). Structured Responses use `store: false`; this is a request setting, not a claim of zero provider retention. [Structured output contract](https://developers.openai.com/api/docs/guides/structured-outputs).

## Company briefing and private comparison profile — 2 October 2026

Company news briefings and private saved-idea comparisons use `gpt-5.4-2026-03-05`, medium reasoning, a 6,000-token output ceiling and standard-tier prices of $2.50 input, $0.25 cached input and $15 output per million tokens. Reasoning is included in the returned output-token total, not charged again as a separate subset. This separately configured profile uses the same OpenAI key and the same original cumulative ledger. [Official model/pricing](https://developers.openai.com/api/docs/models/gpt-5.4) · [Reasoning usage and limits](https://developers.openai.com/api/docs/guides/reasoning).

Each reservation stores its model and immutable price version. Dispatch and settlement use that stored profile, so upgrading an analysis model cannot reprice a previous call or create another allowance. Either profile's unresolved request blocks both; an unchanged completed request reuses its original result. A rejected interpretation or incomplete output can still incur a settled charge. No automatic paid retry is permitted.

The stronger private profile was introduced after real-company cases exposed material relevance/stance errors in Mini despite exact citations. Shared briefings also use this profile after the later Mini briefing review found dropped role qualifiers and insufficient attribution/citation for combined claims. See the overnight purpose review for the matched-case outcomes and limitations; changing a model is not by itself evidence of accuracy.

## Evidence and data permissions

The original passage-selection route accepts **authored fictional source passages only**. The separately authorized pitch briefing route accepts bounded Finnhub headlines/snippets plus active code-calculated SEC fundamentals; see [market research](../features/market-research.md). It reuses the Deus evidence-packing boundary, validates company and availability cutoff, excludes superseded source versions, and requests passage IDs rather than invented financial prose. The server renders original paragraphs, preserving negation and qualifications. Unknown/duplicate IDs and incomplete responses are rejected; their returned usage is still counted.

This is AI-assisted source selection, not general fact verification or a balanced research guarantee. Omitted passages are explicitly counted. It does not change monitoring conditions or numerical assessments. The deterministic baseline separately summarizes typed facts and authored claim titles with source links; consensus and causality gaps stay visible.

On 2 October the user explicitly authorized Finnhub free-tier data for this local pitching MVP and removed the earlier compliance prerequisite. The supplied key now enables manual quote/company-news refreshes and optional source-linked OpenAI briefing. This does not reset the paid allowance or authorize public deployment. Model output never changes code-computed financial observations or monitoring definitions.

## Running explicit live checks

Normal `pytest` and browser checks are fully offline. The buttons in the local app and these explicit commands can use the approved live route, after the private settings are enabled:

```sh
.venv/bin/python -m thesis.live_smoke --case baseline
.venv/bin/python -m thesis.live_smoke --case contrary
.venv/bin/python -m thesis.live_smoke --case restatement
```

They save local evidence under `.local/live-tests/`, check required authored sources, and repeat the identical request to verify reuse without a second dispatch. Do not treat these tiny authored cases as extraction accuracy or investment usefulness evidence. If a request becomes unresolved, inspect the recorded call and provider accounting before another attempt. Do not delete the ledger, release an unverified charge, or invent a zero-cost reconciliation.

## Interrupted request and explicit continuation — 2 October 2026

The user reported US$0.87 and 56 requests in the OpenAI dashboard and authorized continued work after the 03:42 SGT Apple briefing timeout. Call `00900866-c649-431d-b8e4-f3b62d211b79` remains unresolved in its original immutable request history. Migration 009 permits an administrator to record that specific authorization separately. Its full US$0.13926 reservation remains deducted from the original US$10 cap. `spent_usd` remains confirmed usage only; `reserved_usd` includes the maximum hold; `accounted_maximum_usd` identifies its authorized portion. No usage, response ID or precise actual cost is invented. Ordinary app/source roles cannot create such decisions. A later verified provider response can settle only its own held amount. Other ambiguous requests still block.

Subsequent direct requests send the existing durable call UUID as `X-Client-Request-Id`, which OpenAI documents as useful for investigating timeouts even without a returned response ID. The strong reasoning profile now has a bounded 180-second read timeout (15-second connection timeout); the legacy route retains 60 seconds. Neither change retries a request or recovers the old response retroactively. [Official request-ID guidance](https://developers.openai.com/api/reference/overview#debugging-requests).

## Budget extension and renewed testing — 3 October 2026

The user explicitly directed further tests, raised the cumulative ceiling to US$20 and reported US$7.53 in the provider dashboard. Migration 027 preserves the original budget row's creation time and all calls, while recording the US$10→US$20 amendment separately. The private `THESIS_LIVE_TEST_BUDGET_USD=20` must match the approved setting; the database remains the spending authority. Application/source roles cannot raise the cap or rewrite the amendment.

The later Amazon timeout `c9576f42-8305-46e8-b540-1d38547c3cab` retains its entire US$0.162305 maximum through a separate operator continuation record. It remains unresolved in the original call history, just like the earlier US$0.13926 hold. Neither amount is released or replaced with inferred usage. Before new tests, confirmed/held/available accounting is US$7.407271 / US$0.301565 / US$12.291164. The reported dashboard total is recorded as owner evidence, not an exact per-request receipt. Future ambiguous calls retain the same stop rule.


## Bounded private answer-evidence profile — 3 October 2026

New broad reasoning checks use the `idea_answer_evidence` format with medium reasoning and exactly 9,000 output tokens, including reasoning, under `openai-gpt-5.4-idea-evidence-9000-20261003`. The standard token prices and GPT-5.4 model are unchanged. Two initial 6,000-token tests returned explicit `max_output_tokens` incompleteness; their actual usage is settled and their rejected outputs are preserved. The larger tests are explicit changed-request evaluations, not automatic retries.

The new format alone can use this allowance. Question-only checks, original private comparisons and briefings retain their previous profiles. Sentiment's existing 9,000-medium profile and the evaluation-only checker's 9,000-high profile also remain unchanged. Full maximum reservation, immutable historical pricing, one cumulative US$20 ledger and ambiguous-charge blocking continue to apply. No key or private setting is changed.

## Apple interruption and reported aggregate usage — 4 October 2026

In response to the question about keeping the interrupted 3 October 23:09 SGT Apple request's maximum reserved and continuing within US$20, the owner reported **US$15.37 spent so far**. The aggregate is evidence of reported provider usage, not a precise receipt for any individual call. An append-only administrative decision retains the entire **US$0.300925** maximum of `252ee3af-01b4-4f0f-a6f6-e575fc768e86`; its original record remains unresolved, with no invented response, usage or charge. The three retained maxima sum to **US$0.60249**. No historical hold or confirmed charge is changed.

At that decision, the ledger has US$15.1381395 confirmed and US$4.2593705 available after all reservations. Explicit remaining company-relevance tests and a separately identified Apple confirmation trial continue under the same US$20 ceiling. There is no automatic retry of the interrupted request; future unknown charges still stop dispatch unless reconciled or separately authorized. See [phase 59 evaluation](../reviews/2026-10-04/source-limits-phase-review.md) for the final test accounting.
