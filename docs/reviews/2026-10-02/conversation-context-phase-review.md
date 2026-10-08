# Conversation-context phase review — 2 October 2026

Parent-authored review from five perspectives, not independent consultants or participant research.

| Perspective | Purpose check and decision |
| --- | --- |
| Product | Users investigating social sentiment need to see what a reply addresses. Add immediate-parent inspection within the existing source dialog, preserving a direct path back to the original discussion. |
| Research | Six actual comment/parent probes include an ambiguous AI remark, security-policy discussion, an AI-funding reply, present respect for NVIDIA, a space-computing link and a benchmark question. Parent text can explain the topic but cannot automatically supply the reply author's stance. Keep it separate from saved model interpretation pending comparative evaluation. |
| Engineering | Reuse HN's original-item transport and persistent clock. Verify the child before retrieving its parent, limit to two requests, retain immutable results and fence late attempts. No new model, budget or provider is needed. |
| UX | Expose a plainly named question in the source dialog, distinguish parent message/headline from original comment and show both publication and retrieval dates. Cached reads are free of supplier calls; collection is explicit. Label missing/failed/changed/removed states and keep long text usable on phones. |
| Commercial/evaluation | Source inspection strengthens the pitch's traceability but is not measured time saving or recurring value. Compare users' understanding of ambiguous replies with and without context before treating it as a paid benefit. |

The original-source probe is retained under `.local/live-tests/conversation-context-probe-20261002T140639Z/`. Twelve public item requests retrieved six current comments and six parents. It used no model calls. Those checks motivated source inspection, not an unsupported automatic sentiment upgrade.

The initial focused source/inspection suite passed 43 checks. The integrated suite passed 668 checks with both actual SEC corpora. Twelve frontend checks and the build pass. The first browser run completed the flow but failed its final POST count because the specific mock route bypassed the generic route counter; the counter now observes requests directly. Preserve the initial failure. The final conversation browser passes cached source reading, explicit mocked acquisition, failure recovery, original-parent links and 320/390/1440px layouts. Collection transport itself is exercised by the real API handlers and mocked-provider backend tests.

Review refinements: changed “separate author” to “separate message” because a parent may be by the same person; prevented late cached reads or responses after closing from replacing current UI state; let the cooldown expire without requiring a page reload. The source-removal callback closes the source and refreshes the affected saved research.

## Installed actual-source verification

Schema 24 is installed. Backup `.local/backups/phase32-conversation-context-20261002T142235Z/` preserved the previous source/database; all prior row values and private configuration survived installation. Final evidence is `.local/live-tests/conversation-context-20261002T142237Z/`. Six installed checks made twelve fresh original-item requests: three Microsoft comment parents and three NVIDIA story parents. All 24 selected parent fields (type, title, body, original link) matched the recorded original API responses, and each cached re-open reused its saved result. The earlier discovery probe is separate, another twelve requests; neither sequence is a classifier evaluation.

Saved sentiment/social records, all private semantic tables and model-call hashes are unchanged. Processing cursor clocks are excluded from semantic preservation because they advance normally; no false all-database-unchanged claim is made. All news/filing watches remain off. The original budget is unchanged: US$6.215791 confirmed plus US$0.13926 held for the original interrupted request, 173 calls, US$3.644949 remaining. This phase made zero model calls; the original interrupted cost remains unsettled.

The installed NVIDIA Vulkan comment and its original Janus parent headline were inspected in the actual browser. The first phone view pushed the parent below lengthy explanatory text; the final compact layout moves the original evidence above the refresh control and passed the conversation browser again. The existing social-platform browser regression passes. Model-context interpretation, broader feeds, prospective alert quality and participant value remain unverified.
