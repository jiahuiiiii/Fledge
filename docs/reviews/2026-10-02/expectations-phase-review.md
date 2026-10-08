# Performance and expectations — phase 27 review

2 October 2026. Parent-authored review from five perspectives; not an independent consultant panel or participant study.

## Purpose and resulting behavior

The implementation plan distinguishes reported fundamentals from expectations behind an investment story. Previously the app had filing figures, attributed sentiment and question answers, but no dated, structured expectation reading. The new Expectations tab preserves reported management outlook and named analyst/research-firm views separately, with exact attribution, numerical wording, horizon and revision wording. Sources, retained history, a reviewable question draft and a selected-reading download are connected to the existing workflow.

No number or period is fabricated to fill a card. The page states when the snippet lacks an amount or horizon and when original management disclosure has not been checked. It links to reported performance without implying that incomparable periods establish a forecast beat or miss.

## Development evaluation and retained failures

Initial evidence: `.local/live-tests/expectations-20261002T094319Z/`. First correction: `.local/live-tests/expectations-retest-20261002T094929Z/`. Final evaluation: `.local/live-tests/expectations-retest-20261002T095152Z/`.

Five initial requests exposed a concrete attribution failure: Apple product hopes in journalist narration became management outlook, while a Morgan Stanley estimate revision without a new numerical value was omitted. Meta business exploration and an auditor pact were also over-included as outlook. The next prompt explicitly required attributed expectations and retained named research-firm revisions even when values were absent.

The first corrected Apple result handled those cases, but the Meta result returned a source-prefixed passage ID that was not supplied. Validation rejected the entire result. The final request schema enumerates supplied source and local passage IDs, while server validation still checks same-source membership and exact text. The original failed response and charge remain recorded; no result was silently repaired or automatically retried. A known source ID in gap prose is rendered as its exact source title, with the raw response preserved.

| Final packet | Selected expectation checked | Result |
| --- | --- | --- |
| Actual Microsoft snippets | Reported spending outlook retains approximately stated amount and calendar 2026; analyst price-target numbers do not become company guidance | Selected checks pass; potential margin impact remains qualitative |
| Actual Apple snippets | Morgan Stanley's revision is an analyst view; missing amount/period stays unknown; journalist hopes are excluded; no invented Woodring affiliation | Selected checks pass |
| Actual Meta snippets | Zuckerberg's Muse ambition remains an expectation, with no inferred period; business exploration and audit pact are excluded | Selected checks pass |
| Actual Amazon snippets | Synopsys outlook is not Amazon guidance, and generic deal commentary is not management outlook | No qualifying expectation in this selected packet |
| Six authored contrasts | Reaffirmed fiscal range and exclusion, calendar analyst forecast, withdrawal without replacement, and exclusions for counterparty guidance, journalist hopes and a pact | All six selected criteria pass |

The five final packets match **17/17 selected criteria**, with **29 exact quotation associations** checked against their supplied texts. Twelve requests cover initial calls and corrective retests. This is a small development set with founder-authored expectations; quotation fidelity does not prove interpretation, original-company accuracy, whole-feed recall or investment usefulness. No authored packet is promoted into product research.

## Verification and cost

- 559 integrated backend checks pass with both retained public SEC corpora. The initial full run exposed a disposable-fixture cleanup omission after the new foreign key was added; both cleanup fixtures now include the new table.
- 65 final focused checks pass after request/display/history refinements; two of those tests were added after the integrated run. Ten frontend checks/build and three browser journeys pass. The final expectations browser was rerun after the history refinement.
- The initial phone overflow was fixed; original logs remain retained. Browser tests make no paid calls and use disposable authored data.
- Phase cost is **US$0.390555**. Cumulative confirmed spend is **US$5.461716**, plus the unchanged original **US$0.13926 maximum hold**, leaving **US$4.399024** under the original ceiling. There are 163 calls and no new operationally unresolved charge. The original interrupted call's actual charge remains unsettled.

## Five perspectives

| Perspective | Finding | Remaining requirement |
| --- | --- | --- |
| Product | Adds a concrete way to inspect the expectation behind a story and turn it into a research question | Original-company guidance and forecast-versus-actual comparisons remain partial rather than silently inferred |
| UX | Attribution, period and missing information sit beside the source; performance, social opinions and assumptions stay separate | No participant has yet demonstrated that these distinctions are understood |
| Engineering | Shared immutable readings reuse current sources, ledger and permissions; cached readings preserve original dates | Bounded lexical selection can omit relevant reporting; generated statements remain subject to semantic error |
| Research | Actual cases exposed both attribution mistakes and unsupported citation formatting before installation | Same-case retests are not held-out accuracy evidence; fuller primary sources and independent labels remain needed |
| Business | Uses current suppliers and keys; this phase adds no subscription or source cost | Small development costs do not establish cost per active customer, retention or willingness to pay |

This is progress toward the reconciled plan, not full-plan completion. Original guidance collection, broader social coverage, normalized financial trends/valuation extensions, participant benefit and commercial validation remain open. Hosting, billing and external messaging remain outside the local pitch scope.

## Installed verification

Backup: `.local/backups/phase27-expectations-20261002T103522Z/`. The additive migration preserved every preexisting database row and private configuration value. Four reviewed actual-company packets were made available from settled cached responses, with no new dispatch or charge: Microsoft has three findings, Apple two, Meta one and Amazon an explicit empty reading with gaps. Authored contrasts and rejected earlier outputs remain evaluation evidence only.

Installed request hashes match the evaluated inputs, repeat extraction reuses the same record, source-linked downloads are inert, and main-account versions/watch settings/publications remain unchanged. Watches remain off. The installed Microsoft view displays the original amount and calendar-year wording; its source dialog matches the retained provider snippet. The final verification file records source hashes, current schema 19, unchanged private state and the reconciled original budget.
