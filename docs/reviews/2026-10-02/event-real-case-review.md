# Actual event evidence: first failure and corrected retest

2 October 2026, approximately 08:39–08:42 SGT. Parent-agent inspection of nine authored conditions against the actual company news already retrieved from Finnhub; no claim that the reporting itself was independently verified. This is developmental evaluation, not a held-out accuracy estimate or student validation.

The three frozen packets used Microsoft, Apple and Alphabet. Each request contained three event criteria with inclusive report dates 30 September–2 October 2026. Definitions and expected classifications were saved before their calls. Prompt v1 made three new calls and matched eight of nine expected classifications. It incorrectly labelled a prospective Microsoft departure as `denied_report`: the quoted headline said the executive was **to leave**, without an explicit denial. The overall outcome for that condition still stayed unknown, but the denial label was materially misleading. The raw result, quotes, charge and first interpretation remain preserved.

Prompt `thesis-event-evidence-2` distinguishes an explicit denial from future tense or insufficient evidence. A new three-call run against the same saved definitions/snapshots matched all nine classifications; explanations and fifteen exact source quotations were inspected against the supplied passages. Unchanged repeat requests reused all three saved results with no new charges.

| Company | Condition | Expected and corrected result |
| --- | --- | --- |
| Microsoft | askpolly integration implemented | Reported confirmation, attributed to the announcement |
| Microsoft | Phil Spencer departure during 2026 | Reported risk; source explicitly says he left that year |
| Microsoft | Ryan Roslansky already departed | Unknown; prospective departure is not completion and is not a denial |
| Apple | Broad corporate overhaul implemented | Unknown; source only describes consideration |
| Apple | Morgan Stanley revenue estimates raised | Reported forecast revision; not observed company revenue |
| Apple | Upcoming Health redesign generally available | Unknown; future capabilities do not confirm release |
| Alphabet | Gemini 4 Argon unveiled | Reported announcement only |
| Alphabet | Gemini 4 Argon paying enterprise revenue established | Unknown; announcement and benchmarks do not establish adoption/revenue |
| Alphabet | Outside AI audits completed | Unknown; voluntary pledge does not establish audit completion |

Code produced combined Microsoft `not_met` because a defined risk was reported, and Apple/Alphabet `unknown` because some required criteria lacked evidence. These are assessments of the authored conditions, not stock recommendations. No model writes SEC numerical observations.

The app now contains clearly labelled Microsoft and Apple pitch examples in previously empty idea slots. The existing Google draft and its three private comparisons were preserved; the Alphabet event evaluation uses a separate local test owner. Both prompt attempts are retained. The corrected Microsoft result and its original source were also opened in the installed in-app browser. Downloads for all three final assessments were generated without source/model requests.

## Evidence and cost

- Initial records: `.local/live-tests/events-v1-20261002T003923Z/`.
- Corrected records and exports: `.local/live-tests/events-v2-20261002T004147Z/`.
- Final read/export verification: `verification.json` in the corrected folder; exact citations, both saved attempts, original Google preservation and unchanged ledger checked.
- Installation backup: `.local/backups/phase9-events-20261002T003739Z/`; all pre-existing rows and private configuration preserved. `event_review_v1.py` additionally preserves the first prompt before correction.
- Six new explicit requests cost US$0.153405. Confirmed cumulative usage is **US$1.07247**. The earlier authorized maximum hold remains **US$0.13926**, for **US$1.21173** committed and **US$8.78827** remaining under the original ceiling. There are 65 request records: 64 settled and the original unresolved request covered by its separate maximum-hold decision. Its actual charge is still unknown.

| Corrected artifact | Exact quotation entries | Elapsed time | SHA-256 |
| --- | ---: | ---: | --- |
| MSFT.json | 4 | 9.421s | `22be7f44aef0b58900c2c857d759eb8544deabc6d7715c50421f0e3ca85562e2` |
| AAPL.json | 5 | 7.853s | `dc8cd176faf75baaf5b354b8a4b6773f782cd1a752f804c984cfd2f50c92a19b` |
| GOOGL.json | 6 | 11.701s | `dff195822b29ac68fdd9bffe35ac0282eaf638cea52fe7009cdc65db1e882b8b` |

The retest validates the correction on these packets, not reliability on unseen event types. No automatic source acquisition, exhaustive historical search, actual occurrence-date extraction, user adoption study or willingness-to-pay test was completed by this run. Pending typed proposals remain separate implementation work.
