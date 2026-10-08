# Phase 40 — current-source preview beside saved sentiment

This is one agent's five-perspective review, not independent consultant signoff or participant research.

| Perspective | Finding | Response and remaining limit |
| --- | --- | --- |
| Product | Newly retrieved social texts were difficult to inspect without another AI run, and older labels could be mistaken for the latest selection. | Add a read-only current-source preview, including the first-analysis journey; keep saved labels and their original-source view unchanged. No new interpretation is claimed. |
| Research | Source turnover can result from new versions, selection/age limits or parent availability rather than a real change in company sentiment. | Separate selected-version changes, retained-parent changes and comparison-pool changes. Use no market-shift, event-count or materiality inference. |
| Data/ML | An old analysis must not supply labels for texts it never consumed. | Render exact current text without model labels; matching inputs also does not prove the installed method is validated. Existing method/age warnings remain separate. |
| Architecture | Access withdrawal could leak old sources through a new comparison or view. | Build current inputs independently from permitted sources; withhold deltas against unavailable saved readings. Reuse a repeatable-read workspace response and immutable source identities. No new table or provider. |
| UX/business | Students should be able to investigate sources while generation is unavailable, without confusing stored data with a live feed. | Explain local selection time versus source dates, scope and missing coverage. Reuse original-source inspection. Comprehension, recurring use and paid value still require participants. |

## Verification

The focused suite passes 50 checks. Initial failures came from two new fixture errors: an incorrect service entry-point name and an attempted configuration change using the restricted source role. Corrected fixtures use the actual workspace service and the disposable database administrator for source-access setup; the application permissions were not broadened.

The new browser journey verifies exact current news/Reddit/HN text, membership differences, no borrowed labels, source dialogs, no-analysis and empty-platform states, reload and 320/390/1440px layouts. Its first run tried to use the mobile company selector at desktop width; the harness now performs that step at the supported mobile width. Prior failures remain in the saved logs. The existing saved-source reading regression is retained, with withdrawal assertions scoped to saved content rather than unrelated currently permitted texts.

New reads make no supplier/model request. The preview does not repair earlier semantic failures or complete live context-aware testing while the phase-34 charge remains unresolved. Actual-source collection checks and final integrated/browser verification are recorded below when complete.

## Installed result and actual-source audit

The phase is installed with schema 26. Evidence: `.local/live-tests/current-sources-20261003T043317Z/`; pre-change source/database backup: `.local/backups/phase40-current-sources-20261003T043315Z/`. Installation preserved every existing row and private configuration value. The final integrated suite passed 796 backend checks with the retained real-data corpora, the focused suite passed 50, and all twelve frontend checks plus the build passed. Both current-source and saved-original-source browser journeys passed at 320/390/1440px. The saved-source journey initially exceeded its screenshot timeout on a full page; the final capture targets the inspected saved-source section. That harness failure remains in the evidence.

On 3 October, a bounded actual refresh made four Finnhub requests and 42 Hacker News search/original-item requests across Microsoft and NVIDIA. All returned successfully. Original JSON responses and predeclared checks are retained in `actual-refresh/`. No Reddit refresh or paid model request was made.

| Actual company | Current selection | Selection change against saved analysis | Direct original-response checks |
| --- | --- | --- | --- |
| Microsoft | 8 news from 75 candidates; 4 retained Reddit posts; 4 HN comments from 19 candidates | 5 selected news versions replaced; all 4 selected HN comments replaced | All 8 selected news snippets and 4 selected HN texts/dates match returned responses; quote price/previous close/open/timestamp match |
| NVIDIA | 8 news from 50 candidates; 4 retained Reddit posts; 4 HN comments from 21 candidates | All 8 selected news versions and 4 selected HN comments replaced | All 8 selected news snippets and 4 selected HN texts/dates match returned responses; quote price/previous close/open/timestamp match |

These are source-version changes, not new-event counts or sentiment reversals. Candidate counts include eligible retained versions; they are not counts of fresh articles returned in this request. The audit independently checked source membership/deltas against the accessible saved packets and verified that the current projection contains no classification fields.

The first actual audit compared date strings literally and stopped because a stored `+08:00` timestamp equalled the source's UTC timestamp as an instant but not as a string. The audit was corrected to compare timezone-aware instants. It reused all Microsoft responses without repeating acquisition, then completed the single NVIDIA refresh. Both runners/logs are retained; this was a test-harness issue, not a source-time or application fix.

Saved sentiment, answers, themes, private alert checks, reasoning revisions, model/accounting records and all-account watch settings remained byte-equivalent in their canonical record hashes. Existing company/private alert counts stayed at 0/16. The two legitimate news acquisitions added two shared snapshots; the ordinary numerical worker added one evaluation during the audit. Two quote records and 23 new social-source versions were stored. No watch was enabled.

Installed browser inspection verified both companies' separate news/HN selections, dated comparison notices and source-dialog access. It made no acquisition/model request. Earlier saved model labels remain attached to their original inputs. The screenshot is `installed-current-sources.png` in the evidence directory.

The budget remains US$7.407271 confirmed, US$0.301565 reserved, US$2.291164 available under the original ceiling, 194 calls and one blocking unresolved charge. Source fidelity is verified for these selected inputs; the new context-aware model's interpretation, prospective alert performance, broader investor discussion coverage and participant value remain unverified. No full-plan completion or independent consultant approval is claimed.
