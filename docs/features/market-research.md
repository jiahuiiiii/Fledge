# Market research for the local pitch

The user authorized Finnhub free-tier quotes/company news and source-linked OpenAI summaries on 2 October 2026. This is a local pitch implementation.

## Data and behaviour

- Supported catalogue: Microsoft, Apple and Alphabet. Microsoft is the demonstrated live company. Adding a workspace alone makes no external call.
- **Refresh market** requests `/quote` and `/company-news` independently. Company news covers the last seven days and stores up to 25 usable articles per check. A persisted two-second request clock and five-minute per-company cooldown bound use. HTTP errors, 403/429, malformed payloads and empty successful feeds remain distinct; no retries or article scraping. API keys use the `X-Finnhub-Token` header and are never shown in the UI.
- Quote validity requires a positive price and provider timestamp. Invalid denominators/ranges stay unknown. A response older than the stored provider quote cannot replace it. The UI shows both quote and retrieval time. No historical chart is fabricated. Quotes cannot alter research monitoring.
- News stores publisher, headline, supplied snippet, original link, publication/first-seen time and immutable versions. Corrections include headline changes. The same URL can belong to two companies. Omitted older articles stay in history; successful empty windows explicitly explain retained stories. Exact copied text is grouped; this is not independent confirmation.
- News and active SEC evidence coexist. SEC calculations remain pinned to the committed filing checkpoint, including a correction returning to earlier values. Company period/sequence is read at commit so simultaneous source refreshes cannot overwrite a newer filing. Interrupted requests mark failed coverage and reject late completion.

## Optional briefing

**Summarise sources** sends at most ten deduplicated news headlines/snippets (bounded input size) plus active code-calculated SEC text to the existing pinned direct OpenAI model. Company name/symbol are explicit. Title mentions rank before snippet mentions, then broader market coverage, newest within each group. This is a transparent relevance heuristic, not a claim-importance or sentiment score. It excludes private saved reasoning. Every generated point cites supplied source IDs and exact quotations. The app labels reported content, AI interpretation and uncertainty. Prompt version 2 keeps points short and leaves numeric SEC figures in the deterministic panel. Quote matching only validates traceability; it does not prove the summary accurately follows its evidence. Original sources remain available.

The paid route shares the original US$10 ledger. Cache identity includes prompt version, model and exact selected context, excluding poll timestamps. Opening the page, market refreshes and repeated unchanged summaries do not initiate fresh model calls. Invalid outputs still retain accounted usage and are not retried automatically. There are no model-written numbers or changes to numerical condition results.

## Verification

139 backend checks and three frontend contract checks passed after this integration; the new browser journey covers source inspection, AI attribution, saved/reloaded reasoning, empty-versus-failed feeds, no page-triggered paid calls, and 320–1440px layouts. The focused corpus checks wrong-company/unsafe/future news, missing quote sentinels, regression to older quotes, SEC/news coexistence and A→B→A, duplicate/unchanged polling, headline corrections, shared article URLs, quote-only non-alerts, partial failures, concurrent filing completion, interrupted requests and invalid model citations accounted exactly once. Mocked injection/denial cases test packet preservation and boundaries, not empirical model resistance. The live Microsoft flow and final browser check passed. Two deliberately revised live market briefings reused their cache on repeat; total original-ledger spending is US$0.01260675, five settled calls, no unresolved charges. See [implementation status](../archive/status/implementation-status.md).

Finnhub contracts: [quote](https://finnhub.io/docs/api/quote), [company news](https://finnhub.io/docs/api/company-news). Source reuse: [Deus adaptation](../../PROVENANCE.md).


## October 2 overnight correction

Current company briefings use the same pinned GPT-5.4 medium-reasoning profile as private comparisons, with the original shared US$10 ledger. The legacy Mini route remains for authored fictional passage selection. Explicit configuration status is separate for these routes; supplying a model key alone does not bypass the original installation/budget gates.

The briefing's current contract conservatively omits ellipsis-bearing source passages from model input and citation eligibility, without changing the stored snippet. Counts and limits are displayed; a packet with no usable news stops before spending. Source status/job qualifiers and citation coverage of every material subclaim are part of the quality check. See [overnight purpose review](../archive/status/overnight-purpose-review.md) for original failures, corrected live outputs, cache checks and actual spending. Older phase paragraphs above retain their historical model and test results.
