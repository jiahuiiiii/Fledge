# Original reply context during watches

In the news/social panel, expand **Original reply context** and enable **Check original reply context during watches** after enabling the company watch. This option defaults off. It follows the existing hourly/four-hour schedule while the local app runs. Stopping the watch pauses it; changing frequency preserves the selected option. Turning the option off stops scheduled parent acquisition, while analyses may still use eligible shared context previously saved with a source.

Before watched sentiment analysis, the app selects its ordinary source sample and considers at most four selected Hacker News replies. Eligible parents already checked within 24 hours are reused. Otherwise, the existing original-conversation collector checks the exact child and one immediate parent. The phase adds at most eight original-item requests per attempt, sharing the existing one-second request clock, source cooldown, size limits, host allowlist and immutable context records. It retrieves no ancestors, linked articles or other replies. No separate model request is added; extra input can affect the cost of the existing metered analysis.

Parents remain separate evidence, never extra posts or sentiment votes. The subsequent analysis prepares its own fresh source snapshot and pins the exact eligible context it actually uses; another concurrent source update can change that sample. A recently failed or running shared lookup is not permission to bypass its cooldown. Any API/transport failure ends further parent requests for that attempt and records partial context coverage. Missing parents do not prevent analysis of otherwise eligible original texts.

A verified edit to a selected child stops this attempt before analysis. The saved version remains historical; a later source refresh must acquire the edited version. Confirmed removals use the existing withdrawal mechanism, and removed children cannot enter the subsequent sample. No older successful parent is substituted after a newer failure. Oversized or ineligible parents remain excluded by the existing model-input bounds.

## Watch lifecycle and history

Migration 026 adds default-false `include_context` to watch settings and immutable attempt headers. Existing watches and past attempts remain opted out; installation enables no watch and rewrites no earlier result. Public context is shared, while settings and attempts retain their owner boundary.

The worker checks its enabled setting, exact claim token and unexpired lease before new source/model stages and between child/parent requests. Turning off or reconfiguring the watch stops subsequent dispatch. An already-dispatched request may finish, but late results cannot publish an automatic company/private alert after the claim expires. Completed research can remain historical. Interrupting a context lookup can leave an unfinished source claim until its existing short lease expires; this is not recorded as a quiet successful check.

**Watch check history → What was checked** shows whether context acquisition was selected, how many replies were considered, source-request attempts, reused parents, partial coverage and how many parents the saved analysis actually consumed. It records attempts even if a later model stage fails. Complete source withdrawal still withholds consumed analysis details. Reading history makes no request.

The existing context-only reanalysis suppression, same-content cache reuse, saved-reasoning revision checks and original cumulative AI ledger remain unchanged. No automatic paid retry, source-provider replacement, external delivery or watch enrollment is introduced.

## Evidence and limits

Software tests cover default-off behavior, persistence, bounds, cache reuse, stale checks, cooldowns, failures, edits, removals, stops, expired claims, history and quiet context-only reanalysis. Optional replay tests use five retained actual Microsoft/NVIDIA child-parent pairs through the actual acquisition/sampling path in a disposable database. Those replays intentionally stop before model dispatch; they prove input handling, not sentiment meaning or alert usefulness. [Phase review](../reviews/2026-10-03/watch-context-phase-review.md).

This closes the need to open every selected reply manually during an opted-in watch. Broader investor-platform coverage, prospective alert performance and actual context-aware model evaluation remain unfinished. Watches remain off in the installed main and QA accounts.
