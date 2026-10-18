# Split-window header — 17 October 2026

The owner reported clipping when the app occupied half a Mac screen. At a
756px CSS viewport (1,512 physical pixels at 2×), the existing single-row header
shrank the navigation, wrapped “My ideas” and pushed Account outside the window.
The two-row layout previously started only below 600px.

New `frontend/src/styles/header.css`, imported after the existing styles in
`main.jsx`, uses the existing 980px breakpoint. Logo and account tools share the
first row; navigation has its own 44px row. Navigation labels stay on one line,
and the existing phone spacing and wide desktop layout remain. The DOM, account
controls, navigation actions, colours and fonts are unchanged. The user's
uncommitted `frontend/src/styles/app.css` is byte-for-byte preserved.

The browser test extracts both actual header JSX templates from `App.jsx` and
exercises loaded/loading and Beginner/Pro states. It reproduces the original
clipping before applying the fix, then checks 64 resize cases over 320–1440px,
including both sides of 600/980px and repeated narrow/wide transitions. All
controls must remain inside the header/window without overlap; navigation stays
on one line. Four additional checks cover Account containment/Escape/focus,
navigation selection and Telegram dialog access. The test also runs with the
currently installed stylesheet assets, inlining saved fonts; browser HTTP is
blocked. No app or test app is started.

Source and installed-CSS runs each pass 68 checks. Frontend 202 unit tests,
temporary production build, scoped formatting and diff checks pass. Screenshots
at 756/390/320px were inspected. The existing build-size warning is retained.
No backend behaviour changes, source refreshes or paid calls occur.

Installed 17 October at 16:12:38 Singapore time as one content-hashed stylesheet
and an atomic index update. All existing assets and script references remain
exact; the app process is unchanged. HTTP serves the new index and identical
tested CSS. Backup: `.local/backups/header-responsive-20261017T081238Z/`.
Evidence: `.local/live-tests/header-responsive-20261017/`.

No app/DB restart, environment edit, database change or account-setting action.
Prepared phase 5 code and migrations are not installed by this update. Refresh
the page to load the new stylesheet. Paid-test cost: US$0.
