# Beginner persona test — 14 October 2026

A test agent role-played **Kai, 20**, a polytechnic student with S$500 in a
brokerage app who has never read a financial statement, using a local test
server at phone size (390×844) plus one desktop pass. Test data: fictional
NSTR/AURQ, sample world headlines, and a stand-in for the paid AI watchlist
check (no live keys). Three rounds; fixes shipped between rounds.

| Score (1–5) | Round 1 | Round 2 | Round 3 |
|---|---|---|---|
| First impression | 3 | 4 | 4 |
| Clarity of what to do | 2 | 3 | 4 |
| Summary page usefulness | 2 | 3 | 4 |
| World news usefulness | 4 | 4 | 4 |
| Jargon level (5 = none) | 2 | 2 | 3 |
| Mobile comfort | 3 | 4 | 4 |
| Would open again tomorrow | 2 | 3 | 3.5 |

Best-liked: the "World news that may matter" card ("Could hurt: tariffs make
imported parts more expensive").

## Fixed from the test

- "A few stocks" put Kai in Pro on a page of "Not available" figures →
  Beginner is now the default for everyone except "Active" traders.
- New username accounts saw other accounts' companies and lost the practice
  companies after adding one → own list plus fictional practice companies.
- "Your view" had no button on practice companies; the form used research
  wording and a pre-filled research question → plain Beginner form ("Your
  view", "Your question"/"Your answer", "Get alerts (optional)", "Save my
  view"); the saved message is shown and says alerts are off and where to
  turn them on.
- Summary news card was empty without an AI reading → shows saved company
  updates; "Not checked yet" → "Not read yet".
- No "should I worry?" answer → an **In short** line restating the cards in
  plain sentences, ending with "Worth reading the headlines below before you
  decide anything" when news is negative or a world headline could hurt.
- "Could help/hurt" blocks now say "A possibility to think about, not a
  prediction or a tip."; World uses "could go either way" everywhere; setup
  instructions (environment variable names) no longer shown to users.
- Home cards in Beginner show price and news only; News & discussion starts
  with a plain paragraph; "Manage my companies", "Turn on news alerts",
  "Create your Fledge account"; scroll to top when switching companies;
  "+ Add" (not "Open") for companies other accounts added; World filters are
  one swipeable row on phones.

## Still open (for the team)

- News & discussion body text is still research-grade ("2025-Q3 (display
  rounded)", "Margin expansion supports a separate part of the idea",
  "conditions or assessments"). Needs a Beginner wording layer.
- The **In short** line can only say "not yet read by AI" until a news reading
  exists; a real "what does this mean" sentence needs the AI reading.
- Demo-story progress ("Next development") is shared by all accounts.
- Onboarding progress resets on reload.
