# Workspace panels and company logos — 9 October 2026

The owner requested the right sidebar only in Workspace and company logos in place of initials.

## Result

The current-idea sidebar and its toggle are available for a selected company in Workspace. My ideas, Updates, History and All companies release its space and omit its toggle. Changing tabs preserves the browser's saved open/closed preference, so returning to Workspace restores that choice. Hidden panels retain mounted state, use the existing animation, and remain inert and hidden from assistive technology.

`CompanyAvatar.jsx` supplies the company-list and company-header images. Actual Broadcom, NVIDIA and Fabrinet PNGs were fetched from Financial Modeling Prep's public image route, checked visually and bundled as Vite assets. All three requests returned HTTP 200 without credentials or redirects. Other registered SEC companies request the same HTTPS route when displayed. An initial remains visible until an image loads, and is retained after failure. Fictional recorded companies make no logo request. Images preserve their aspect ratio and send no referrer. [Original URLs and hashes](../../../frontend/src/assets/company-logos/SOURCES.md) record the three unmodified files. The [provider documentation](https://site.financialmodelingprep.com/developer/docs/company-image-api) labels the route legacy; this check does not establish availability for every ticker.

The content security policy permits `https://financialmodelingprep.com` for images. Scripts and application requests remain restricted to the app's origin. No backend catalogue, schema, research, source permission, watch, recipient or model behavior changed.

## Verification

- All 27 frontend checks and the production build pass; edited frontend/browser files pass formatting.
- The focused session/CSRF/owner-boundary integration check passes in a disposable database, including assertions for the image host and existing script/request restrictions. A full backend suite was not repeated for this presentation change.
- `tests/browser_workspace_panels.cjs` verifies the three real bundled logos, header switching, a controlled missing-logo 404, fictional exclusion, sidebar availability, preference restoration and reload. Eight widths from 320 to 1920px across four tabs yield 32 geometry checks without horizontal overflow. Desktop and phone screenshots were inspected.
- `tests/browser_workspace_motion.cjs` passes with its initial tab updated to Workspace. Shared row hover, cross inset, ellipses, intermediate animation sizes, reversal, retained controls, keyboard focus, reduced motion, persistence and ten viewport widths remain verified.
- Both browser journeys intercept coordinated loading, block application writes and abort external requests. Missing-logo and long-label cases are authored browser fixtures; existing saved company data is read from the owner's local app.

The local web server was restarted gracefully while research loading and model activity were idle to apply the image policy. The existing database stayed running and was not initialized or seeded again. All 100 table fingerprints were identical before restart, after restart and after the final browser journey; `.env` stayed exact across restart. The durable ledger still has 359 calls, US$20.0286415 confirmed, US$0.9156025 historical maximum holds and US$9.055756 remaining. No new model call or Telegram dispatch was requested.

Evidence is in `.local/live-tests/company-logos-20261009/`. Preserve the initial restricted image-fetch and PostgreSQL shared-memory failures, the initial unsupported public-asset path, the blocked-logo policy check and the intermediate formatting failure. The final browser run uses bundled `/assets/` images and the active image policy. This verifies the UI and controlled fallback, without a whole-app, provider-coverage or sentiment-quality claim.
