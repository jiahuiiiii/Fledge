# World news

Added 13 October 2026 (Ten). Owner request: show world events (central-bank
rate decisions, wars and sanctions, tariffs, oil) and which watchlist companies
they might affect.

## What users see

A **World** tab beside Updates lists Finnhub's general market headlines from the
last three days, newest first. Each headline shows its publisher, time (SGT), a
short summary and a link to the original article.

- **Theme tags** come from code-owned keyword rules, not AI: Rates & central
  banks, Inflation & economy, Geopolitics & conflict, Trade & tariffs, Energy &
  oil, Regulation & policy. Filter chips show the count for each theme.
- **Names your company**: a headline that names a watchlist company (its ticker,
  case-sensitive, or its core name, e.g. "Apple") is marked, and the
  **My companies** filter shows those headlines plus any with AI-suggested effects.
- **Check against my watchlist** (optional, paid AI): the 15 newest headlines and
  the account's watchlist (up to 5) go to GPT-5.4 mini in one bounded request.
  It returns, per headline, only companies with a concrete channel (rates and
  valuation, regional demand, supply chains, costs, tariffs, sanctions,
  regulation, currency), an effect (could help / could hurt / mixed or unclear),
  one plain sentence and an exact quote. Links with unknown IDs, repeats or a
  quote not found in that headline's own text are dropped and counted. The same
  headlines and watchlist reuse the saved answer instead of paying again.
  It never recommends trades or predicts prices.

## Sources and limits

- Finnhub `GET /news?category=general` with the existing key, request clock,
  size limit and text/link checks. Refreshes are at least 10 minutes apart; the
  page refreshes automatically when headlines are over 30 minutes old. A failed
  refresh keeps earlier headlines and shows the error.
- Coverage is Finnhub's market-news selection (Reuters, CNBC, Bloomberg and
  others), not every world event. Keyword tags can miss or mis-tag headlines.
- The AI check uses the existing ledger and allowance and the existing live-model
  switches (`THESIS_LIVE_MODELS_ENABLED`, key, approved installation path). When
  live models are unavailable the button is disabled with the reason.

## Code

`migrations/052_world_news.sql` (shared `world_news_articles`/`world_news_state`,
private row-level-secured `world_news_checks`), `thesis/research/world_news.py`,
routes `GET /api/v1/world-news`, `POST /api/v1/world-news/refresh`,
`POST /api/v1/world-news/check`, `frontend/src/components/WorldNews.jsx`,
`frontend/src/lib/worldNews.js`. Tests: `tests/test_world_news.py`,
`frontend/src/lib/worldNews.test.js`.


## Shared presentation — 25 October 2026

World news uses the shared page header, action buttons, filter group, story cards,
metadata, badges, inset effect cards, empty states and disclosure. Theme and
company filters retain their original counts and meaning. Original text and
links remain distinct from labelled AI possibilities. Existing refresh and
watchlist-check policies are unchanged. See [UI verification](../reviews/2026-10-25/shared-reading-pages.md).
