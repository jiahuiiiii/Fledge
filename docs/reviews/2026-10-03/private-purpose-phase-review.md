# Explicit purpose for private checks — phase 46

The previous live test showed a concrete product mismatch: a request for a reported Copilot retention rate generated two indirect investment-risk alerts. A user's factual question and a broad investigation of an investment belief need different output contracts. This phase adds an explicit purpose choice without silently removing the broader research workflow.

## What the user can do

In the news/social panel, **Check focus** offers **Connections to my reasoning** and **Answers to my saved question**. The broader choice remains the default and keeps the existing supports/challenges/risks/answers behavior. The question choice shows the exact saved question and looks only for concrete attributable answers. Related background, ambiguous connections and unrelated sources remain quiet history.

An enabled watch has the same distinction in **Alerts to receive**, alongside company-level updates. Existing watch settings retain their broad reasoning purpose. A question-only draft is sufficient for question-focused checking; the user does not need to invent an investment belief. Reasoning mode still requires saved reasoning. Changing purpose starts a quiet baseline and does not reinterpret already-seen sources as new events.

The chosen purpose is pinned in each request and shown with saved results, individual exports, periodic reviews and scheduled-check history. Earlier records keep their existing meaning and outputs. Choosing a control, reading history or inspecting sources makes no paid request. Watches remain opt-in and run only while the local app is running.

## Implemented contract

The separate question method `thesis-question-watch-2` sends the exact saved question, selected original sources and pinned parents. Saved reasoning remains in the immutable review record but is excluded from this mode's model input. The allowed results are `answers`, `context`, `unclear` and `unrelated`. Code rejects directional labels or reasoning anchors in this route; only an exact saved question segment can anchor an answer. This prevents one specific category mismatch, not every semantic error or an incorrect answer classification.

The question schema binds each result's item ID to that source's passage IDs. A source without a saved parent cannot return parent citations; a source with a parent must cite its own child body and its own parent passages. Evidence fields precede explanation prose. Complete coverage, exact membership/quotes and access checks remain independent validations. This uses supported nested `anyOf`, enum and array constraints in OpenAI's [structured-output contract](https://developers.openai.com/api/docs/guides/structured-outputs), not another model stage or generic evidence checker.

The broad `thesis-watch-relevance-7` request and cache identity remain unchanged for the same inputs. Its known noisy-risk behavior remains unresolved. The question route is a user-selected purpose, not a hidden filter substituted for belief monitoring.

Migration 028 adds the purpose to current watch settings and immutable scheduled attempts, defaulting existing rows to reasoning. The other saved tables remain unchanged. Automatic dispatch derives purpose from the persisted watch, not a caller-supplied override. A changed purpose/lease during a request prevents current publication. Manual checks of a different purpose do not consume unseen material needed by an active watch; watch configuration and state consumption are serialized.

## Verification

- The broad isolated suite passed **870 backend checks**, with all four retained actual-source corpora configured. A subsequent **49-test focused run** passed after the source-bound schema correction, overlapping the broad run and including one additional source/parent-schema case.
- Fourteen frontend checks and the final build passed. Static undefined-name/syntax checks passed. An exploratory broader lint scan found existing style findings; it was not a clean lint gate and no unrelated style rewrite was performed.
- The final private-alert browser journey passed at **320, 390 and 1440 pixels**. It checks manual purpose selection, persisted watch purpose across frequency changes, quiet baseline on switching, current/historical purpose labels, source opening, download, review and archive behavior. Focus controls and inbox screenshots were inspected. The installed NVIDIA workspace was reloaded and displayed both focus choices with broad reasoning still selected; no check, save or watch was activated. API purpose dispatch is covered separately with a mocked model; the browser makes no paid calls.
- Tests cover rejecting risk/support/challenge labels, wrong/missing/dual anchors, exact request/cache separation, quiet classifications, question-only drafts, invalid choices, owner isolation, purpose-switch races, manual/watch interaction, scheduled-history preservation and exports.

Two newly authored assertions initially used a nonexistent workspace helper; they were corrected to the existing `service.state` API. One build invocation used an unsupported command option and was rerun successfully from the frontend directory. Neither was a product-behavior failure. Retain those logs alongside the actual provider failure below.

