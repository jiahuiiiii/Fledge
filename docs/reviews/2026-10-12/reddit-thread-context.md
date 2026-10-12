# Saved Reddit discussion context

The owner identified that a topic and its replies were being analysed as isolated
texts. The sentiment packet had thread membership, but the model wire omitted it.
Batching could separate related messages. RSS also discarded comments without an
explicit company mention, even when their verified topic concerned the company.
RSS supplies update timestamps and thread membership, but no immediate-parent
IDs; reconstructing a reply tree from feed order would be unsupported.

## Change

`reddit_thread_context.py` pins existing permitted topic/comment passages from
the selected date window and groups thread targets. Explicit message IDs and
anonymous author references preserve boundaries. A known immediate-parent link
is retained; RSS links remain unknown. The quick check and sentiment request
both receive the discussion, with context-only messages distinguished from
labelled targets. Short replies within the same existing collection bound are
retained; replies without their own company mention require the permitted topic
before analysis. Topic membership does not prove a reply's relevance or stance.

Eight target originals and the existing request-size limits remain in force.
Targets and topics stay whole. Available saved siblings are supplied where they
fit; large discussions span requests with the topic repeated and explicit
saved/supplied/omitted counts. Only the original requested messages count toward
the existing sentiment arithmetic. No model summary rewrites source text.
Each result retains the exact discussion supplied to its batch, including when
combined validation runs against all sources. Generic comment headings cannot
serve as the comment's own attitude evidence.

Topic-only dependencies participate in access and withdrawal checks. Discussion
changes affect request identity and suppress false opinion-change alerts. The
current-source view calls these discussion-context changes rather than parent
changes. Evidence displays topics/comments, links, update-date basis, omitted
messages, missing topics and unknown/outside-excerpt parents. Stored readings
remain unchanged and display their earlier method. Exact new requests still
reuse settled calls. The model, low reasoning effort, 12,000 output ceiling,
US$40 ledger, per-request reservation, unknown-charge and retry controls remain.

New identities: `thesis-source-sentiment-24`,
`sentiment-whole-source-batches-6`, `relevance-prefilter-2`, and
`saved-reddit-thread-context-1`. Existing `reddit-comment-rss-updated-1`
timestamp identity and the blocked/disabled Reddit routes remain unchanged.

## Verification

- Full offline `tests` suite: 2,029 passed, 93 optional skips. After the final
  news-only request optimisation and additional topic-window fixture, the
  focused Reddit/context/batching/quick-check/history suite passed 136 tests.
  These totals overlap and must not be added.
- 169 frontend tests, build, scoped formatting, Python compilation and diff
  checks passed. New tests cover whole saved discussions, more than eight
  comments, unknown and known parent links, missing topics, long messages,
  exact source preservation, pre-dispatch oversize failure, context-only access,
  per-batch evidence, reuse, and context-change alerts. Collection integration
  verifies short replies and topic withdrawal/window requirements.
- Read-only planning verified all 13 saved companies. Every eligible source
  remains covered exactly once; full requests stay at most 48,000 bytes and
  quick requests at most 44,000. Model dispatch was explicitly forbidden. The
  saved NVIDIA sample has 689 sources and a final 89-batch plan; it was not run.
- Candidate and installed browsers each passed 22 cases: 13 retained company
  responses; authored discussion evidence at 1440/980/390/320; missing topic,
  omitted comments, known parent, outside-excerpt parent and withheld reading.
  All writes/external requests were blocked. Original links, escaped text,
  scrolling, Escape/focus return, no browser errors and no horizontal overflow
  were checked; desktop/phone screenshots were inspected. Authored labels are
  transport/presentation fixtures, not semantic model evaluations.
- Installed read-only core APIs for all 13 companies match the saved-reading
  presentation from immutable records. Old items were not relabelled or given
  retrospective thread context.

## Installation and retained evidence

The idle app-only restart changed PID 28788 to 2402; the research-loading worker
lock was verified. Initial index `93880163` was followed by a frontend-only
discussion-status wording update without another restart. Final index is
`62c280b63e84153a4ad7d3ebb5357ecacd89ccc3e15aeb96759dbc95686c2985`.
All 48 files in the candidate manifest were verified as served; retained assets
include earlier checked candidate builds and prior installed assets.

All 116 table fingerprints, schema 49, environment and spending ledger remained
exact across installation through final API/browser verification. PostgreSQL
was not restarted. No source refresh, paid model request, watch-setting/private
research action or historical rewrite was initiated. Concurrent source files,
the preceding timestamp/peer/status work and the unmerged onboarding patch were
preserved.

Evidence: `.local/live-tests/reddit-thread-context-20261012/`.
Backup: `.local/backups/reddit-thread-context-20261012/` (source rollback copies,
original indexes and pre-install database dump).

Retain the sandbox test-database/socket diagnostics, an obsolete mocked-render
fixture failure, the nonexistent watch-test filename, authored fixtures that
mistakenly expected no news sources, the initial build path mistake, and the
early missing-manifest installation guard. That guard stopped before mutation;
the completed installer was not rerun. The final wording used a separate atomic
frontend-only installation. Earlier candidates/logs are retained.

This remains a bounded saved sample, not complete Reddit retrieval. RSS reply
parents remain unknown, and ambiguous short replies can remain unclear. Optional
theme/question research retain their own input contracts. No paid evaluation of
semantic accuracy or proof of improved investor comprehension was performed.
