# Ten beginner personas, in pairs — 15 October 2026

Owner (Ten) noticed the Signals Summary was "too summarised" ("Mostly
positive?", "Mixed?") only when presenting it to a friend. To reproduce that,
ten simulated people tested in five presenter → friend pairs on a phone, the
friend asking "what does that mean?" whenever the screen didn't say. Data:
fictional Northstar (NSTR) with a harness AI news/social reading, a price and AI
world-news links (no live keys).

| Pair | Presenter → friend |
|---|---|
| 1 | Kai, 20, poly student → his mum, 52, hawker, English second language, never invested |
| 2 | Priya, 22, finance student → Daniel, 23, NSF, skeptical, skims |
| 3 | Wei Jie, 25, ETF investor → Sarah, 26, impulsive meme-stock buyer |
| 4 | Aisha, 19, red–green colour-blind, phone only → Marcus, 21, crypto power user |
| 5 | Linh, 21, international student, English second language → Uncle Tan, 60, dividend investor, distrusts AI |

## What every pair found (fixed)

Before this round the lights already moved from mood words to counts ("2
good, 2 bad, 2 neutral") with the actual headlines grouped under them.

- **World light only counted the risk.** Red "One risk to watch" over a section
  with 1 could-help, 1 either-way, 1 could-hurt read as "all bad" (pairs 1–5).
  → Counts like the other lights ("1 could help, 1 could hurt, 1 either way"),
  red only when everything linked could hurt; the alert line names the risk.
- **Counts didn't match lists.** "1 mixed" post counted but not shown (1–5).
  → Mixed group shown.
- **Who decided "good"/"bad"?** AI rating was only disclosed inside a pop-up
  (1, 5). → Key under the lights: "Sorted by AI…; tap any item to check it."
- **Colour-only meaning** (4, 1). → ▲ ▼ ◆ shapes, a written key and full
  aria-labels on each light.
- **"Before you decide anything" read as "decide to buy"** (3). → "Read both
  sides below." The not-buy/sell line moved from the footer to under the lights.
- **Price vs news** ("big bank deal, so why is it down?") (1, 3). → "Prices move
  for many reasons. The news below may not explain today's move."; "since the
  last close" instead of "in the last session".
- **Hype posts looked like green signals** (3). → Posts labelled "(opinions)"
  with neutral dots; majority wording ("Most posts are upbeat, but some are
  worried. Online posts are opinions, not facts.").
- **"Just facts"** implied good/bad items aren't facts (1, 2, 5). → "Neutral,
  neither good nor bad".
- **Tapping a light hid the heading under the sticky bar** (1, 4). → scroll
  margin.
- **World items on Summary had no source or date** (5). → publisher · day.
- **World tab**: "Headlines checked" next to "not connected" (1) → one clear
  status; "My companies 3" counted headlines (1, 3, 4) → "About my companies";
  disabled check button with no reason (1) → reason shown; cut-off quote (1, 3)
  → removed; footer reworded.
- **Your view**: blank answer saved as "saved" (4) → requires a sentence;
  question assumed liking (5) → "What do I think about X, and why?"; alerts
  message pointed to a switch the practice company doesn't have → corrected.
- **Beginner News & discussion promised "every news article" but showed 2025
  company reports** for the practice company (1–5) → intro now says it shows the
  practice company's own reports, not today's news.
- Company dialog buttons under 44 px on phones → enlarged.

Re-test (pairs 1 and 3): 7 of 12 and 5 of 9 original findings fixed, the rest
partly; Kai: "Ma read the key herself and stopped panicking at the colours";
Sarah: "Less shouty, I get the diamonds."

## Still open — for the team (outside the Beginner Summary)

1. **Demo story progress is shared by all accounts** (pairs 2–5): a new account
   opens at "Source outage" because someone else pressed "Next development".
   Stage labels ("Q2 baseline", "Source outage", "Revenue restatement") need a
   one-line plain explanation, and the Summary doesn't say what changed.
2. **News & discussion has no plain list of today's news for live companies in
   Beginner** — the evidence cards ("Supports/Challenges", "display rounded",
   "chosen condition") are research-grade; "Challenges" was attached to a
   revenue *upgrade* (pair 3).
3. **Source dialog small print**: "PROVIDER SNIPPET", "First available here Not
   checked", social byline missing platform/author, the parent-context
   paragraph (pairs 1, 5).
4. **Updates/Data & sources jargon** in Beginner ("monitored conditions",
   "Quiet checks remain in History", 2025-only source list) (4, 5).
5. **Text doesn't scale with larger font settings** (fixed px sizes) (5).
6. **Removing a practice company** leaves no way to find it again in search
   (4).
7. **First run** opens "Add a company" automatically, which showed a listings
   error without data keys (1, 2).
8. **Dividends** (yield, payout) appear nowhere; dividend investors expect them
   (5).
9. Pro mode's Summary is identical to Beginner's; Pro financials mention SEC
   ratios / an Outlook tab that aren't shown for the practice company (2).

Transcripts and screenshots: `/home/claude/w/persona/pairs/pair1…5/` in the test
environment (not committed).
