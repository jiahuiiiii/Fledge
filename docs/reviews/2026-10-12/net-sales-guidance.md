# Net sales guidance and prior-period comparisons — 12 October 2026

The owner reported Amazon's **Format needs review** management revenue outlook and asked for a fix. The retained original release was already present; collection was not the problem. Its “Net sales” label was absent from the whole-company revenue grammar. The remaining operating-income passage compared against Q3 2025, which the reader combined with the Q3 2026 guidance heading as conflicting forecast dates.

## Change and limits

`sec-management-outlook-3` adds whole-company net-sales prose/table labels and recognises bounded explicit comparison suffixes. Only an explicitly older period with matching quarter/year and fiscal/calendar conventions is removed from forecast-period detection. Same-period, future, unlabelled and mixed-convention comparisons require review. Authored negative cases cover segment sales, other issuers, conditions, reversed growth ranges, actuals and multiple forecasts.

The full quote, evidence offsets, context and immutable original remain exact. There is no issuer branch, inferred currency, GAAP basis or ending date. Amazon's original range is $197–202 billion, labelled Q3 2026 with exact date and currency unspecified. This is the latest saved release's named-period guidance, not a verified current Q4 forecast. Other outlook formats remain bounded rather than universally supported.

No collection, AI generation, paid request, watch change, schema migration or database restart is part of this fix. The teammate's login/onboarding patch and unrelated frontend work remain preserved.

## Evidence

Evidence: `.local/live-tests/net-sales-guidance-20261012/`. Backup: `.local/backups/net-sales-guidance-20261012/`.

- Focused outlook/format/disclosure suite: 114 passed, including the exact saved Amazon release and nine-company retained release corpus.
- Read-only replay over all twelve currently saved companies: Amazon changes from `unsupported_format` to `named_period`; every other company's full projection remains exact except the versioned method identity. Missing BABA release and AAPL/MSFT absent numerical outlooks remain explicit gaps.
- Full offline backend suite: 2,006 passed, 93 optional skips. Frontend: 158 passed. Source syntax and diff checks pass. No frontend rebuild was needed for this backend-only correction.
- Candidate and installed browsers each pass 14 cases: all twelve companies, original evidence and SEC links, desktop keyboard/Escape/focus return, plus Amazon at 390 and 320 pixels. The reported Overview card shows $197–202bn and Q3 2026. Screenshots of the card, outlook and full source quotation were inspected; no browser errors or overflow. Browser writes and external requests were blocked.
- Idle app-only installation: PID 29025 → 92323, with the worker advisory lock reacquired. All 116 tables, schema 49, environment and ledger are exact across installation. All 163 installed frontend files remain exact, including index `c6a4cf0c`; the database was not restarted. A private pre-install database dump and source copies are retained in the backup directory.
- Final verification repeats the table, ledger, source/configuration/frontend hash and worker checks after the installed browser suite: all remain exact. The durable summary is `verification.json` in the evidence directory.

Preserved diagnostics: the first sandboxed database read was denied and succeeded with reviewed local-socket access; the initial status query referenced a nonexistent `telegram_connections` table after all twelve snapshots had been saved; the first replay equality check included the intentionally changed nested method identity, and the corrected comparison excludes only method fields. These attempts made no database writes.

The first installed browser harness compared Python's space-separated timestamp strings with the API's ISO `T` serialization, rejected an otherwise correct Apple response and timed out. A direct field comparison confirmed only that representation difference. Fixtures now use the API encoder; the corrected installed suite passes without another source edit or restart. The original failure log/body are retained. Early status checks before backup completion and a sandbox-denied process listing are also retained; reviewed read-only process inspection confirmed normal completion.
