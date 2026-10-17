# Price moves and cited explanations

Prepared17October2026 on `codex/redesign-phase-4`. **Not live; acceptance pending.**
Additive migrations058–060 are covered by the owner's migration approval but
have only run in disposable tests. The live installation remains schema57.
No watch, Telegram preference or saved research is changed by installation.

## Price rules and references

`THESIS_MOVE_ALERTS` defaults off. When enabled, the independent price worker
checks at most every15minutes during the regular New York session and the first
15minutes after its close. Existing fast watches collect company quotes/news;
price detection never waits for social collection or a bulk AI reading.
The same2026–28 calendar as the news lane supplies DST, holidays and early closes.
Unknown years cannot produce live price alerts.

Arithmetic uses Decimal prices and the quote's previous close. Proposed defaults
remain3% in a session, a2-percentage-point gap against QQQ, or5% over two sessions.
The owner must approve these before activation. Configurable values are
`THESIS_MOVE_SESSION_PERCENT`, `THESIS_MOVE_INDEX_GAP_POINTS` and
`THESIS_MOVE_TWO_SESSION_PERCENT`. Quote times must be from a regular session,
not future, at most30minutes old, and within15minutes of their reference quote.
SPY is additional context and never silently replaces missing QQQ. Missing sector
data remains unknown. Two-session arithmetic requires consecutive completed daily
sessions from one saved split-adjustment vintage, with its prior close within
0.5% of the current quote's previous-close basis. Provisional, missing, conflicting
or unsupported history cannot trigger that rule.

QQQ, SPY and SOXX live in `reference_instruments`, **outside** the company/SEC
directory. Their immutable quotes and daily windows share the existing Finnhub
and Yahoo adapters/request clocks. Per-reference leases prevent parallel duplicate
requests; quotes reuse a5-minute check and daily windows an hourly check. Failed
requests preserve the prior snapshot and do not immediately retry. The Yahoo
normalizer accepts ETF explicitly on this path; company history still requires
EQUITY. Real capability probes returned usable quotes for3/3references and a
usable QQQ daily window; these probes made no AI call or account research write.

An explicit semiconductor classification defaults to SOXX. Broad technology and
unknown sectors get none. `company_sector_references` stores private owner edits,
including an explicit choice of none; no preference is backfilled. The preview's
sector control reads settings first and writes only when the person presses Save.
Changing it affects future checks, preserving all saved alert numbers.

Two or more qualifying companies moving in the same direction as the **same**
QQQ snapshot form one market event. Other watched companies moving that way may
appear as **market context only**, retaining `triggered=false`. This grouping
asserts co-movement, not a common cause. A claim per account/company/session/
direction prevents repeated triggers; grouped events count once in the inbox,
while appearing in every member company's filter and badge. The database checks
company/reference membership, and publication rechecks enabled watches, quote
freshness and exact saved numbers.

## Explanations and spending

The explainer is a separate role, disabled unless `THESIS_MOVE_EXPLAINER_MODEL`
is explicitly chosen. Supported proposed models are GPT-5.5 snapshot
`gpt-5.5-2026-04-23` and the existing priced Opus5.5. Bulk/quick models remain
unchanged; a cross-provider explainer uses its own provider key. No environment
model choice has been made for this role.

