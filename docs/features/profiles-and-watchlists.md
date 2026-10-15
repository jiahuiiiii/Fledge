# Username sign-in, first-login questions, tailored home and five-company watchlist

Added 11–12 October 2026 (Ten: login and backend).

## Username and password sign-in (test product)

Set `THESIS_AUTH_MODE=password` in `.env`. Sign-up always creates a new,
separate account; it never grants the installation owner's research. To sign
in to that research, create the owner login from the server's own shell with
`python -m thesis.password_auth owner <username>` (it asks for the password
twice and refuses if the owner already has a login). The sign-in page then
offers **Create account** / **Sign in** with a username and password; no email
or Supabase is needed. Passwords are stored only as salted scrypt hashes;
sessions are 7-day HTTP-only cookies whose hash is kept server-side; five wrong
passwords for a username (or 50 installation-wide) pause attempts for 15
minutes. Each attempt is counted under a row lock before the password is
checked, so simultaneous attempts cannot get past the limit. There is no password reset yet. Without the setting, the email-link
sign-in and local demo behave exactly as before.
Code: `migrations/051_password_accounts.sql`, `thesis/password_auth.py`, small
hooks in `thesis/auth.py` and `thesis/app.py`, `AccountGate.jsx`;
tests: `tests/test_password_auth.py`.

## What users see

1. After signing in for the first time, four questions: experience (just
   starting / ETFs or funds / a few stocks / active), interests (sectors, or
   "not sure yet"), usual holding period and what they want help with first
   (understand a company / check an idea / watch what I own). "Skip for now"
   asks again next sign-in.
2. Then the add-company search opens so they can start their watchlist.
3. The home page uses their answers: headline and next step follow their goal,
   their interests are repeated back as search hints, the starter questions
   are reordered by goal, and the view starts in **Beginner** mode for everyone but
   "Active" traders, who start in **Pro**. A top-bar switch changes it at any time
   (see [Beginner and Pro modes](beginner-mode.md)).
4. Each account follows at most **five companies**. Once an account has a
   watchlist, the sidebar shows only those companies. A sixth company can still
   be opened and read; it is just not added, and a notice explains the limit.
   Active news/social watches are also capped at five.

Fledge never picks, ranks or recommends companies from these answers.

## Backend

| Piece | Where |
| --- | --- |
| Tables `investor_profiles`, `watchlist_companies` (row-level security per account; the 5-company limit is a database trigger) | `migrations/050_profiles_and_watchlists.sql` |
| Answers and explain/data preference | `thesis/profile.py` |
| Watchlist add/remove/list | `thesis/watchlist.py` |
| Tailored home content | `thesis/home.py` |
| Watch cap | `thesis/monitoring/news_watch.py` (`configure`) |
| `watchlisted` flag on each company | `thesis/service.py` (`catalogue`) |

API: `GET/PUT /api/v1/profile`, `PUT /api/v1/profile/detail-mode`,
`GET /api/v1/home`, `GET/POST /api/v1/watchlist`,
`DELETE /api/v1/watchlist/{instrument_id}`.

## Frontend wiring (minimal; Jiahui to restyle)

`Onboarding.jsx`, `DetailModeToggle.jsx`, `lib/profile.js`, and small changes
in `App.jsx`, `EmptyWorkspace.jsx`, `CompanionGuide.jsx` and `api/client.js`.
The explain/data preference is exposed as `useProfile()` and as
`data-detail-mode` on the page root; individual panels do not yet change
their content by mode.

## Open points

- The questions appear in a dialog after sign-in. This differs from the
  companion journey's "no compulsory modal on page load"; agree the final
  form together.
- Existing accounts with no watchlist keep the old sidebar until they add or
  remove a company.
- Neutral sector lists ("largest companies in technology") need sector data
  the company directory does not have yet.

## Verification

`tests/test_profiles_watchlists.py` (6 cases: validation, privacy between
accounts, the five-company limit incl. re-adding, watch cap, home content, API)
and `src/lib/profile.test.js`. Backend run on PostgreSQL 16 in a disposable
cluster, not the project's PostgreSQL 18.
