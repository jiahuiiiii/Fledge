# Summary cards and dedicated Account page — 25 October 2026

The owner asked to align Summary's large coloured indicators with the current
UI and replace the Account dropdown with a navigable page, using existing parts.

## Presentation

Summary's News, People online and World links now compose shared `Card` and
`SectionHeader` on neutral surfaces, with compact count text and a quiet arrow.
The counts and their ordering remain exact. Removed the standalone shape legend
and large decorative shapes; the price change uses the existing text and a
shared badge with one short context line. The cards still jump to the same
source sections. No reading, classification or calculation changed.

Account is available at `?view=account` from the top-right link. It uses existing
shared headings, cards, buttons and badges, the original `ProModeSwitch`, the
original profile-question event, the original password/recovery dialog and the
original AccountGate sign-out/session boundary. Removed the repeated account
privacy paragraph, quiz marketing prompt, recovery reminder and verbose on/off
copy. Terms and Privacy remain reachable. Password controls stay restricted to
the existing username/password account mode.

The loading workspace, loaded workspace and Account page share one
`WorkspaceHeader`. Account navigation adds a browser-history entry; direct links,
reload and Back work through the current query-based navigation. The existing
research subtree stays mounted while Account is open, retaining its local state.
The hidden and visible main regions use distinct IDs so Skip to content targets
the current page. An initial direct Account visit does not require a company
workspace read. Profile setup is optional on this page; explicitly retaking the
questions keeps the original flow. Desktop Account content scrolls independently
below the shared header.

## Verification

- Frontend library suite: **214 passed**.
- `frontend_summary_account.mjs`: passed against the real App, AccountGate,
  Summary and security-dialog components with authored sessions/readings and
  mocked API methods. Checked direct URL/reload, browser Back, retained subtree
  probe, unique visible main ID, initial no-write behaviour, explicit Pro change,
  security dialog focus/Escape, explicit fake recovery-code creation, cancelling
  profile questions and the sign-out boundary. Checked exact Summary count text,
  neutral surfaces and keyboard section links at 1440/768/390/320 px.
- `frontend_header_responsive.mjs`: **68 checks passed**, including 64 resize
  combinations for Beginner/Pro and update availability, with Account and
  configured Telegram controls; no overlap or clipping. No HTTP requests.
- The App-route fixture fulfils its virtual document and local font requests
  locally. All API calls are in-memory fakes; no API or external HTTP request
  was made. No browser errors. Desktop and phone screenshots were inspected in
  `summary-account-screenshots/`.
- Production build and diff checks passed. The existing main-chunk size warning
  remains. Initial fixture assertions used old button labels, a new-browser
  signup default and unserved fonts; these were corrected before the passing run.

The retained-subtree probe establishes that Account navigation does not unmount
that research tree; it is not an independent test of every editor. No backend,
schema, actual preference, password, recovery code, saved research, source/model
call, delivery or running process was changed. Unrelated working-tree edits were
preserved. Nothing was committed or pushed.