GPT-5.5's bounded profile uses standard US$5input / US$0.50cached input /
US$30output per million tokens, low effort,2,000output tokens and the existing
64kB request bound. [Official model/pricing reference](https://developers.openai.com/api/docs/models/gpt-5.5).
Other request families cannot use this model/profile. Historical price profiles
and settled ledger records stay unchanged.

One call consumes the exact saved move numbers, up to20company and8World
headlines from the prior24hours, bounded excerpts and explicit coverage limits.
Every proposed causal sentence needs exact quotes from the same supplied source
IDs. Unknown IDs, cross-source/stitched quotes, missing citations, advice and price
predictions reject the whole explanation. The result is one or two sentences,
classified market/sector/company/no clear cause. Co-movement alone is insufficient;
no clear cause uses fixed app wording. These are interpretations of excerpts,
not verified causation or a complete news search.

The ledger records every paid attempt. An immutable per-event attempt is saved
**before** dispatch. Settled invalid answers and unresolved transport failures
never automatically retry. A later process can recover a saved settlement for
free even after the model role is disabled. A missing or uncertain answer keeps
the numeric preview usable and the cause unknown; it does not stop other price
events or bulk watches. Raw responses, usage and unresolved holds remain saved.

## Preview, review and delivery

Every event created by this phase is an immutable **preview** in Updates and the
weekly review. No new event is sent to Telegram. Price previews have their own
review endpoint and owner-scoped records. Viewing, filtering, exporting and
reviewing never fetch sources or call AI. Group members have explicit context
labels, quote/session dates, index gaps, sector context and two-session limits.

Source versions and all consumed headline metadata are pinned. Permission changes
withhold the complete displayed event. World articles are mutable in their source
table, so a captured version hash detects later corrections; earlier snapshots
are not rewritten. Review actions remain retained.

The fourth Telegram kind is prepared with numbers first, every member, explicit
context-only labels, a cautious cause, at most two escaped source links and the
existing3,800UTF-16-unit bound. A preview cannot enter the outbox, even if ordinary
Telegram delivery is already on. A separate `THESIS_MOVE_TELEGRAM_ENABLED` switch
also defaults off; turning it on cannot convert old immutable previews into live
events. Existing uncertain-send protection remains. Live publication/routing and
the proposed five-trading-day shadow period still need the owner's explicit OK.

## Replay and acceptance limits

The frozen13–17October replay contains4trading sessions and3events: a META
relative move on13October, one market event on14October, and one on16October.
The14October group covers NVDA, AMZN and GOOGL plus AVGO/META. Only NVDA, AVGO
and META cross thresholds; AMZN/GOOGL remain explicitly context-only.

The saved15October prices do **not** support a second qualifying event:
NVDA's two-session decline is4.94049%, below5%; AMZN is+0.26763% that session
and GOOGL+0.45449%. No thresholds were lowered or rounded to force acceptance.
The plan's literal14–15October expectation needs reconciliation with these
saved figures. Four-session retrospective arithmetic cannot prove20-minute
delivery, live recall or continuous monitoring. The QQQ daily closes were captured
later; their original quote times remain unknown and are never invented.

Ten authored-output fixtures test validation, including rejected advice, wrong
IDs and invented quotes. Separately, the owner approved a real GPT-5.5 test of
four authored contrasts and six saved-real headline groups. All **10/10** now
pass citation checks. The first run stopped after five paid answers because
the validator rejected two distinct exact quotes from one article. The fix
permits distinct quotes from the same source while rejecting repeated identical
quotes and retaining every exact-source check. All five saved answers passed
free revalidation. A separately approved continuation sent only the five never
attempted cases; no paid answer was resent. The four authored cause checks match
4/4; six real cases have no independent semantic ground truth.

First run: **US$0.036890**. Continuation: **US$0.079345**. Total phase4 paid tests:
**US$0.116235**, zero unresolved holds. Separate selected-model AVGO test:
US$0.5073675. Combined approved tests: US$0.6236025. The live explainer stays off.
The owner-labelled50-source quality set and all live/shadow measurements remain
outstanding.

| Phase4 done-when item | Result | Evidence |
| --- | --- | --- |
| 13–17October replay catches the named sell-off | **Partially verified; wording unresolved** | 3events/4sessions; 14October group includes all3named companies, no separate15October trigger |
| Threshold and grouping unit tests | **Passed** | Full offline2308pass/93optional skips; final affected125pass plus runner101pass, overlapping |
| Explainer citation checks on10authored/real cases | **Passed** | 10/10paid outputs accepted after free saved-answer revalidation; no semantic-accuracy claim |

Frontend202tests/build/scopedformat pass; 8isolated browser groups at1440/390/320
pass with all requests blocked. Screenshots inspected. The preview uses the
existing evidence-card design: one comparison table, explanation with its quotes
and links together, and expandable price/rule/settings details. The user's
`app.css` edits remain byte-for-byte unchanged. Initial full-suite reset/FK
fixture failures and the paid validator stop remain retained as diagnostics.

No phase4 migration, frontend installation, restart or live activation has happened.
The app remains on the owner-started phase1–3 core with new cadence/alerts off.
Phase4 requires058–060, a matching frontend install and owner Terminal restart;
model, thresholds, cadence hours and shadow duration still need live approval.
It is **prepared, not marked done**.

Private evidence: `.local/live-tests/redesign-phase-4-20261017/`.
