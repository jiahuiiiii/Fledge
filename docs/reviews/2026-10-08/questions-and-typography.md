# Private questions, typography and sentiment positioning — 8 October 2026

## Implemented

A visible **Add question** action sits beside the research-question label. The dialog saves a private question for the selected company and selects it. Added questions and the last selection survive reloads and switching companies. Adding/selecting never runs AI, creates an idea revision or enables a watch. The existing **Investigate this question** action starts an answer only on explicit submission.

Migration 038 stores question bookmarks separately from immutable answer history. Actual app-role tests cover owner isolation, source-role denial, concurrent first additions, one selected question, whitespace/case deduplication and strict API input/session controls. Existing `/questions` routes remain the paid answer/history boundary. Selection writes use the local session owner; client-provided owner fields are rejected. UI callbacks cannot apply a response to another company after navigation.

MiSans Latin replaces the system/Inter stack. Four unmodified official WOFF2 files are local, with the regular face preloaded, fallback fonts and `font-display: swap`. Xiaomi's license and app footer credit are included. Inputs, textareas and custom selects brighten their existing border on focus without an extra ring. Other keyboard controls retain visible focus. The Add question dialog focuses its text field and uses native dialog containment and Escape behavior.

Proposal cards now separate labels, question titles and paragraphs consistently. Before/after columns keep natural content heights and stack on narrow screens. Long source timestamps are rendered as readable UTC dates. Explanatory copy is under **How suggestions work**. Saved proposal content, stale status, source inspection, checkboxes and explicit approval are unchanged.

## Positioning recommendation

Position sentiment as **narrative monitoring for an investment thesis**: help users see what is being discussed, where sources disagree, and what new evidence warrants revisiting a saved question. The promise is a shorter, traceable research loop, rather than an unvalidated return claim.

The [linked Reddit discussion](https://www.reddit.com/r/algotrading/comments/1jvftsj/sentiment_based_trading_strategy_stupid_idea/) raises latency, competition, context, manipulation and retrospective-testing concerns. Its conflicting anecdotes do not establish whether a strategy earns returns. Avoid adopting the arbitrary formulas or confident profitability claims in comments.

Suggested product emphasis:

- Show topics, direct excerpts, attributed source, time window and sample size before an aggregate tone score.
- Separate reported developments from opinions. A selected social sample is not market consensus; absent coverage stays unknown.
- Anchor alerts to genuinely new evidence relevant to saved questions/assumptions. A tone shift supplies context, not a verified event or a return forecast.
- Measure alert relevance, missed important developments, unsupported claims, research effort and usefulness over repeated reviews. These are future validation measures, not current demonstrated outcomes.

No sentiment model, alert threshold or source policy was changed in this phase. Current v16 failures and participant validation remain open.

## Verification and preservation

- 42 focused backend cases: question library, existing revision and proposal behavior. The first run had one incorrect test expectation (unauthenticated status 403 instead of the established 401); corrected final run passes.
- 31 additional existing saved-answer and workspace-reset cases pass. A first invocation used a nonexistent filename and ran no tests; retained separately.
- 27 frontend checks pass; Vite build succeeds.
- A final HTTP check found that the server originally exposed only `/assets`; the initial font preview therefore used a fallback. Added a narrow `/fonts` static route, verified the actual WOFF2 response and license, tested path traversal rejection, and repeated final desktop/mobile visual checks. The final 12-case question/font suite passes, overlapping the earlier 11 question cases; total distinct backend coverage for this phase is 74.
- Browser: add/save/reload, return to a company, custom dropdown selection, native dialog autofocus, source comparison and checkbox selection. 320px and 390px inspections show stacked comparison columns, 15px body text and no horizontal overflow. Desktop visually inspected at the normal 1512px viewport. Temporary size overrides were reset.
- Read-only verification on the owner's actual Broadcom workspace; added test questions and selection mutations stayed in an isolated mocked database. Real stale proposals retain their original content and stale state.
- Source/database backup: `.local/backups/phase78-questions-20261008T011832Z/`. All 91 existing tables matched exactly across migration; no research reset occurred.
- Evidence and screenshots: `.local/live-tests/research-questions-phase78/`.
- No new paid requests. Checkpoint: US$17.140737 confirmed plus US$0.60249 prior maximum holds, US$12.256773 available of the original US$30; 319 calls. Existing user-enabled watches remain untouched.

## Five-perspective review

These are one implementer's review lenses, not independent reviewers.

- Product: reusable questions support the investigation/revisit loop without creating automatic paid work.
- UX: the missing action is now visible; concise comparison labels, spacing and consistent font reduce clutter.
- Engineering: bookmarks have their own schema and preserve answer/revision contracts; selected state is serialized and scope-fenced.
- Evidence: original suggestions are unchanged and source-linked. This UI work adds no sentiment-accuracy evidence.
- Commercial: timely, personally relevant research alerts remain a monetization hypothesis. Generic sentiment scores alone are not a demonstrated moat or validated paid offer.
