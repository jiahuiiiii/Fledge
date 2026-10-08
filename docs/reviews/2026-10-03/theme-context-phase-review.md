# Phase 37 — saved conversation context in discussion themes

This is a parent-authored review from five perspectives, not independent consultant signoff or participant evidence.

| Perspective | Finding | Response and remaining limit |
| --- | --- | --- |
| Product | A reply could be interpreted with its parent in sentiment/private alerts but without it in the theme summary. | Both theme synthesis and its evidence check now use the same parent pinned in the original classified sample. This aligns their inputs; it does not prove a better interpretation. |
| Research | A parent headline or opinion can be mistaken for the reply's own argument. | Keep separate child-body and own-parent citations per claim. Require expressed child stance/argument, preserve ambiguity and forbid parent-only facts as child findings. Exact quotes still do not certify semantic support. |
| Data/ML | Passing rendered parent evidence wholesale into the second stage would also send unselected raw body text. | Project only selected parent citations for each candidate claim. Supply bounded eligible parent passages separately for detecting omission/contradiction, never for repairing unsupported claims. |
| Architecture | A later parent edit or removal could corrupt immutable source history or trigger wasteful regeneration. | Reuse pinned analysis context, stable request identities and whole-analysis withdrawal. Keep the two existing stages and single ledger; add no data service, migration or automatic watch step. |
| UX/business | Adding parents can make a small discussion sample appear larger or independently corroborated. | Parent evidence has its own disclosure, dates and link; selected-text counts remain based on original children. The update does not establish investor coverage, prospective alert value or paid demand. |

## Contract

The new synthesis prompt is `thesis-discussion-themes-7`, evidence policy `theme-source-title-parent-2`, and second-pass policy `discussion-theme-evidence-check-2`. Each continues to use the unchanged model and 6,000-output-token profile. The second step filters complete themes/gaps without rewriting candidates. Parent loading stays explicit and does not update earlier sentiment samples, summaries or alerts.

Theme preparation inherits at most four parents/8,000 combined passage bytes from the sentiment sample. It never looks up current parent state to replace the saved version. A claim with supplied parent context needs one or two valid own-parent references and at least one own-child body citation. Parent quotations remain separate from aggregate child citations and do not increase source counts. All older saved formats, prompts, results and method notices remain intact.

Both stages treat sources as untrusted input. Parent raw bodies, unselected title text, original links and storage/check metadata are excluded from candidate claim inputs to the checker. Its separate full-source context contains only eligible passages. The original raw parent is still available for human inspection, explicitly separated from selected model evidence.

Withdrawal before synthesis prevents dispatch; withdrawal after synthesis prevents the second step; withdrawal during or after checking withholds the saved result, history and download. Failed/invalid results remain auditable and are not automatically retried. No watch is enabled or new alert emitted by this phase.

## Evaluation limits

The phase-34 Amazon timeout remains unresolved; no new paid model call is authorized through that block. New sentiment, private relevance and theme-context quality must still be tested against actual model outputs. Earlier semantic errors, rejected candidates and the interrupted request remain retained. More software tests and input audits cannot establish that those errors are fixed.

Frozen actual-source request projections, if recorded below, use explicit authored placeholders and all candidate texts. They validate provenance and request boundaries, not the production relevance filter, semantic themes, user usefulness, prospective monitoring, precision or recall. No authored projection is promoted into company research.

## Next quality gate

When the separate paid-dispatch decision is resolved, evaluate the retained Microsoft/NVIDIA contexts against predeclared criteria, including parent/child attribution, unresolved pronouns, reported plans and same-issue disagreement. Do not retry the interrupted request or declare whole-feed accuracy. Broader social-source continuity, question research context, participant comprehension and the remaining plan requirements stay open.


## Verified software and installed evidence

754 integrated backend checks pass with both retained actual SEC corpora. The focused theme/context suites pass 86 checks; twelve frontend checks and the production build pass. Automated providers are mocked and databases disposable. New cases cover both-stage parent identity, selected-versus-raw passage boundaries, exact citations, unchanged source counts, malformed/foreign/duplicate references, old sample preservation, cache reuse despite later parent changes, and withdrawal before/between/during/after the two stages. The checker can filter a failed theme without mutating surviving evidence.

The authored theme browser journey passes at 320/390/1440px: parent and child text remain separate, source links and downloads work, old format/history stays readable, unchanged requests reuse saved results, watches/labels remain unchanged, and failure/withdrawal states work. Installed review found that disabled generation needed an explanation beside the button. The final UI adds that message and the browser test checks the disabled state explicitly.

Backup: `.local/backups/phase37-theme-context-20261002T224323Z/`. Evidence: `.local/live-tests/theme-context-20261002T224325Z/`. Installation preserved every preexisting database row and the private environment. Schema remains 25 and all main/QA news and filing watches remain off.

Two actual retained Microsoft/NVIDIA samples each contribute sixteen original candidate texts to undispatched request-shape audits. Both new stages preserve the five saved parent identities/eight eligible parent passages matched against original HN responses and phase-35 sentiment inputs. Authored placeholder claims select five separate parent quotations to verify checker projection; these are not model findings or relevance-filtered product results. All three previously published theme results remain exactly unchanged and carry their original methods; no parent context was retrofitted into them.

The installed NVIDIA theme panel still opens the retained result and original passages. Paid generation remains disabled; reading does not dispatch either stage. New-method semantic quality is not verified. No new model/source request or publication occurred.

Original cumulative budget unchanged: US$7.407271 confirmed, US$0.301565 reserved, US$2.291164 remaining, 194 calls. One unresolved Amazon charge blocks new dispatch; its US$0.162305 maximum and the earlier authorized US$0.13926 maximum remain held with actual interrupted costs unsettled. The full implementation plan and participant validation remain incomplete.
