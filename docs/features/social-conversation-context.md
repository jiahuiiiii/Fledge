# Inspect the original conversation — phase 32

Open an original Hacker News source from sentiment, a research answer, history or an alert. **What is this replying to?** shows a saved immediate-parent check, if available. **Load original conversation** explicitly retrieves the original comment and its parent through the same paced HN API. Opening the source only reads saved local data. Neither action calls a model or enables monitoring.

The original comment must still match its saved text and publication time. An edited comment produces a visible source-changed result; its historical text and interpretation remain unchanged. A deleted/dead comment is recorded through the existing withdrawal boundary and its consumed analyses become unavailable. A parent must match the exact API-supplied parent ID, have a compatible date and be a bounded story or comment. Job/recruitment material, missing text and oversized parents are excluded. No linked article, surrounding replies, user profile or further ancestor is retrieved. The parent is a separate message, not necessarily a separate author.

The API has an explicit `parent` field for comments, which can refer to a comment or story. This implementation reuses that relation rather than guessing from search titles. [Official HN API](https://github.com/HackerNews/API#items).

## Meaning and limitations

The extra context is for source inspection. Existing sentiment, private relevance and question-answer models still consume their original bounded comment text; they do **not** use this parent. UI copy states that distinction. A parent headline or another message does not automatically establish the reply's opinion. This phase does not claim improved classifier accuracy, complete thread interpretation or broader investor representation.

Dates distinguish parent publication from current retrieval. This is a check performed now, not proof of what the parent said at the older analysis cutoff; the API does not supply an edit history. A currently changed parent cannot rewrite an old result. Missing and failed checks have explicit outcomes and never appear as a successful empty conversation. Removed parent content is withheld on subsequent reads. Detection is bounded to requested items, not continuous deletion monitoring.

## Persistence and operation

Migration 24 adds immutable shared conversation-result records and a separate current-attempt pointer. The restricted source role writes them; the app reads them. Results are linked to an existing social source and contain no private reasoning. Each check has at most two original-item requests, the existing one-second global source clock, a three-minute claim and a fifteen-minute per-source cooldown. A newer claim fences an older completion. Provider denial stops the check without retry, proxy, alternate host or fallback. Source errors do not consume AI credits.

Reads never dispatch source requests. The source dialog has explicit loading/error/cooldown states, ignores outdated read responses and late completions after closing, and refreshes affected research if removal is detected. The source text is rendered as escaped text. Reopening a stored result uses the same retained record.

## Verification

See the [five-perspective review](../reviews/2026-10-02/conversation-context-phase-review.md) for actual-source inspection, isolated software checks and final installation evidence. This closes one source-review gap in the social sentiment journey. Automatic context-aware interpretation, full discussion retrieval, broader source coverage and participant validation remain incomplete.

## Phase 35 extension

Inspection still changes no saved label and makes no AI call. A new sentiment analysis can now consume eligible recently checked parents, pinning the exact version and displaying separate evidence. The earlier comment-only statements describe phase 32; private relevance, themes and question research still have their own inputs. [Current context-aware sentiment contract](context-aware-sentiment.md).
