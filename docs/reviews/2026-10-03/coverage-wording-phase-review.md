# Source-specific news comparisons — phase 54

3 October 2026. New news comparisons now use a code-written description of the model's selected relationship beside each report's own exact excerpts. They no longer publish the model's free-text comparison explanation. This prevents the observed Amazon explanation from attributing a counterparty and location to both reports when only one supplied those details. It does not prove the underlying repeat/additional-detail/contradiction decision is correct.

## Implemented behavior

`coverage-source-pair-1` labels a comparison as an AI interpretation and invites the reader to compare the two original excerpts. Actor names, amounts, dates, locations and event status appear only in their source-specific quotations. The existing source links, repeat guards, counts, seen keys and private/publication boundaries remain in place. No new service or model stage was added.

The raw provider explanation remains in its original metered response for audit and compatibility. The existing output schema still requests that field; new rendered results discard it. This preserves the exact model request/cache identity and avoids a paid reanalysis just to change presentation. The rendering/summary policy advances from `sentiment-coverage-5` to `sentiment-coverage-6`; classifier v10, medium reasoning and the finite 9,000-token allowance stay unchanged. Candidate v12, the generic checker and high-reasoning evaluation stay uninstalled/unwired.

Old saved analyses and alert payloads retain their original text. When their comparison lacks the new policy marker, the workspace, alert view and weekly export identify it as an earlier AI-written summary and ask the reader to check what each report supports. The stored history is not rewritten. Current access checks still apply to both compared reports, including comparison-only sources.

A rendering-policy change creates a distinct saved-analysis identity while retaining the same model-call key. The old and new analyses can therefore share one settled response. Policy changes cannot themselves claim a sentiment reversal. Watches remain opt-in, and installation enables none.

## Verification against the failure

The seven comparisons saved during phase53 were replayed through the new pure rendering boundary, including the Amazon counterparty/location overstatement. Every relationship, repeat guard, review note, source identity, quotation, coverage group and seen key remains exact. All 24 comparison-quotation associations retain their original scope. Free prose is replaced by the appropriate code-written relationship description. This is a saved-response replay with no new acquisition or AI request; it is not fresh model-quality validation.

Tests deliberately return invented company/location/amount prose for each relationship and verify that it cannot enter new app results. Historical-result and alert/export tests preserve the original wording, identify its older format, verify the two original sources and prove that changing rendering policy does not add a model charge.

Final checks: **984 backend tests** with all six retained corpora; **52 overlapping focused cases**; fourteen frontend checks and the production build; sentiment and reporting-update browser journeys at 320/390/1440px. The first checks exposed two errors in the new test fixture (a ledger column name and an earlier report not yet seen); both were corrected, and the complete suite rerun. Initial failures are retained. Browser provider calls are mocked. The expanded comparison was visually inspected at phone width.

The existing Amazon sample was appended as `60d398aa-8f8d-4bd7-ad5f-48c08ffb34ea` using its exact cached v10 response and original source cutoff `2026-10-03T05:46:10.614202+00:00`. Its ten items and two comparisons are visible in the installed app. Every prior protected row remains exact. This makes the source-specific comparison visible without refreshing data, making a paid request, editing saved reasoning, enabling a watch or publishing an alert. It must not be described as a new live market reading. A separate GET-only browser check of the installed app passed at 390/1440px, including original-source inspection; no writes or external requests occurred. The phone comparison was visually inspected.

## Preservation and evidence

Schema remains 29. A pre-install source/database backup, frozen file list, protected-row fingerprints, replay report, initial/final test logs, screenshots and final app verification are retained in `.local/live-tests/coverage-wording-20261003T115852Z/`. The pre-install backup is `.local/backups/phase54-coverage-wording-20261003T120316Z/`. `install.json` and `final-verification.json` record the installation and final checks. Protected research/private/watch rows remain exact, with only the explicitly recorded shared Amazon analysis appended. Source and weekly schedules stay off.

This phase adds **US$0**. The cumulative US$20 ledger remains **US$14.0244295 confirmed plus US$0.301565 historical maximum accounting**, leaving **US$5.6740055**, 278 calls and no new unresolved charge. Earlier ambiguous charges are still unknown and their maxima remain accounted.

## Five-perspective review

These are five perspectives applied by one coding agent, not independent professional consultants or user research.

| Perspective | Judgment and consequence |
| --- | --- |
| Product | The comparison now tells the user what kind of change to inspect and shows each report's evidence. It removes an observed unsupported sentence while retaining the alert/review workflow. |
| Research quality | Code controls descriptive wording; the model still judges whether reports are related and which excerpts matter. Exact quotations and this replay do not establish general grouping accuracy or recall. |
| UX | The existing compact disclosure, original-source actions and phone layout are preserved. Historical free prose is identifiable, and the new wording does not bury the paired excerpts under another paragraph. |
| Architecture | A rendering-policy version preserves immutable history and reuses settled responses. No migration, new provider, pipeline stage or repeated paid request is needed. |
| Business | A concrete reliability improvement costs no additional model credits. This does not establish customer retention, willingness to pay or production economics. |

The overall goal remains incomplete. Selected sentiment errors and standalone-answer quality remain open; this phase does not silently promote a failed classifier candidate. Next work should address another substantive alert-plan gap—event occurrence dates versus report-publication dates—while retaining the established source/approval boundaries. Broader financial/valuation and participant evidence also remain open.
