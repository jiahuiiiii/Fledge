# Phase 75 — private Telegram alert delivery

The user explicitly requested the Kestrel Telegram integration as an additional delivery channel for important developments. Thesis now connects an owner-selected private chat and forwards existing published company, saved-idea and monitored-condition alerts. This supersedes the historical in-app-only boundary for Telegram; it does not enable watches or add price predictions.

The team's Kestrel connect/disconnect and structured-message workflow is reused as the product pattern. The implementation uses the official Bot API without adding a dependency, a public webhook or hosting. Unlike Kestrel's swallowed-error send path, delivery is acknowledged only after a valid Telegram message/chat response. Details and setup are in [the channel contract](../../features/telegram-alerts.md).

## Verification

- Broad isolated suite: **1,161 passed, 29 skipped**, including retained real SEC responses and 37 initial Telegram cases. The skips require other opt-in retained corpora. No fresh source/model requests occurred.
- Final focused checks: **40 Telegram cases pass**, adding three cases after the broad run. A 61-case combined Telegram/review/fresh-workspace run also passes; these counts overlap, not additional independent cases.
- Frontend: existing **25 tests pass**, final production build and changed-file formatting checks pass.
- Browser: mocked channel setup, expiring-link UI, private-chat confirmation, explicit opt-in, connection test, ambiguous delivery feedback, pause/disconnect, keyboard opening/Escape, empty-workspace availability and 320/390/1440/1920px layouts pass.
- The real database and real publication paths for all three alert kinds are exercised with mocked Telegram and AI. Existing ledger values stay unchanged during delivery. Duplicate work, concurrent workers, stop-vs-send fencing, intent recovery, 429 cooldown/attempt bound, rejected/unknown responses, source withdrawal, changed idea revisions, malformed records, old queues, HTML escaping/length, RLS and endpoint opt-in protections are covered.

Initial verification exposed two incorrect test assumptions (a fictional story update was assumed to change a numeric figure; a helper used the wrong save signature). Those test calls were corrected. The first browser script selected no company and waited for a deliberately hidden company header. A subsequent browser check exposed a real checkbox feedback delay: the control waited for a server response before updating. The final version updates its check immediately, restores state on failure and excludes stale polling responses during mutations. The phone header was adjusted to keep Telegram beside the brand rather than adding a third row.

There is **no live Telegram receipt yet**. A real bot token and the owner's private chat must be connected in the app, then the test message verified in Telegram. No messages were sent to Kestrel recipients, and no Telegram credentials were copied from that project. The blank `.env` field was added without changing other credentials.

## Five perspectives

One agent applied these five lenses; this is not independent review.

- Product: notifications extend the existing research loop, with the reason and sources available outside the app. The feature does not supply a new trading signal or improve the model's semantic accuracy.
- UX: setup is reachable before the first company is added. Pairing, delivery opt-in and test sending are separate. Delivery states describe success, known rejection and uncertainty accurately; no immediate backlog is sent.
- Data: content is rehydrated under current source access and current private-idea revision. Social sample changes remain distinct from market sentiment. Previously delivered messages cannot be recalled by later access changes.
- Engineering: a forced owner-scoped outbox, immutable alert identity and database lock protect parallel sends and pause/disconnect. Intent commits before HTTP dispatch. Telegram-confirmed throttling has bounded retries; ambiguous sends do not retry. There is no exactly-once network guarantee.
- Evaluation: local and mocked tests cover reliability and presentation, not live delivery, alert usefulness or market-wide sentiment quality. Prior phase 74 semantic failures remain open. Local polling requires an awake Mac and running server.

## Installation and accounting

Migration 036 adds empty channel settings and delivery tables. Installation evidence is retained under `.local/live-tests/telegram-delivery-phase75/installation.json`, with the source/database backup path recorded there. Research remains empty for Wednesday; fixture bootstrap stays off. Model accounting is preserved exactly. No additional API credits are spent by this phase.

The implementation uses no new model prompt, profile or allowance. The previous checkpoint remains US$16.793227 confirmed plus US$0.60249 retained historical maxima under the cumulative US$30 cap. This is not a new allowance or reconciliation of those historical uncertainties.
