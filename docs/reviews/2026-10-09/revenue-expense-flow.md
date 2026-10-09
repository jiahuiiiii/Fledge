# Revenue and expense flow — 9 October 2026

The owner requested a flowing revenue/expense chart. The [contract](../../features/revenue-expense-flow.md) defines accounting scope. Overview and Financials show period controls, compatible revenue categories, profit/cost bands, exact evidence dialogs and expandable detail. Existing complete revenue categories remain in Financials.

Read-only projection of saved Broadcom inputs establishes:

| Period | Revenue | Cost of revenue | Gross profit | Operating expenses | Operating profit | Consolidated net result |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Trailing 4 Aug 2025–2 Aug 2026 | $89.104bn | $27.827bn | $61.277bn | $18.463bn | $42.814bn | $38.265bn |
| Quarter 4 May–2 Aug 2026 | $29.591bn | $9.135bn | $20.456bn | $4.501bn | $15.955bn | $13.088bn |

These are projections over retained SEC inputs, not newly fetched or independently audited statements. The quarter reports R&D $2.895bn and selling/general/administrative $0.996bn, with calculated remainder $0.610bn. Its operating-to-net difference $2.867bn is not called a reported expense. Exact input strings, original definitions and vintages are retained locally.

Focused guarded backend: **74 pass, one optional skip**, covering arithmetic, missing/conflicting values, currencies, fiscal dates, amendments, bridges, net-result definitions, negative/zero values and source/account isolation. Initial fixture failure attempted an older observation time; corrected to actual commit time. Initial frontend: **39 checks**, build/format pass; combined auth/flow candidate: 41 frontend checks.

Guarded business browser passes at 1440/980/390/320px for flow controls, missing history, exact evidence, keyboard/focus, expense remainder, contained phone scrolling and reduced motion, plus existing financial/peer/login cases. Initial SVG assertion used unsupported `innerText`, corrected to `textContent`. Failure logs remain. Final element captures hide fixed app chrome only during screenshots; interactions use normal chrome. Authored screenshots are not actual Microsoft results.

Backup `.local/backups/phase95-revenue-flow/`; evidence `.local/live-tests/revenue-flow-20261009/`. Installation was held for urgent login recovery and combined with [session recovery](session-recovery-and-account-isolation.md), which records final installation/preservation. The feature makes no provider, AI or Telegram request. Independent financial/participant validation and broader forecast access remain open.