## Actual-source evaluation and correction

Four packets and expected answer IDs were frozen before dispatch. They use retained Microsoft/NVIDIA news and public discussion with authored research questions. Before any dispatch, a weak platform-revenue absence control was replaced by the closer buyback-execution control, preserving the original freeze. No provider result informed that replacement.

The initial question method completed three cases and was rejected on the departure case because it supplied parent citations for a comment that had no saved parent. Its prose also invented a separate parent from quoted wording inside the child. The rejection prevented publication. This paid failed output is preserved, not repaired or treated as success.

The corrected method restricts citations by source in the response schema and explicitly distinguishes saved parents from quoted text. All four unchanged packets and expectations were then evaluated again through distinct explicit requests. There is no automatic paid retry.

| Case | Expected and observed under the corrected method |
| --- | --- |
| Microsoft code-review study | The previously excluded discussion supplies one attributable answer: 44% named defect finding as their top review reason, while 14% of comments concerned defects. Other texts remain quiet. No financial effect or proven bug-detection benefit is claimed. |
| Microsoft Copilot paid-seat retention | All 15 texts remain quiet. The executive-departure report and broad AI-spending opinion do not become retention risks or substitute answers. |
| Ryan Roslansky departure timing | Two news reports supply answers. “Will leave at the end of 2026” and “will stay through year-end as an advisor before departing” remain planned timing, not completed departures. |
| NVIDIA buyback execution | All 16 texts remain quiet. The reported additional US$150bn authorization and US$235bn remaining buybacks do not establish how much of the new authorization was executed. |

The final four responses meet **61/61 predeclared answer-versus-quiet decisions**, with three answer items and 58 quiet items. All 106 source-quotation associations and 12 parent-quotation associations match the supplied originals. This is a selected development set with agent-authored expectations, not a broad accuracy benchmark or independent participant evaluation.

All final answers and explanations were reviewed. No additional material error was identified in the three answer items; attribution is also visible in the source cards. One quiet explanation calls a terse HN remark a joke, although the source does not establish humorous intent. This remains an interpretation concern; source-bound citations do not guarantee faithful tone or prose. No internal anchor IDs appeared in these final explanations. The previous broad-mode risk failures and other sentiment/answer failures remain open.

No output was published into the owner's research. These tests do not establish actual return-visit value, prospective alert timing, complete source coverage or profitable decisions.

## Installation and spending

Evidence is retained in `.local/live-tests/private-check-purpose-20261003T070400Z/`, with the corrected run under `source-bound-v2/`. Source/database backup: `.local/backups/phase46-check-purpose-20261003T071214Z/`. Preservation hashes are recorded in `install.json` and `final-verification.json` there. Schema is 28. All preexisting column values are preserved; the new purpose fields default to reasoning. All news/filing watches remain off.

Eight calls cost **US$0.339418** in total, including the rejected response. Confirmed cumulative usage is **US$10.5324895** across **245 calls**, plus unchanged **US$0.301565** historical maximum accounting, leaving **US$9.1659455** of the same **US$20** allowance. No new unresolved charge, source acquisition, product publication or outside message occurred.

## Five-perspective review

These are five perspectives applied by one agent, not independent consultants or customer research.

| Perspective | Assessment |
| --- | --- |
| Product | An explicit question-answer purpose aligns the alert with the user's requested evidence. Broader reasoning investigation remains available and still needs quality improvement. |
| UX | The exact question, visible focus control and historical purpose label explain why a check is quiet or actionable. Actual student comprehension and tolerance for two modes are untested. |
| Research | Positive cases survived the narrower contract and both close controls stayed quiet. A retained structural failure led to an enforceable constraint, while the remaining tone gloss demonstrates continuing semantic limits. |
| Engineering | One ledger, source sample and publication system serve both modes. Versioned question requests, quiet purpose changes and serialized seen-state updates prevent silent reinterpretation or missed cross-purpose work. |
| Business | Better alignment between saved questions and updates strengthens the pitch demonstration. It does not prove recurring usage, willingness to pay or the quality of broader investment-risk alerts. |

The broader implementation plan remains incomplete. Next work should improve source-grounded reasoning/sentiment output and evaluate the remaining plan requirements, without treating this selected four-case result as general validation.
