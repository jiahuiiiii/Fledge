# Phase 38 — saved reply context in question research

This is a parent-authored review from five perspectives, not independent consultant signoff or participant evidence.

| Perspective | Finding | Implemented response and remaining limit |
| --- | --- | --- |
| Product | Question research already selected HN replies, but dropped platform identity and original-parent context. Requiring sentiment first would weaken the research-first journey. | New questions independently select saved texts, then attach eligible exact-comment parents. No saved idea, classification or watch is required. Broader source reach remains incomplete. |
| Research | A parent could be mistaken for a child's view, or its citation could be borrowed by an unrelated answer point. | Each answer/point has its own child citations and separately scoped parent references. Parent-only facts, implied agreement and unresolved pronouns are disallowed by instructions; reference validation does not prove semantic support. |
| Data/ML | Adding parent text to ranking or counts could silently change the sampled population. | Rank original texts first and retain the existing source/byte limits. Parents add no candidates or votes. Preserve platform counts and exact dated input versions. |
| Architecture | Question research has its own source packet and cannot inherit sentiment's withdrawal check. | Apply the shared parent access check directly to every consumed question packet, including cached history and export. Reuse owner policies, ledger and immutable storage without a migration. |
| UX/business | A student should see what evidence was used without confusing a new method with proven accuracy. | Answer evidence shows selected child/parent support; source inspection shows all eligible parent input passages. Older answers retain a neutral method notice. Comprehension, recurring use and paid value remain unmeasured. |

## Verification

769 integrated backend checks pass with both retained actual filing corpora. The final focused question/context suite passes 51 checks. Twelve frontend checks and the production build pass. Automated model providers are mocked and databases are disposable.

The first new fixture assertion incorrectly assumed there were only news and social sources; its existing filing table was correctly included. The assertion was corrected to verify all three source channels. The retained initial failure was test setup, not a model or source-selection failure. A display-spacing issue found during review was corrected and the responsive journey rerun.

New checks cover standalone question input without an idea/sentiment result, platform identity, generic-title exclusion, exact child/parent quotations, same-day reuse after an identical parent recheck, changed/later context with immutable old answers, reference boundaries per answer/point, source withdrawal during/after generation, private ownership, exports, explicit social opt-out, stale context and a failed original-comment check. Existing tests continue to cover question-only follow-up context, source selection, numerical table periods, history, no-source abstention and schema/privacy boundaries.

The authored browser journey passes at 320/390/1440px: cached answers and follow-ups, source dialogs, selected parent evidence, all supplied parent passages, platform counts, actual private downloads, draft opening without saving, failed-request input preservation and reload/history. No source/model request is made. Authored model outputs are interface fixtures, not semantic evaluation results.

## Contract and quality boundary

The new prompt is `thesis-research-answer-4`, using the unchanged model, 6,000-output-token profile and original cumulative ledger. It consumes up to eight news snippets, three social texts and available annual/direct-quarter tables; only the selected HN comments may receive eligible saved parents. A parent is never independently searched or fetched by asking a question. No previous generated answer enters the evidence.

The phase-34 Amazon timeout still blocks new paid dispatch. No fresh model result is produced in this phase; the earlier sentiment, private-alert and theme context changes also remain untested against actual new-model responses. Input matching and mocked tests cannot establish that previous semantic errors are fixed. Preserve those failures and the original charge reservations.

The next model evaluation should test parent/child attribution, ambiguity, reported versus completed events and whether the question remains unanswered when the supplied evidence is insufficient. Broader social-source continuity, prospective alert performance, remaining fundamentals/valuation work and participant validation remain open.

## Installed evidence

Backup: `.local/backups/phase38-question-context-20261002T230420Z/`. Evidence: `.local/live-tests/question-context-20261002T230422Z/`. The installation preserves every preexisting database row and the private environment; schema stays 25. The app was restarted on port 8841.

The installed production selector was exercised read-only with two authored development questions about retained Microsoft security discussions and NVIDIA inference/driver discussions. Microsoft selected eight news snippets, three social texts (two HN, one Reddit) and two filing tables, attaching one saved parent with three eligible passages. NVIDIA selected seven news snippets, three HN comments and two filing tables, attaching two parents with two eligible passages. Two other selected HN comments had no saved context and were explicitly left without it. Parent identities, original child text, publication times and all five supplied parent passages match the retained original API responses and exact immutable database results. No source fetch or model dispatch was performed. These selected questions do not constitute an independent relevance benchmark.

Both complete requests and predeclared semantic criteria are frozen as undispatched input evidence. Model inputs omit storage/check metadata and raw parent bodies, exclude generic HN titles, stay within the existing source limits and pass request-size estimation. Parents add no source candidates. This checks actual production input construction, not the quality of an answer that has not been generated.

All three main-account answers remain accessible with exact original results and no added context. The installed browser confirms the latest saved Microsoft answer and the neutral earlier-method notice; new generation remains visibly disabled. The responsive authored journey was run after the spacing fix; the final neutral-notice wording was then verified in the installed browser. Main and QA news/filing watches remain off.

Budget is unchanged: US$7.407271 confirmed, US$0.301565 reserved, US$2.291164 remaining, 194 calls, one blocking unresolved charge. The original authorized US$0.13926 hold is still unsettled. No new answer, alert, classification or theme was published by this phase.
