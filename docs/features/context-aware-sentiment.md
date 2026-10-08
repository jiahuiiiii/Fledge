# Sentiment with saved conversation context

**Phase 43 status (3 October 2026):** A separate evidence checker was evaluated on sixteen bounded requests, with unchanged candidate findings and positive controls. It remains disconnected from app publication: higher effort improved selected-case matching but still missed errors and raised false-rejection concerns. Existing source/answer/alert behavior is unchanged. See [the evaluation and five-perspective review](../reviews/2026-10-03/finding-checker-phase-review.md). This is not a validated fact-checking layer or completion of the implementation plan.


Current method `thesis-source-sentiment-9` supplies explicit platform metadata and selects citations before explanations under a shared finding-grounding instruction. Phase 42 tested three retained actual-company samples plus an authored contrast. Two earlier exact additions disappeared, but unsupported causal wording and target/direction problems remain; this is not a validated accuracy improvement. Older saved classifications and alerts are unchanged. [Results and limits](../reviews/2026-10-03/finding-grounding-phase-review.md).

New Hacker News sentiment analyses can use a recently verified immediate-parent message. Open a comment's source, choose **Load original conversation**, then request a new sentiment analysis. Loading a parent itself makes no model call and never rewrites a saved label. The acquisition check still verifies that the original comment matches its saved text/date before accepting its API-supplied parent.

The classifier receives the commenter and parent separately. Only the selected child is classified and counted; the parent's tone is not the child's opinion and it is not another sentiment vote. The response must cite the child's own body plus exact passages from its own supplied parent. An ambiguous reply can remain unclear. Original excerpts, a separate **Parent context used for this label** disclosure, dates and saved full parent text are available beside a context-aware label. Earlier analyses remain unchanged.

## Selection and dates

`sentiment_context.py` attaches context to the exact selected comment version. At most four parents, 3,000 bytes of eligible passages per parent and 8,000 bytes total are supplied. The latest check must be available, completed by the new analysis cutoff, no more than 24 hours old and not withdrawn. Oversized/fragment-only context is omitted rather than truncated. Failed, changed-comment, future or removed results are not replaced with an older convenient parent. Acquisition remains explicit; ordinary sample reads do not fetch parents.

A saved parent was checked at its recorded time. This does not establish what it said at a previous analysis cutoff: the upstream API has no edit history. A new analysis pins the immutable parent-result identity. A later identical recheck reuses the same classification input and paid response; a changed parent changes the input identity. Existing results are never retroactively assigned new parent text.

## Interpretation, alerts and access

Prompt `thesis-source-sentiment-8` extends the existing Deus-derived classifier through the same OpenAI model, 9,000-token sentiment profile and original budget. News and Reddit inputs/counts retain their existing boundaries. New `context_passages` references are scoped to each child's parent. Structurally valid quotations do not prove a correct interpretation; actual model-quality evaluation remains required.

A parent addition/removal/change on a comment shared between samples suppresses an aggregate reversal for that platform, even if another new comment is present. Otherwise a re-reading could be mistaken for a changed investor opinion. News-reporting alerts and other platforms retain their own rules. History explicitly identifies changed parent context. Saved alerts and review downloads retain their consumed parent evidence and preserve its separate attribution.

If an included parent is subsequently confirmed removed, the whole analysis and dependent history/alerts/themes/exports are withheld through the existing source boundary. Mere retrieval failure does not erase a valid historical reading. Parent withdrawal detection still depends on a bounded explicit source check, not continuous deletion monitoring.

This phase changes the sentiment classifier and its company-level alert path. The thematic reader, private saved-idea relevance model and question-answer model still use their own original comment-only source inputs; do not claim the entire research pipeline is now thread-aware. Full conversations, automatic parent acquisition, Reddit comments, broader investor coverage and participant validation remain incomplete.

## Verification

See [the phase review](../reviews/2026-10-03/context-sentiment-phase-review.md). Offline model responses are mocked; actual retained source records verify input construction and provenance, not new model accuracy. No new paid call is made while the phase-34 Amazon charge remains unresolved.


Phase 36 extends the same pinned context to private saved-idea relevance and its alert/history/download evidence. It never looks up a newer parent for an old sentiment sample. Themes and question research still use their own separate inputs. [Private relevance contract](idea-relevance-alerts.md#saved-conversation-context--phase-36).


Phase 37 also carries the same pinned parents into both discussion-theme stages, with per-claim child/parent evidence and unchanged original-source counts. Old theme readings are preserved. Question research still has separate inputs. [Contract](discussion-themes.md#saved-conversation-context--phase-37).


Phase 38 extends saved-parent inputs to standalone question research. It ranks original source texts independently, then attaches eligible exact-comment parents at the question cutoff; it does not require a sentiment analysis first. Each answer retains its own immutable inputs. [Contract](question-research.md#saved-reply-context--phase-38).


## Source excerpts — phase 47

New readings use `thesis-source-sentiment-10`: an exact selection of original wording replaces the freely generated per-item explanation. An earlier expressed attitude may be shown separately; the main selection may also retain earlier context or an antecedent. Parent context stays distinct and is not another vote. The model still chooses the source category and tone, and can misclassify them. Exact excerpts do not prove those judgments. Historical readings retain their original outputs. See [the implementation, actual-case failures and review](../reviews/2026-10-03/sentiment-extracts-phase-review.md).
