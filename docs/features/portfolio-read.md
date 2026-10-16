# Your list today (portfolio read) — 16 October 2026

Requested by Ten after his lecturer asked what Fledge says about a whole
watchlist (nine AI stocks all down on 14 Oct). Fledge looked at one company at a
time; this reads the **whole list together**.

## Where
Home, above "My companies", when the account's watchlist has **2 or more**
companies. Both Beginner and Pro.

## What it shows
**Lights (built in code, no AI, always available)**
- **Today:** e.g. "All 5 down, −15.5% to −1.8%", "3 up, 2 down (…)", or "A quiet
  day: all within ±0.5%". From each company's latest saved quote.
- **How spread out:** sectors on file, e.g. "Mostly Semiconductors (4 of 5)" or
  "2 sectors on file; 2 not on file". It never calls a list diversified: broad
  sectors can still share one risk.
- **World:** from the account's own World-tab check, e.g. "1 event could hurt 4
  of 5". "Not checked against world news yet" until that check has run.

**Without an explanation:** "How each moved" (bars grouped by sector on file,
news tone across the list) and "World news touching your list".

**Explain my list (optional, one AI request):** the same saved material (prices,
each company's newest rated headlines, recent world headlines and the account's
world links) goes to one bounded request. It returns:
- *What happened*: a headline and up to 3 drivers, **each citing saved headline
  IDs** (shown as source links).
- *Why some moved more*: groups that moved alike with one-sentence reasons and
  bars per company.
- *For your list*: one takeaway about the list as a whole.

Checks in code: unknown source IDs, companies placed in two groups and
advice-like wording ("consider buying", "opportunity", "will rebound", "price
target"…) are dropped and counted; describing a sell-off is allowed. The same
list and material reuse the saved answer (no second charge). A changed list
hides the old explanation. Private per account (`portfolio_reads`, RLS,
migration 055). Uses the existing model ledger and live-AI switch, so it only
runs where Fledge's AI runs.

## API
- `GET /api/v1/portfolio` → lights, groups, companies, saved explanation.
- `POST /api/v1/portfolio/explain` → runs the AI read (422 when AI is off, the
  list has fewer than 2 companies, or no prices are saved).

## Not included (yet)
- Importing a list from a screenshot (the model ledger only allows text).
- Lists over the 5-company watchlist limit.
- Showing the read only on "big move" days; it shows whenever the list has 2+.
