# Investor-type quiz and Terms/PDPA consent — 15 October 2026

> **Updated 16 October 2026** after 12 persona runs (see
> `docs/reviews/2026-10-16/onboarding-friction-personas.md`): first sign-in now asks
> **2 questions on one screen** (experience, goal); the investor type is optional and
> later (2 more questions from Home or Account), adds **Just starting out**, and quotes
> the person's answers. Holding period is derived from the style answer (migration 054
> adds the `news` goal). Interests are no longer asked. The table below is the original
> 15 October design.

Requested by Ten after feedback from a real user:

> When logging in, answer 5 questions to identify which type of investor you
> are (slow investor, swing trader…), so someone who wants to invest knows what
> type of investor they are.

> Make the user accept terms and conditions when they register. Managing
> personal data (PDPA).

## Investor-type quiz

First sign-in now asks **five** questions (was four), then shows a result card.

| # | Question | Stored as |
|---|----------|-----------|
| 1 | Where are you with investing? | `experience` (unchanged) |
| 2 | When you buy, how long do you plan to keep it? | `horizon` (unchanged values) |
| 3 | How often do you (or would you) buy or sell? | `trade_frequency` (new) |
| 4 | A stock you own falls 15% in one week. What do you do first? | `drop_reaction` (new) |
| 5 | What do you want Fledge to help with first? | `goal` (unchanged) |

Interests moved from a required question to an optional chip list on the
result screen. Older profiles (four answers) still work; the two new columns
are nullable (migration 053).

**Types** (`thesis/investor_type.py`, deterministic points, no AI):
Long-term investor · Steady builder · Swing trader · Active trader. Ties go to
the calmer style. Copy lives in `frontend/src/lib/investorTypes.js`: what the
type means, usual holding period and checking rhythm, a "watch out for" line
and how Fledge helps. The result says it describes how the person said they
invest and is not advice. The type is never used to choose, rank or recommend
investments.

**Account menu** shows "Your investor type" and **Retake the quiz**. Retaking
prefills the previous answers and keeps the Beginner/Pro choice.

## Terms of Use, Privacy Notice and consent

- `/terms` and `/privacy` are readable without signing in
  (`frontend/src/components/LegalPage.jsx`), plain English.
- **Sign-up** needs an unticked-by-default checkbox ("I have read and agree to
  the Terms of Use and the Privacy Notice, and I consent…"). The server rejects
  `/api/v1/auth/register` without `accept_terms: true` and the current
  `terms_version`, so no account can be created without consent.
- Consent is recorded in `terms_acceptances` (account, version, time; RLS per
  account), in the same transaction that creates the account.
- **Existing accounts** (and everyone after a version bump) see a one-time
  "Before you continue" screen after sign-in: three-line summary, the same
  checkbox, Agree and continue, or sign out. `POST /api/v1/terms/accept`.
- Version: `thesis/terms.py` `VERSION` and `frontend/src/lib/terms.js`
  `TERMS_VERSION` must match. Bump both for material changes.
- Footer links to Terms and Privacy in the Account menu.

PDPA areas the Privacy Notice covers: what is collected, purposes, consent and
withdrawal, disclosure to AI/market-data/Telegram services and overseas
transfer, protection, retention (delete within 30 days of request), access and
correction (reply within 30 days), breach notification, and a Data Protection
Officer contact.

### Before launch (open items for the team)

1. **Fill in `PRIVACY_CONTACT`** in `frontend/src/lib/terms.js` (the DPO
   business contact the PDPA requires). Until then the pages say "contact
   details coming soon".
2. **Get the wording checked** by someone qualified (school legal clinic,
   lecturer or lawyer). These texts are a plain-English draft, not legal advice.
3. There is no self-service **data export or account deletion** yet; requests
   are handled by the team by email as the notice says. Consider adding both.
4. The terms gate is enforced in the app for existing accounts; the API itself
   only enforces consent at sign-up.
5. Email-link sign-in (managed mode) also shows the gate after the first
   sign-in, since that flow creates accounts on the callback.
