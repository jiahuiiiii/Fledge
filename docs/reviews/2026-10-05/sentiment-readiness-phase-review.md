# Sentiment, alerts and target-chart review — phase 74

The user asked us to research and improve the main sentiment/alert features, investigate additional social platforms, add an analyst-target graph and fix the removal notice. The active research workspace must remain empty for Wednesday. No new provider account or watch enrollment is introduced.

## Delivered behaviour

See [implementation and source research](../../testing/sentiment-alert-readiness.md). Method `thesis-source-sentiment-16`, development policy `source-development-2`, count/alert policy `sentiment-coverage-8`, and coverage explanation policy `coverage-source-pair-2` add independent source-event evidence and stated impact to the existing single classification request. No extra paid runtime stage or model change is added. Positive/negative opinion remains sentiment; only supported specific developments can create reporting updates. Full original passages, provenance, per-platform separation, source withholding, quiet baselines and immutable history are preserved.

A cited change must contain event evidence absent from its linked earlier report. Equal cited wording cannot create a new-detail update. Genuine numeric/status changes and changed headlines remain eligible when supported by the selected source evidence. Semantic paraphrase matching remains fallible. The previous generic finding checker is still not used for publication.

The valuation panel now plots the target range and the retrieved quote, displays low/mean/median/high and computes each potential return from the same quote. Missing/invalid quote and target states are handled explicitly. This is not a future price path or a recommended entry price. The notice uses a two-column layout with an accessible icon-only revert/dismiss group at the far right. Actual rendered tests verify it, not just source markup.

## Verification and retained failures

Final broad offline suite: **1,124 passed, 29 skipped** with the retained real SEC corpus enabled. The skipped tests require other opt-in saved corpora. Four additional retained-response replay tests pass separately. Frontend: **25 tests and production build pass**. Browser checks cover the target range/quote arithmetic and icon positions at 320, 390, 1440 and 1920 pixels; the sentiment journey covers source inspection, watch controls, two grouped alerts, review state, reload and desktop/phone layouts. Browser data is wholly authored and isolated.

Earlier broad runs exposed outdated mock event fields after label mutation and an unused-schema size overhead. Both were corrected; no runtime validation was relaxed. The first attempt to combine valuation and older sentiment fixtures correctly rejected the older filing; sentiment browser checks then ran in their own separate database. The first candidate request exceeded the unchanged 64,000-byte ceiling before reservation/dispatch. Its artifact is retained; no charge or unresolved request resulted. Production fitting remains bounded and omits whole sources rather than shortening their evidence.

Eight paid development calls cost **US$0.8554325** in total. Three initial candidate calls exposed the distinction between negative overall tone and a neutral stated event. They were not installed. The final method was evaluated on the original actual-source samples and authored positive/negative controls. This is developer-labelled retrospective evaluation, not independent ground truth.

| Final-method check | Result | Important boundary |
| --- | --- | --- |
| Actual sources classified | 40 items across NVDA, AMZN, META | One NVDA Reddit item and one comparison report omitted to stay inside the existing bound; original selected text is complete. |
| Specific-event eligibility | 30/30 selected criteria across actual and initial authored cases | Includes concrete reports, rumours, opinions, hypotheticals, questions and teasers. |
| Adverse-event eligibility | 31/32 frozen criteria | The cancelled-acquisition-talks control had no stated harm. The model returned no stated impact; the predeclared adverse expectation remains a recorded mismatch, not relabelled as a pass. |
| Supplemental explicit-harm controls | 4/4 event and 4/4 adverse decisions | Two explicit stated-harm patterns and two no-harm/opinion patterns, all wholly authored; unchanged prompt, separate packet, not a replacement for the failed criterion. |
| Selected original tone retention | 15/16 | NVDA's descriptive launch still receives positive framing instead of the frozen neutral expectation. |
| Selected company relevance retention | 28/29 | A hardware/workflow requirement is incorrectly excluded under the developer criterion. One previously scored social source is omitted, not counted as correct. |
| Same-input alert replay | Quiet in all four main final packets | No claim about prospective feed-wide missed alerts or delivery latency. |

The four main final packets contain 145 validated selected quotation associations, including reporting and coverage evidence. Exact quotations do not establish correct interpretation. General sentiment accuracy is **not** demonstrated to improve, and the all-criteria semantic gate did **not** pass. The installation decision is narrower: the event-alert boundary and unchanged-evidence checks prevent the reproduced teaser/mixed-article false alerts while explicit adverse controls and correction replays still deliver. Keep these limitations visible for the owner's test; do not describe the feature as optimal or fully validated.

Standalone answer antecedent/citation-coverage failures from phase 69 remain outside this change and are not claimed fixed. Sparse social coverage, one-author samples, source failures and prototype polling latency also remain real limitations.

## Five perspectives

One agent applied these five lenses; this was not independent consultant review.

- Product: clearer reasons for an alert and a quiet result help the owner evaluate the main loop. Market-wide sentiment and predictive value are not established.
- UX: source-event details sit behind disclosure; chart arithmetic is readable; icon controls remain keyboard-labelled. Browser evidence verifies full-width alignment and narrow layouts.
- Data: platform access was checked rather than inferred from old libraries. HN is integrated; Mastodon is feasible but uneven; Bluesky denied the actual search; X/YouTube/Stocktwits require separate access decisions.
- Engineering: reuse existing ledger, source contracts, grouping and watches. No migration, new runtime dependency, automatic retry or rewritten historical result. Model limits remain unchanged.
- Evaluation: retain every initial failure, frozen-label mismatch, omitted source and regression. The narrower event-alert improvement is distinct from general tone/relevance quality.

## Evidence and accounting

Final frozen requests, calls, scores and report: `.local/live-tests/sentiment-readiness-20261005-phase74-event-impact/`. Supplemental unchanged-method controls: `.local/live-tests/sentiment-readiness-20261005-phase74-explicit-controls/`. Initial candidates and pre-dispatch rejection: sibling phase74, phase74-fit and phase74-compact directories. Do not remove or overwrite them.

Cumulative accounting after this work: **US$16.793227 confirmed + US$0.60249 retained historical maxima**, leaving **US$12.604283 of US$30**, 314 total calls and zero new blocking unresolved charges. Historical maxima remain held; earlier ambiguous charges are not silently resolved. No new product research or alerts were published into the owner's empty database.

## Installed state

Installed on 5 October. Backup: `.local/backups/phase74-readiness-20261005T031421Z/` (source and database). The app at port 8841 was restarted and its actual served bundle verified in Chrome. All research tables remain empty after restart; fixture bootstrap remains off. All provider accounting is identical before and after installation. The owner needs only to refresh an old browser tab to load the new UI.
