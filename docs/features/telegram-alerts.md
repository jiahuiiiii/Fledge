# Telegram alerts

Thesis now adapts the connect/disconnect and structured notification flow from our Kestrel project. A dedicated Telegram bot forwards **newly published** company, saved-idea and monitored-condition alerts to the private chat you connect. It does not create a new signal model, turn on watches, or make extra AI calls.

## Connect your chat

1. Open [BotFather](https://t.me/BotFather), send `/newbot`, and follow its prompts. Use a new bot for Thesis so Kestrel can keep using its own bot.
2. Put the token in `TELEGRAM_BOT_TOKEN=` in this project's private `.env`. Do not paste it into chat or commit the file. Settings are reread; restarting Thesis is unnecessary.
3. Open **Telegram** in the top bar, then **Connect Telegram**. Open the resulting link and tap **Start** in Telegram.
4. Return to Thesis and choose **Check connection**. Check that the displayed private chat is yours.
5. Choose **Send a test message**. Its status should become **Delivered**, and the connection test should appear in your chat.
6. Check **Send future alerts to this chat**. Company research watches and saved conditions keep their own settings. Set them up in the relevant company workspace.

The link expires after ten minutes and is single use. The app accepts private chats only. Creating a new link invalidates the previous one. Connecting does not itself enable delivery or send a message; the test button and delivery switch are separate explicit actions.

## What messages contain

- Ticker and alert category.
- What changed and the existing alert's reason or source excerpt.
- Separate news/social sample changes where applicable. Social discussion is not presented as market consensus or verified company news.
- The relevant saved question for idea/condition alerts, bounded to a short excerpt.
- Source links where available, sample/alert timestamps, and instructions to open the company's Updates on this Mac.

There is no buy/sell action, price prediction, new LLM summary or live price-movement alarm. Recorded demo alerts are explicitly labelled fictional. Localhost app links are not placed in Telegram because they would point at the receiving phone's own device; public original-source links remain usable.

## Timing and delivery states

Thesis and the Mac must remain running. Source watches keep their own polling schedules. The Telegram worker checks its queue every five seconds, sending at most one message per five seconds. Browser tabs may be closed while the local server continues running.

Enabling or re-enabling delivery starts with future publications; old Updates are not sent as a backlog. A restart catches up only on unsent alerts published while delivery was enabled and within the preceding 24 hours. Older alerts remain in Updates. Existing alerts are unique by owner, kind and original record ID.

**Delivered** requires Telegram's successful response with a message ID and the intended chat ID. **Delivery unconfirmed** means a connection or app interruption left the outcome unknown; check the chat. It is not resent automatically. This prevents accidental duplicates but is not a guarantee of exactly-once delivery. Telegram-confirmed rate limits may retry after the supplied delay, with a maximum of three attempts. Rejected delivery pauses the channel. Fix the connection, then explicitly re-enable it; old failed messages are not replayed.

Pausing/disconnecting cancels queued messages. A send already in progress may finish before the pause returns. Disconnecting does not delete previously delivered Telegram messages or stop research watches.

## Privacy, access and persistence

Alert content and a short saved-question excerpt leave the Mac for the explicitly linked Telegram private chat. Tokens stay only in `.env`; the connection link's secret is stored as a hash with an expiry. Chat identity and outbox metadata are owner-scoped with forced database row security; the shared source role cannot read them. The outbox stores references/status, not copied message bodies. Current source permissions and saved-idea revision are checked before dispatch. Previously delivered messages cannot be recalled by later source withdrawal.

The original Kestrel implementation can swallow a send failure and still mark its alert sent. Thesis intentionally replaces that behavior with durable intent, verified acknowledgements, failure states and conservative recovery. It uses official Bot API polling for explicit chat connection, not Kestrel's public webhook or hardcoded bot username. It never deletes an existing bot webhook; a bot already serving another app must be kept separate.

## Verification

`tests/test_telegram.py` exercises the real database and actual alert publication paths with mocked Telegram/AI transport. `tests/run_telegram_browser.py` uses a disposable workspace and mocked channel responses for the connection screen. No tests send to a real chat or consume OpenAI credits. Actual Telegram delivery is only established after a configured bot and its owner complete the live connection/test above.

The 8 October layout follow-up puts the three pairing actions in equal-width columns
with matching height, type and padding, then stacks them below 600px. Setup text
and actions use consistent gaps. The frontend's 27 checks/build and isolated
Telegram journey pass; pairing screenshots cover 320–1920px. The browser runner
loads the existing external-network guard only into its disposable server, never
the owner's app. This is a presentation change, not a change to pairing or delivery.

Protocol references: [Bot API: polling and webhook behavior](https://core.telegram.org/bots/api#getupdates), [sendMessage and acknowledgement contract](https://core.telegram.org/bots/api#sendmessage), [private-chat connection links](https://core.telegram.org/bots/features#deep-linking), and [Telegram message pacing](https://core.telegram.org/bots/faq#my-bot-is-hitting-limits-how-do-i-avoid-this). Reviewed 5 October 2026.
