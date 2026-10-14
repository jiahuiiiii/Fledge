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

## The Summary page

One column of plain cards, no charts:

1. **Share price**: last saved price and "up/down x% in the last session".
   The move is not explained by a headline.
2. **The basics**: the existing plain sentences about revenue growth,
   management guidance and cash versus borrowing, when saved.
3. **What the news says**: the saved AI tone for company news in words
   ("Mostly positive", "Mixed", "Not enough to tell yet") and the five newest
   headlines with their own tone; each opens the original source.
4. **What people are saying online**: tone per platform (Reddit, Hacker News,
   X) and the three newest posts.
5. **World news that may matter**: World-tab headlines that name the company
   or that the watchlist check linked to it, with the plain reason; otherwise
   the two newest rate, conflict or trade headlines as the big picture.
6. **Your view**: the saved idea, or a prompt to write one.

Everything rewords saved readings; nothing new is calculated or recommended,
and the page says it is not advice to buy or sell.

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
