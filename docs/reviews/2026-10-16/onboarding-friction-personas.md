# First-time user friction: 8 personas, then 4 re-tests — 16 October 2026

Ten asked: get as many personas as possible to find what is hard for new users;
too many questions hurt the experience; least friction while users still get what
they need. Each persona drove the real app (Playwright) from the signed-out
landing page to their own goal, on their own device. Logs and screenshots were
kept outside the repo (test workspace).

## Round 1 (before): 8 personas

| Persona | Device | Taps to first value | Would quit at |
|---|---|---|---|
| Aisha, 19, never invested | 390 phone | ~22 | search "northstar" → no results |
| Marcus, 24, robo-adviser | 390 phone | ~21 (100 s) | the quiz, if interrupted |
| Wei Ling, 21, options trader | desktop | 17 (+4 to financials) | quiz Q4 |
| Mr Tan, 58, retiree | 360 phone | ~19 | SGX shares not covered, learnt last |
| Priya, 27, compliance | desktop + phone | ~17 | no privacy contact |
| Jordan, 22, swing trader (skipper) | 390 phone | 5 (skipped) | his ticker has no data |
| Hannah, 20, keyboard + screen reader | desktop | ~85 keys | silent screen changes |
| Daniel, 30, iPad evaluator | 820 tablet | ~24 | Apple page dead end |

**What everyone agreed on**
- Five questions **before any value**; only Q1 (experience) and Q5 (goal) mattered;
  Q2/Q3 overlapped; Q4 (15% fall) felt like a bank suitability form.
- The result **ignored answers** ("checks about once a month" after "most days") and
  told non-investors they were a "Steady builder… ETFs".
- Landing page never said what Fledge is; disabled **Create account** gave no reason;
  username/password rules only appeared as browser bubbles.
- After the quiz: an **Add-a-company dialog popped up** by itself, "Watchlist 0/5" next to
  "My companies 2", unexplained practice companies, Northstar below the fold.
- Search **couldn't find Northstar** although it was already in the list.
- Financials were hidden behind a footnote; Home didn't return to the list.
- Keyboard: focus didn't move on new screens, radios ignored arrow keys, weak focus rings.

## Changes

**Onboarding (from 5 + 1 screens to 1 screen)**
- First sign-in asks **two questions on one screen**: where you are with investing, and
  what you want from Fledge (new option: *Keep up with news*). Continue → straight into
  the app. "Skip, show me the app" is explicit.
- The investor type is now **optional and later**: "What kind of investor are you? Find
  out in 2 questions" on the Home card and in Account (4 if the first two were skipped).
  The two questions: *Which sounds most like you?* (merges holding period and trading
  frequency) and the 15% fall question (with *prefer not to say*).
- New **Just starting out** type for people who haven't invested. Result quotes the
  person's own answers ("You said: …") instead of made-up habits.
- Interest chips removed from onboarding (data minimisation; they only added one line).
- "I trade often" shows an optional *Turn on Pro tools now*; traders get the Pro offer on
  the result. Beginner Summary ends with a one-tap *Turn on Pro tools* button.
- Sticky, full-width 52px main button; errors appear above it and jump to the missing
  question.

**Landing and sign-up**
- Pitch: "Understand the news behind your stocks… US-listed companies. Fledge never tells
  you what to buy." Create account / Sign in tabs (Create by default on a new browser).
- Rules shown under the fields; our own inline errors ("At least 8 characters (you have
  5)"); the button is never silently disabled.
- Shorter consent: "I agree to the Terms of Use and to Fledge using my data as set out in
  the Privacy Notice", plus "We keep only your username, your answers and what you save.
  No NRIC, bank details or real money."

**After sign-in**
- No auto-opened Add-a-company dialog. Slim Home card: next step + **See an example:
  Northstar Software** + investor-type prompt; no watchlist counter. Skippers get the
  same card.
- "Northstar and Aurora are practice companies (not real)…"; Northstar listed first;
  company page badge **Practice company, not real**.
- Search shows your own companies (incl. practice) by name/ticker; no-match text says
  SGX/non-US shares aren't covered yet. Directory status reworded.
- Beginner **Home** always returns to the company list. World tab: one status line for
  Beginners, no blocked AI button.

**Accessibility**
- Focus moves to the new heading after sign-up, each step and back in the app; skip link;
  radio groups are one Tab stop with arrow keys; strong focus rings; selected answers
  show a filled check; Account menu closes on Escape; logo arrow hidden from readers.

**Privacy/Terms wording**: "other users cannot see it" (not "no one"), named countries
(US; DeepSeek in China), current questions listed, AI-summary caveat.

## Round 2 (after): 4 re-tests

| Persona | Taps to first value (before → after) |
|---|---|
| Aisha | ~22 → ~6–8 |
| Mr Tan | ~19 → ~8 |
| Hannah | ~85 keys → ~31 keys; silent transitions 8 → 4 (then fixed further) |
| Wei Ling | 17 → ~8 |

Fixed after round 2: "haven't started" now always gives *Just starting out*; skipper Home
card; error placement; practice badge; SGX wording; Pro offer only for traders; hint and
error wording agree; consent checkbox linked to its error; focus after Continue/Done;
skip link.

## Still open (for the team)
1. **Privacy contact** (`PRIVACY_CONTACT`) and a delete-my-account / request-my-data path.
2. **Singapore (SGX) coverage**: the most common reason a local newcomer would leave.
3. **Plain-English source dialog**: "Source evidence · PROVIDER SNIPPET · Not checked" and
   unexplained terms (margin, breaking out).
4. **One-line "what this company does"** under the name on the Summary (needs data).
5. **Pro mode** feels like another app (menu renames, Summary not default, demo bar) and
   the Pro home card shows "Unavailable" where Financials has figures; Outlook mention
   without an Outlook tab.
6. Companies without data (e.g. a newly added NVDA): "needs attention / AI paused" copy.
