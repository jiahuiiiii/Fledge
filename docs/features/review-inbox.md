# Combined review inbox — phase 26

Open **Updates** for one chronological list of published changes to saved reasoning, company news/social sentiment and monitored conditions. The default includes all retained dates, across the local account's ideas and watches, awaiting review. Each row identifies its company and update type. The company selector in this inbox is independent of the workspace watchlist selection.

The global inbox hides the last-opened company's header, idea panel, mobile selector and source-refresh toolbar. Company research remains reachable from the main Workspace navigation, desktop watchlist and each update. This prevents an unrelated company from appearing to own the entire inbox.

Choose a company or review status, then expand a company/private alert to inspect its exact evidence. A condition change opens the original assessment in History. Opening evidence does not acknowledge an alert. Existing explicit review actions preserve the saved idea and remain independent for every record. Quiet private checks remain in History.

Counts cover the entire selected company scope, independently of the twenty-row page size and selected review-status filter. The matching-record total and page position appear separately. Pages retain their original end cutoff; review states are current. Ordering uses the time the application recorded the update, not the underlying event's time. **Refresh inbox** reloads saved records without fetching sources or invoking a model. Successful acknowledgement returns to the first page.

The source-coverage disclosure shows missing/failed/old checks and disabled watches, including when no update is awaiting review. A quiet inbox does not establish that nothing happened. Recorded companies remain labelled fictional. Withdrawn evidence cannot appear in previews or expanded derived interpretations.

## Presentation follow-up — 9 October 2026

Updates uses grouped company/status filters, compact whole-scope count badges and clearer company/type/date headings on the update cards. Company/private card disclosures own an explicit arrow beside **Inspect evidence**, which becomes **Hide evidence** when expanded. The shared disclosure pseudo-chevron is suppressed only on those card summaries, preventing a stray border line above the ticker; source coverage and nested disclosures keep their own arrows. The entire summary remains keyboard accessible, with a visible focus outline and reduced-motion support. The weekly-review banner retains its inner padding, including with the compact company rail.

Opening evidence still does not acknowledge an alert. Exact source inspection, explicit review/unresolved actions, condition-history links, original recorded ordering, whole-scope counts, cutoff pagination, company/review filters, coverage warnings and withheld interpretations retain their existing behaviour. See the [UI correction and verification](../reviews/2026-10-09/updates-ui.md).

## Reuse and boundary

This uses the existing owner-scoped periodic-review query, its whole-history counts, source-access checks and stable pagination. Existing company/private alert components are embedded without their separate headers and filters. No new backend, schema, prompt, model, source or dependency is introduced. No historical records are rewritten, and installation does not enable watches.

Weekly review remains available for date filtering and a complete filtered download. The inbox makes saved updates easier to inspect; it does not broaden acquisition or establish alert relevance, detection delay, user comprehension or recurring value. It refreshes on entry, filter/page changes, explicit refresh and successful review; it adds no background polling.

## Verification

Ten frontend tests and the build pass. Thirty-seven focused backend checks cover the reused query, reporting updates and watch history; the previous phase's 541-test full-suite result is a historical baseline, not a new full-suite run.

The new authored browser fixture has 26 published updates across two companies and all three types. It checks exact page order/counts, filters, source inspection, independent review, exact condition navigation, delayed-response rejection, failed-request recovery, withheld previews and 320/390/1440px layouts. Existing sentiment, private-alert, changed-report, weekly-review and condition-expiry journeys also pass. Phone/desktop screenshots were visually inspected. These tests use disposable authored records and mocked providers, with no paid calls.

Evidence is retained in `.local/live-tests/review-inbox-20261002T092150Z/`. Initial test failures are preserved: a heading locator became ambiguous after previews were added, the older weekly test expected one private alert despite a two-alert fixture, and the new inbox test initially read a filter result before its request completed. Final checks retain the original behavioral expectations and wait for the corresponding view.
