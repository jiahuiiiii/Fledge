# Companion entry and explanations — 9 October 2026

The owner asked to judge the companion proposal and start implementation. [The journey](../../features/companion-journey.md) records the judgment, implemented boundary and remaining work. This is a first research-to-draft slice, not the complete companion roadmap.

## Product judgment

Adopt the private reasoning/review loop and test a first audience of new investors who already hold a few stocks. Clubs are a recruitment hypothesis, not validation. Replace broad competitor claims with a specific workflow proposition; Simply Wall St already offers narratives. Use one sentence with bounded coverage: “Thesis helps you explore an investment idea, keep your reasoning, and review changes in the evidence you follow.”

Keep distinct evidence limitations instead of assigning one confidence score. Never infer a user's investment decision from marking an alert reviewed. Condition suggestions need supported definitions and explicit approval; company-only alerts cannot invent personal relevance. Regulatory review of the actual service, metered unit economics, comprehension and prospective return behaviour remain separate launch/evaluation work. The older Wednesday 7 October test is not an upcoming session.

## Implementation

`CompanionGuide` adds an optional entry inside **Ask a question → Your research**, sharing the current private-question interface. Four questions route to business explanation, growth, disclosed risks and expectations. Business/risk shortcuts focus the exact heading after saved research loads, including an explicit missing/withheld fallback. Other shortcuts focus the selected tab. Selecting a shortcut closes the research and guide dialogs. The guide and prompt clear across company/account boundaries; modal identity also changes on navigation. Fictional scenarios offer three supported routes with explicit fictional wording.

Starter reading actions are local navigation. They do not save questions, generate answers, collect sources, approve conditions or enable watches. The four starters are also available through the original explicit library-selection flow. Custom questions open the existing private interface. A selected starter can prefill only a new idea's question; existing saved question/reasoning remains exact. Sentence-template placeholders and help are not written as user reasoning. The original save, draft, validation, conflict and approval flows remain.

`TermHelp` uses the existing native dialog and 44px labelled controls for revenue, growth, operating margin, free cash flow, P/E, management guidance, analyst consensus and GAAP/adjusted figures. It explains definitions and appropriate comparisons without inventing company-specific findings. Exact financial periods, arithmetic, source evidence, unknown values and restrictions are preserved. Empty-workspace copy invites researching an owned or unfamiliar company without collecting personal financial details.

No new backend, schema, provider, model, analytics, notification, budget or monitoring policy is introduced. A beginner condition wizard, broad evidence-status redesign, personal alert narrative, decision notes and look-back remain proposed, explicitly labelled in the journey.

## Verification

The current shared frontend's 87 tests pass; no totals are added to the earlier 83-test run. Production build passes. Concurrent work split other large components, so the final shared entry size is about 357kB; this task does not claim that reduction as its own optimization.

The guarded `--companion` browser journey uses a fresh disposable database, authored financials/business readings and blocked outbound requests. It verifies all four routes, focused headings, exact source inspection, missing risk coverage, withheld brief content even when raw fields are retained, blank/new versus exact/existing reasoning, cancellation without writes, custom-question entry, guide dismissal and company change. It exercises glossary definitions and focus return, fictional shortcuts and the empty workspace. Responsive guide checks cover 1440/980/390/320px; narrow term/prompt checks cover 390/320px. Screenshots are inspected. These are software/UI checks, not independent financial accuracy or participant comprehension results.

A separate read-only candidate browser checks the owner's saved Broadcom research at 1440/390/320px. It verifies the guide, actual saved business-topic navigation, operating-margin explanation and original reasoning editor without saving. Instrument, versions, private question library, financial depth, news watch and company/private alerts compare exactly before/after. Automatic source-loading writes and external decorative images are blocked. This is a selected saved-data integrity check in local-pitch mode, not a whole-database/ledger audit or managed-login validation.

## Installation and final readback

Source/file-set and prior-index guards passed. The atomic frontend installation serves index `7c3f6ec6192f609a8b805ba4ccbefee9ffa18ad331a351f7ff0d7c75ad245bfd`; all 77 retained candidate assets/fonts and the local-pitch session return HTTP 200 with exact bytes. Earlier installed assets and `.env` remain unchanged. No app or database restart occurred. The final entry is 357.11kB in the shared build.

The same separate Broadcom browser check passes against the actually installed files, with no candidate overlay, at 1440/390/320px. The protected fields remain exact, and its sole attempted mutation is the existing automatic loading route, blocked by the test. Actual and authored screenshots are inspected. Touched-source formatting, JavaScript/Python syntax and scoped whitespace checks pass; the final frontend source manifest is unchanged after installation. No backend suite or fresh ledger/whole-database audit is claimed.

## Failures retained

- Two initial guessed component paths were absent. Root-level `npx` formatting made no progress and was stopped; the installed local formatter succeeded.
- A final documentation patch used a partial paragraph as an exact line and did not apply; the installation note was subsequently inserted at the correct heading.
- The first build occurred during concurrent UI work and could not resolve its not-yet-created `PeerContext` component. No failing candidate was installed.
- The first isolated database could not start inside the sandbox. The guarded offline command then ran with the required local process permissions; no owner database was used.
- The first two browser candidates failed before the guide because a concurrently added loading sidebar referenced `current` before initialization. The loading branch now carries no saved question. A separate nested financial-evidence button introduced during that work was reduced to the intended single exact-value control, retaining its evidence.
- The extended empty-workspace fixture initially cleared the catalogue without setting the API's required `empty` flag. The app correctly showed an empty collection. The fixture was corrected and the full journey passed.
- The first actual-data script tried workspace access before opening the normal local session; it returned no catalogue. Opening the regular session first fixed the read-only check.
- The nested guide exposed a shared native-dialog issue: React propagated Escape cancellation through the portal and closed the outer research dialog too. `Modal` now handles only its own cancellation and stops propagation, preserving the outer dialog and returning focus to its caller.
- Later source-hash comparisons detected ongoing edits to shared files. The concurrent layout task moved the guide into Your research; the earlier test expected a page-level entry and timed out. The final tests use the shared research entry and nested-dialog focus path. Installation waits for the exact tested source, preserving those edits instead of replacing them with an earlier candidate.

Evidence and logs: `.local/live-tests/companion-start-20261009/`. Before-work frontend source, prior installed assets, journey and runner: `.local/backups/companion-start-20261009/`. Original logs and failed attempts remain. The installation report in the evidence directory records the final guarded outcome; installation status must not be inferred from a successful build alone.

No live AI, market/source refresh, email or Telegram dispatch, owner private research/review write or watch enrolment was performed by this task. The separate unresolved FN charge/reservation and original research/access goal are untouched.
