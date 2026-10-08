# Saved-reasoning alerts — phase 12

**UI follow-up (8 October 2026):** The sentiment panel shows **Watch settings** and **Check against my idea** only while **Watch news + social changes** is enabled, as requested by the owner. Hiding these controls does not clear saved preferences, suppress history, submit a manual check or change the backend manual-check contract.

The product now asks a narrower question: does this new report or discussion bear on the exact investment reasoning the user saved? Company sentiment remains separate. A favourable headline can challenge a cost assumption; an adverse story can be irrelevant to a particular idea.

## User journey

1. Save a draft question or investment reasoning. A question-only draft is sufficient for question-focused checks; broad reasoning checks require saved reasoning.
2. Analyse the company's selected news/social sample. Choose **Connections to my reasoning** or **Answers to my saved question** under **Check focus**, then **Check this sample against my idea** for an explicit private comparison.
3. Inspect potential supports/challenges, risks to investigate or evidence toward an open question in **Updates**, with the saved words, original source quotation and the model's explanation together. Context, unclear and unrelated findings stay in **History** without creating an alert.
4. Mark an alert reviewed or unresolved; inspect the current idea before changing it. A check never edits reasoning or approves conditions. Export preserves the checked revision and review state.
5. Optionally enable a local watch and select **Changes linked to my saved reasoning** or **Answers to my saved question**. The current sample becomes a quiet baseline. Later runs check only unseen selected content. Turning the watch off stops new delivery. Editing reasoning establishes a new baseline at the next run.

Watches default off. They run only while this local application is running, at the visible selected interval. Private matching adds a metered model request when new eligible content exists, using the original shared budget. No automatic paid retry, external notification or email is added.

## Evidence and privacy contract

- Migration 013 is the schema authority. Private checks, publications and acknowledgements are immutable and protected by forced owner policies. The shared sentiment result does not contain private reasoning.
- The check pins the exact reasoning revision and shared sample cutoff. Current selection `private-original-sample-1` considers all usable original items in that sample independently of company-sentiment relevance labels, deduplicates exact content and alternates news/social up to 16 items. A Hacker News comment needs body evidence; its generic title is insufficient. This is not an exhaustive search. Earlier saved checks retain their company-relevance filter and display that limitation.
- Current broad-check prompt `thesis-watch-relevance-9` does not receive sentiment labels or aggregate counts. The model selects source passage and saved-sentence IDs; code renders original quotations and verifies all selected sources occur exactly once. Exact quotation does not prove the interpretation is correct.
- Supports/challenges require a specific saved sentence. Social arguments remain attributed opinions. Forecasts, future departures, product launches and permission to seek damages must not become completed results, paying-customer adoption or damages awarded.
- Cached identical checks make no new paid request. Quiet checks still save their result. Automatic checks mark examined content as seen, including context-only material, to avoid repeated analysis.
- Late results after an edit, archive, newer analysis, source withdrawal or disabled/reconfigured watch remain historical and do not create current alerts. Original results remain inspectable under the source access boundary.
- Source withdrawal withholds affected derived interpretation and excerpts, including in exports. Review acknowledgement is append-only. Returning to an earlier source body does not manufacture a new alert.
- Company watch mode retains generic source/sentiment alerts. Saved-reasoning mode suppresses that duplicate stream for the same watch. Unread company counts include both alert types and clear after review.

## Verification and limits

Automated tests use mocked models and disposable databases. They exercise complete sample coverage, exact revision/quotes, owner separation, cache, quiet results, duplicate inputs, malformed output, watch opt-in, stale results, withdrawal, exports and unread counts. The browser journey covers scope selection, old revisions, source reading, downloads, review, archive and 320/390/1440-pixel layouts. Actual-source model tests and their retained failures belong in the phase review.

This is a bounded relevance workflow for the local pitch. It does not establish alert precision/recall, prospective detection time, market consensus, user usefulness or willingness to pay. Coverage currently includes selected Finnhub news, accessible Reddit feeds and Hacker News comments; denied feeds stay visibly unavailable. Broader social platforms, reliable unattended operation and customer validation remain outstanding.

## Research questions and a stated position

A request such as “I need customer evidence before deciding” does not assert optimism or pessimism. Prompt v4 uses **Risk to investigate** for a specific threat relevant to that research outcome without claiming the user's reasoning is contradicted. Supports/challenges require a position the user actually states. Risks require an exact related saved sentence and remain attributed interpretations. Generic bad news, lack of requested proof and agreement with caution are insufficient. The live Google demo exposed this distinction; its original v3 result is retained and marked unresolved rather than rewritten.


