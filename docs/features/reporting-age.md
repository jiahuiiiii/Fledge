# Reporting age and expected newer figures

Maximum reporting age and an expected reporting period/date are separate optional choices. Age limits how old a selected period may be; an expectation specifies the period needed after a chosen date. A figure may satisfy the target period yet be too old under the separate age limit. Neither date is inferred from a legal or company filing calendar. [Expected reporting evidence](report-expectations.md) · [Phase57 verification](../reviews/2026-10-03/report-expectations-phase-review.md).

The original age-limit contract follows.

# User-defined reporting age

Implemented locally in phase 5. Each numerical condition can optionally specify a maximum number of days since the reporting period ended. Blank means no age limit; existing saved definitions retain that meaning. This is a user's research criterion, not an expected filing deadline or a recommendation about how recent financial evidence should be.

## Interpretation

An N-day limit includes the entire UTC date N days after the actual reporting period end. It expires at 00:00 UTC on day N+1. Annual and quarterly scopes remain separate. Refetching or restating the same period does not renew its age. A new eligible reporting period supplies its own actual end date; it may already exceed a short chosen limit when published.

Expired compatible evidence makes a condition unknown, retaining its last value, observation identity and source. Missing or conflicting facts keep their separate explanations. The underlying reported fact is not declared false or deleted. Source-check freshness remains a separate dimension: a fresh check can coexist with an expired figure, and an outage can coexist with expiration.

The editor previews the compatible period end, current age and expiry date. Editing or clearing a limit resets approval. Saved definitions, conflicts and historical assessments show the exact saved limit. Expiry-only updates say that reporting figures passed the user's age limit; they do not claim that a new financial figure arrived.

## Clock and recovery

Recorded samples use their recorded scenario date. SEC workspaces use the current UTC clock while the local app runs. Local checks do not fetch filings or call OpenAI. The visible workspace refreshes from the local API while idle and when the window regains focus; new filings still require a manual source refresh.

Each assessment freezes its source cutoff, assessment time, source-check identities, source-check age state, condition definitions and expiry states. Historical views use those saved inputs. The time the worker actually creates the result remains separately recorded; after downtime, the logical expiration time can precede its detection.

A private cursor records both the last shared source snapshot and the time already assessed. Catch-up queues each distinct expiration boundary before the next source snapshot, followed by the latest clock state. A durable queue order keeps several boundaries discovered in the same transaction in sequence. Repeated checks with unchanged meaningful inputs create no new assessment or update. A new revision starts at its approval assessment time; it does not manufacture earlier expiration events. Archived ideas receive no new scheduled work.

Collection, saving and scheduling use the same short lock order so a concurrent source change cannot introduce evidence from after the saved assessment time. HTTP remains outside those locks. Original pending manifests still run with their original no-age-limit contract; migration 006 adds nullable limits without rewriting historical definitions, manifests or results.

## Remaining scope

This is age-based eligibility for the two supported numerical metrics. It does not implement expected reporting dates, future-period targets, catalyst deadlines or inferred event confirmations. Those remain separate work on the implementation tracker. The software checks do not establish investor comprehension or the economic suitability of a particular limit.
