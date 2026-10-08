# Proposal phase review

2 October 2026. Five-perspective self-review by the implementing parent agent; additional independent subagent review remains unavailable at the previously observed agent usage limit. This is neither an independent professional panel nor participant research.

| Perspective | Assessment | Remaining concern |
| --- | --- | --- |
| Product | Converts a research question or saved belief into concrete proposed definitions, and supports accepting, editing or rejecting them. | Real-case suggestions must be judged for relevance, rather than equating schema validity with usefulness. |
| UX | Before/after cards start unselected; users can combine compatible changes, choose missing dates/numbers and edit the complete result. A stale approval preserves unsaved text and explains the conflict. | Choosing a meaningful threshold/horizon is still difficult. The app must not hide that judgement behind a suggested number. The long page needs actual student comprehension testing. |
| Evidence | Original source passage IDs and exact base definitions remain traceable. No model writes observed fundamentals or approves its own proposal. | A correctly quoted rationale can still be misleading. Starting ideas must remain hypotheses; new thresholds/dates must not be presented as facts or investment recommendations. |
| Architecture | One existing revision transaction and original ledger; immutable proposal/decision records; actual restricted roles; source/base staleness; atomic and idempotent approval. | Conditional changes that intentionally exceed the current metric/event vocabulary are rejected. Simultaneous conflicting proposals for the same target cannot be combined. |
| Business | Reduces the blank-editor problem and connects source research to the existing monitoring/revisit workflow. | Neither recurring use nor willingness to pay is established. It does not justify billing or a monetisation claim. |

Technical failures found before installation included a row-lock permission mismatch against append-only grants (fixed with advisory locking) and browser assertions that ran before history navigation completed (fixed by waiting for the selected record). Keep functional tests and actual-case semantic checks separate. Source access changes now also suppress the generation overview and approved-export evidence.


Actual-company review exposed issues beyond valid JSON and exact citations. The first Google adoption criterion incorrectly accepted published pricing as evidence of paying users. The first Apple criterion allowed a named component to establish a broadly described overhaul. A prompt correction distinguishes offers, paid use and recognized revenue and requires partial completion to be explicitly scoped. The Google retest then returned requirements cut off at the field limit; a code guard now withholds unfinished criteria, and the prompt requires concise complete sentences. All attempts are retained. See [the live case record](proposal-real-case-review.md).

The bounded workflow is implemented and exercised; the quality gate remains criterion-by-criterion review, not automatic trust in generated rules. Wider fundamentals/valuation and recurring acquisition/digest remain the next product gaps. Do not invest further in production infrastructure at the expense of those missing user capabilities.