## Evidence toward an open question — phase 17

A concrete reported answer to an explicit question can now produce a separate **Evidence toward your question** update (`answers`). It can point to the exact saved question field or a question/request within the saved reasoning. A future availability date can answer when availability is planned; it does not establish completed availability or sales. A partial answer must say what remains unknown. It never changes the idea, conditions or research outcome automatically.

Supports/challenges still require an asserted belief, and specific threats still use Risk to investigate. Background topic overlap, a source omitting requested evidence, a launch presented as proof of paid adoption, or an unsupported social opinion stays quiet. An attributed social report may answer a question but remains a report from that post, not independently verified evidence. These are model instructions and developer test criteria, not a guarantee of semantic correctness.

The model selects exactly one supplied saved segment for an answer: `question_segment_id` or `reasoning_segment_id`, with the other null. Code validates membership and renders original characters; unsupported, missing, dual or foreign anchors are rejected. Question IDs are derived deterministically from the exact immutable saved question. New requests use prompt v6 and a new request identity; old saved results retain their original prompt/output and remain readable without a call. No database migration is needed.

Answers share the existing grouped publication, baseline/content deduplication, revision checks, owner/source permissions, review actions, history, weekly review and downloads. A watch does not reprocess its already-seen baseline just because the prompt changed. Manual checks can inspect the selected existing sample; the category does not imply that the underlying news just happened. Semantic paraphrase deduplication remains incomplete. Saved reasoning is still required to enable an idea-related watch; the question alone is not a second watch system.

### Phase 23 source selection correction

Retain distinct unseen reports within a semantic-repeat group when preparing a private check. A newer teaser can omit information in the earlier complete snippet; treating their shared story key as identical source content loses evidence. Previously seen keys still suppress repeated watch delivery. Within one new request, deduplicate exact full-content identities only, retaining the existing sixteen-source limit, alternating channels and one publication per check. Actual NVIDIA buyback testing exposed this failure; the catalogue phase review retains the initial output and corrective retest. Historical results and prompt identities remain unchanged.


## Saved conversation context — phase 36

The private check now consumes the exact HN parent already pinned in its selected sentiment analysis. It does not fetch a parent or attach today's context to an older sample. An analysis with no parent stays comment-only even if the user later inspects the conversation. The parent selection and byte limits are inherited from [context-aware sentiment](context-aware-sentiment.md).

The parent is nested context, not a new source connection or independent confirmation. Prompt v7 requires the child's own body evidence and one or two exact passages from its own parent. The connection must concern what the child actually argues or expresses; a parent-only fact or opinion cannot be attributed to the commenter. Ambiguity can stay context/unclear. Code validates references and quotation boundaries, not the truth of the interpretation.

**Inspect the source evidence** includes **Parent context used for this connection**, with separate quotations, publication/check times and the original parent link. Saved history, the individual download and periodic research review preserve that context. Earlier checks retain their original output and display an earlier-method notice. A later parent edit/check does not change a saved connection.

The existing automatic seen-content policy still keys the original source text: acquiring a parent or reanalysing the same comments does not itself create a fresh private call or alert. An explicit manual check can examine the selected saved sample. Withdrawal of any consumed source or parent withholds the entire affected check and export; withdrawal during a request prevents current publication. Owner isolation, exact saved revision, no automatic paid retry and default-off watches remain unchanged. No migration is needed.

[Phase review](../reviews/2026-10-03/private-context-phase-review.md) distinguishes mocked software verification and retained actual-source input checks from model interpretation quality. The new private prompt has not been dispatched to OpenAI while the previous Amazon charge is unresolved.


## Independent private source selection — phase 45

General company relevance and relevance to a particular saved question are different judgments. The private stage now considers usable original sources even when the shared sentiment stage labels them unrelated or unclear. It retains the shared analysis's exact source versions and saved parents; it does not add a new source service or refresh anything. Original sentence/ellipsis limits still apply. News and Reddit can have meaningful title-only evidence; the generic Hacker News title cannot substitute for a comment body.

Selection policy has its own request identity. Opening an old check does not rerun it or change its result. An explicit new manual check can use the wider selection, with the existing metered model profile. The UI, individual download and periodic review state whether a check used the old company-relevance filter or the new original-source selection, along with source counts. Historical counts keep their original meanings.

