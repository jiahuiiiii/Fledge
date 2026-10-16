# Testing "Your list today" (for Jia Hui)

## Automatic (any machine, no AI cost)
```sh
.venv/bin/python -m pytest -q tests/test_portfolio.py
npm test --prefix frontend
```
Covers move/spread/world wording, sector groups, cited-only explanations, the
advice guard, answer reuse, account privacy and the API.

## On your machine (real AI)
1. Pull, start Fledge (migration 055 applies itself), sign in.
2. Add 4–5 real companies that moved together recently (e.g. NVDA, AVGO, ORCL,
   MSFT, AMD) and press **Update** on each so prices and news are saved.
3. World tab → Refresh → **Check against my watchlist**.
4. Home → **Your list today** should appear. Check:
   - Today light matches the % moves on each company page.
   - World light matches the World tab links.
5. Press **Explain my list**. Check:
   - Every "What happened" line has a source link that opens the right article.
   - Groups make sense and each company appears once.
   - Nothing reads like advice (buy/sell/hold, "opportunity", price calls).
   - Press it again: no new charge in the cost log (answer reused).
6. Remove one company → the explanation disappears until you explain again.
7. Phone width (390px) and desktop: nothing overflows; bars are readable.

Each explanation is one AI call, logged like the World-tab check.
