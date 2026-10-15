# Beginner and Pro modes

Added 14 October 2026 (Ten). Owner request: the app has too many charts for
real beginners; give them a simple summary page built from what Ten himself
trades on: company news, world news and social sentiment.

## What changes

A top-bar switch, **Beginner | Pro**, replaces "Explain it to me | Show me the
data" and uses the same saved setting (`detail_mode`: `explain` = Beginner,
`data` = Pro). Accounts that answered the first-login questions save it on the
server; accounts that skipped them keep it in this browser (default Pro).

- **Beginner**: a company shows only **Summary** and **News & discussion**.
  Overview, Financials, Outlook and Compare & value are hidden, and "?" term
  help and reading notes open by default.
- **Pro**: every tab, with **Summary** added first.

## The Summary page ("Signals", chosen 15 October 2026)

Option B of the four designs the team compared. One column, no charts:

1. **Price**: last saved price and "up/down x% in the last session". The move
   is not explained by a headline.
2. **Three lights**, readable in seconds, each a tap target that jumps to its
   reason:
   - **News**: the saved AI news tone in words ("Mostly positive", "Mixed",
     "Not enough to tell yet"); "Not read yet" when only unread updates exist.
   - **People online**: the combined tone across Reddit, Hacker News and X
     ("Mostly upbeat", "Mostly worried", "Split").
   - **World**: from the World tab's watchlist check: "One risk to watch"
     (red) if any linked headline could hurt, else "Could help" or "Could go
     either way"; "Nothing linked" otherwise.
   When any light is red, a line under them says "Something here could hurt.
   Worth reading the reasons before you decide anything."
3. **Why these lights?**: one plain line per light, e.g. "4 of 6 recent
   articles sound upbeat. Latest: …", each platform's tone, and the world
   link's reason with its headline; plus "possibilities, not predictions or
   tips".
4. **What happened**: newest company news, posts and linked world headlines
   merged by date (Today / Yesterday / weekday), each opening its source;
   links to all news & posts and to World news.
5. **Your view**: the saved view, or a prompt to write one.

Lights describe what is being said, not whether to buy or sell; nothing new is
calculated or recommended. Helpers: `newsLight`, `socialLight`, `worldLight`,
`whatHappened` in `lib/beginnerSummary.js` (tested).

## Code

`frontend/src/components/BeginnerSummary.jsx`, `lib/beginnerSummary.js`
(+ tests), `ResearchNavigation.jsx` (`researchTabs`), `DetailModeToggle.jsx`,
`lib/profile.js` (local mode for accounts without answers), `App.jsx`.

## Phone layout fixes — 14 October 2026

Checked every main view at 390 and 360 px wide (sign-in, first-login
questions, home, company Summary/Overview/Financials/News, World, Updates, My
ideas, account menu). `frontend/src/styles/mobile.css`, loaded last:

- The all-companies home and World view no longer show the last-opened
  company's header on phones (World also hides the demo bar).
- The account menu stays inside the screen.
- Research tabs scroll sideways with a fade showing more tabs exist.
- Small controls (Beginner/Pro, demo bar, "Read source", source links, World
  filters) are at least 44 px tall on phones and touch screens.

## After the beginner persona test — 14 October 2026

See [the persona test](../reviews/2026-10-14/beginner-persona.md). Beginner is
now the default for everyone except "Active" traders; Summary opens with an
**In short** line; the view form, home cards and News & discussion intro use
plain words in Beginner; new username accounts see only their own companies
plus the fictional practice ones.

## Beginner first, Pro in the account menu — 15 October 2026

Owner: still too many things to click. Everyone now starts in **Beginner**
(including "Active" traders); the top-bar Beginner | Pro switch is gone and
**Pro tools** is a switch inside the **Account** menu (a small **Settings** menu
when Fledge runs without accounts). In Beginner:

- Top menu: **Home · World · My views** (Updates appears only when something is
  waiting); no Telegram button.
- Company page: just the Summary; no Ask a question / Data & sources buttons,
  research tabs, section heading or practice-story bar. "All news & posts →"
  opens the news list with "← Back to summary".
- Home: "My companies", one plain line, no search box or reload button.