Quiet watch baselines and previously seen exact texts remain unchanged. Changing policy, adding parent context or reclassifying the same sample cannot itself produce a fresh private alert. Prior validated coverage links can still suppress already-seen repeat reporting; this is not independence from every shared model decision. A genuinely new source can be checked regardless of its company-relevance label. The same revision, owner, access, lease, grouped publication and no-automatic-paid-retry boundaries apply.

The source sample is still selected upstream, capped and dependent on accessible feeds. Wider private eligibility does not establish better overall recall or precision. [The phase review](../reviews/2026-10-03/private-selection-phase-review.md) records a recovered actual-source question connection, a no-evidence control and the limits of those authored cases.


## Explicit check purpose — phase 46

The broader reasoning mode remains the default and uses unchanged method v7. The optional **Answers to my saved question** mode uses `thesis-question-watch-2`: only answers to the exact question can alert; related background, ambiguity and unrelated texts remain quiet. It does not infer an investment position, and a question-only saved draft is sufficient. The reasoning text stays in the immutable record but is not sent in the question-focused request.

The request schema restricts each item's source and parent citations. Code also rejects directional labels and reasoning anchors in question mode, validates the exact question segment and checks every selected item. These boundaries prevent category/reference errors, not all false answers or unsupported prose. Historical broad checks keep their original output/cache identities; current and saved focus is visible in the UI and exports.

Watch focus persists separately from manual focus. Switching focus starts a quiet baseline and invalidates in-flight delivery; changing frequency preserves purpose. A manual check with a different focus cannot consume an active watch's unseen sources. Migration 028 defaults existing settings and attempts to broad reasoning. All existing watch opt-in, revision, access and budget safeguards apply.

[The phase review](../reviews/2026-10-03/private-purpose-phase-review.md) records four initial tests, a rejected invented-parent response, and four source-bound retests. Final answer/quiet decisions matched the selected criteria; broad-mode risk noise and general semantic accuracy remain unresolved.


## Possible connections without alerts — phase 48

New broad reasoning checks show whether a source directly addresses the saved idea, makes its own argument, or needs another evidential step. An inferred connection appears in History as **Possible connection · not an alert**, with **What would establish the link**. It contributes no alert count and a possible-only check stays out of Updates. A mixed check may show the lead beside an actual alert, explicitly distinguished. Private and periodic downloads retain the same distinction.

For example, an executive departure alone does not establish customer losses. A source that actually reports a retention change, or explicitly argues that renewal prices threaten retention, can still warrant review. The classification is AI interpretation, not verified causation or a trade recommendation. Tests found remaining cases that incorrectly treat questions or missing data as answers; this change does not resolve all alert noise.

The explicit question-only route remains unchanged. Existing history keeps its original classifications, and installing the method does not cause seen text to alert again. No new source/model stage or database migration is needed. [Evaluation, failures and five-perspective review](../reviews/2026-10-03/connection-basis-phase-review.md).


## Substantive answers and original wording — phase 49

New broad reasoning checks pair the exact question fragment with an exact excerpt from the selected original source. **Question addressed** and **Answer evidence · original wording** appear together in history, alert details and private/periodic downloads. These are AI-selected source matches, not independent verification; the full selected passages remain inspectable.

The response distinguishes a direct answer, partial answer or explicit negative answer from a source question, absent information or background. Only the first three may create an answer alert. Code requires the target to occur in the selected saved segment and the answer excerpt to occur in one of that item's selected original passages. A separate parent alone cannot supply the child's answer. Whitespace normalization retains the original source characters. Non-answer items cannot carry an answer pair. Existing inferred leads stay quiet.

The exact question matters: “No contracts renewed in Q3” can answer whether any renewed; a launch announcement without renewal figures cannot. That same absence can answer whether the launch announcement disclosed figures. Questions containing a genuine firsthand assertion can still contribute that assertion. The implementation does not reject question marks or negative wording mechanically.

The explicit question-only v2 route and its requests remain unchanged. Older checks keep their original results and do not acquire new answer excerpts retrospectively. Source withdrawal withholds the whole evidence record. No migration or extra model stage is added. New broad checks use the separately metered 9,000-output-token medium profile after two larger tests exhausted 6,000; prior requests retain their original accounting. [Evaluation and limits](../reviews/2026-10-03/substantive-answers-phase-review.md).
