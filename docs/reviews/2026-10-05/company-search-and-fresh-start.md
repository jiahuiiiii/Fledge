# Company search and fresh start review

The purpose is to remove two usability obstacles before the owner's Wednesday walkthrough: the fixed six-company limit and crowded, inconsistent form layouts. A separate authorized reset prepares an actual empty user journey while retaining the original spending ledger.

## Implementation

The company dialog now starts with company-name/ticker search over a cached official SEC exchange directory. Sidebar management is collapsed below the results. Registration preserves existing identifiers, uses verified CIK mappings, prevents duplicate or conflicting issuer identities and does not enable a watch or make a model call. The first iteration accepts ordinary one-to-five-letter symbols on supported US exchanges. Share-class formats and a second workspace for an already registered issuer are explicitly unavailable. This is not worldwide instrument coverage.

Existing acquisition adapters now accept registered SEC companies, including daily prices, reference multiples, public analyst targets, news briefings and discussion research. Price/currency/source checks and refresh pacing remain. News/filing/provider gaps are displayed rather than filled. New-company social matching is conservative; company-name aliases have not been exhaustively curated.

The question panel has a separate form body, clearer spacing, shorter helper text and a shared custom checkbox. Native input semantics remain for forms, keyboard use and assistive technology. Search has bounded result scrolling, delayed local requests, ignored late responses and an explicit directory-update action. Escape closes the search dialog. Motion respects reduced-motion settings.

A fresh workspace now has a first-company action and empty states across navigation tabs. The operator reset archives the full database and clears research tables in one transaction, preserving accounting and configuration. Ordinary restarts preserve the empty state. Archived research is recoverable, not permanently destroyed.

## Verification

The full offline run completed with 1,080 passing cases, 55 skipped retained-corpus cases and one outdated US$20 budget assertion. That assertion was changed to read the approved cap, preserving its test of private charges enforcing the shared limit. All 15 focused budget/privacy/reset cases then passed, including the corrected case. This establishes 1,081 distinct backend cases across the runs, not a second complete full-suite pass. Earlier selected runs and the corrected conservative ticker-match test overlap this total. Twenty-two frontend checks and the production build passed.

Browser verification covers search by name, adding a non-preset AMD workspace, custom checkbox keyboard/appearance, Escape dismissal and 320/390/1440/1920px layouts. The reset/restart journey covers stale bookmarked links, all-company empty tabs, first-company addition, history navigation and reload. The existing question journey covers saved answers, citations, parent context, exports, follow-ups and failure-preserved input without new model calls.

Actual-source and installation records are appended below after verification. No paid model test is required for this change. Historical sentiment/answer correctness failures are not resolved by UI work or a database reset.

## Five perspectives

- **Product:** Search removes a clear onboarding dead end. Keep the first session centred on two companies and one complete idea rather than more features.
- **UX:** Search-first layout, less helper prose and consistent controls reduce scanning effort. Empty and provider-error states need equal attention during the owner's test.
- **Architecture:** Cache public identity separately from research. Preserve immutable saved histories during normal use; only the explicit backed-up operator reset bypasses them. Preserve source gates and the single ledger.
- **Evidence:** Real acquisition verifies transport and identity, not investment conclusions or model accuracy. New-company social coverage remains narrower than the six curated aliases.
- **Business and testing:** A 45–60 minute guided session and structured feedback should identify pitch blockers efficiently. One owner session is useful feedback, not proof of customer demand.

## Installed result

Installed source backup: `.local/backups/phase73-company-search-20261005T021934Z/`. Evidence: `.local/live-tests/company-search-20261005T021934Z/`. A full restore of the pre-install archive into a temporary database recovered all eight original companies and exactly matched the current accounting hash. The temporary restore database was then removed.

A real non-preset AMD case retrieved the quarter ended 27 June 2026, Finnhub quote and news, 251 daily price sessions, reference multiples and public analyst targets. Every adapter completed; no idea was saved and no watch enabled. The provider accounting hash stayed exact. This verifies real acquisition and symbol routing, not AI interpretation quality.

The requested reset then archived the complete pre-reset database at `.local/backups/fresh-workspace-20261005T022236Z/database.dump`. Its reset report lists all cleared research tables. Post-restart inspection finds every active research table empty, `seed_demo=false`, and no watches. Keys and settings were not edited. Cumulative accounting remains US$15.9377945 confirmed plus US$0.60249 retained maxima, leaving US$13.4597155 of US$30 across 306 calls, with no blocking unresolved request.

The installed empty screen, recovery of an old company URL, cached real-directory AMD search, Escape dismissal and reload pass in a read-only browser check that rejects all writes. Separate disposable SEC and question browser journeys pass. Screenshots are retained with the evidence. Wednesday's first session is left empty; no test company was added after reset.

Final interaction regression also passes: desktop/phone sidebar removal, undo, reload and restoration; custom menu mouse/keyboard/typeahead/Escape/Tab behavior; persistent navigation frame; delayed inbox skeleton; and no navigation-triggered workspace refetch. It exposed and fixed expanded dialog content extending below the viewport. A separate delayed-add test verifies that completion cannot override a newer company/tab selection. Valid company links are preserved when the reset marker is first observed in a new browser.
