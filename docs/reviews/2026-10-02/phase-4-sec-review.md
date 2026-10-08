# Phase 4 — structured filing fundamentals

Three AI threads reviewed architecture, product/UX and evidence/business. They are consultant-style development feedback, not independent professional or user validation. The delivered scope is an offline-verified SEC capability; live compatibility and filing reconciliation remain pending contact configuration.

Corrections from review:

- Material source identity excludes unused/reordered facts and canonicalizes selected numeric values. Equivalent JSON number spellings create no review noise; parsed raw payload changes remain retained.
- HTTP parsing preserves fractional numeric lexemes before Decimal calculation. The calculation trail retains exact selected values, explicit precision and display rounding limits.
- Older filing responses cannot replace the active reporting period or imply successful current coverage.
- Failed refreshes reload persisted coverage into the UI without retrying network access.
- Annual/quarterly scope appears in both sides of an edit conflict. Scope edits reset monitoring approval. Unknown outcomes explain the mismatch.
- Add-company errors appear inside the dialog with selection retained. The saved-idea panel explicitly says that filing retrieval requires a manual refresh.
- A restricted shared-source role cannot read private ideas or model accounting. HTTP is outside short serialized transactions. Local source-age/interruption checks make no HTTP request, and stale attempts are fenced.
- Completion/failure/default clock timestamps are taken after the collection lock, preventing a concurrent clock tick from making a valid completed response appear older than state.
- A successful source checkpoint pins the active immutable version, so a correction returning to an earlier value updates current facts without erasing intermediate history. A focused architecture re-review found no blocker; its minor return-flag issue was corrected so reactivation reports a change and a subsequent identical refresh does not.

The two browser journeys passed, including scope-only conflict resolution, immediate denied-source display, exact historical calculation inputs, empty/configuration states, approval reset, original recorded scenarios and responsive widths from 320px. Test counts and delivery verification are in [implementation status](../../archive/status/implementation-status.md).

No live financial data, new model calls, data subscription, publication or customer-validation result is implied. Original source reuse remains Kestrel UI/evaluation and Deus normalization/evidence contracts; the SEC adapter and calculation rules are new modules using the existing HTTP/database dependencies, not an imported financial-data platform.
