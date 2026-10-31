# Fledge

**A research companion for newer investors.** Fledge helps you understand a company, write down why you believe what you believe, and get told when the evidence changes.

It does not tell you what to buy or sell, and it does not trade for you. Its job is to make your own thinking better informed and easier to revisit.

*Fledge was previously named Thesis. The repository and some internal names still use "Thesis".*

---

## The problem

Someone who starts investing faces three problems:

1. **Too much noise.** News, Reddit threads, analyst notes and filings all say different things, and it's hard to tell what matters for the company you own.
2. **No memory.** You form an opinion, then forget why. When the price moves, you can't tell whether the facts changed or you just got nervous.
3. **Alerts that cry wolf.** Most price apps ping you for every wobble, so you learn to ignore them.

## What Fledge does

**Start with a question, not a ticker.** Pick a company and ask what you actually want to know: *How does it make money? Is it growing? What could go wrong? What do analysts expect?* Each question takes you to the relevant evidence.

**Understand the company in plain language.**
- **Overview:** price chart, key signals and short explanations of the business.
- **News & discussion:** headlines plus what investors are saying on Reddit and Hacker News. AI reads these and shows the overall tone, with the original quotes beside it so you can check the reading yourself.
- **Financials:** revenue, profit and cash flow taken from the company's official SEC filings. Management guidance and analyst forecasts are kept separate and labelled.
- **Compare & value:** how the company stacks up against its peers, with clearly labelled "what if" valuation scenarios.

**Write down your reasoning.** Save a short note: *I think… because… I'm unsure about… I would reconsider if…* Fledge keeps every version, so you can see later how your view changed and what evidence you had at the time.

**Get alerts that earn their place.**
- Watch a company and Fledge checks news and discussion for real changes in tone.
- It also catches meaningful price moves, such as a big one-day swing or a move against the market.
- Urgent items go straight to your phone on **Telegram**. Everything else is collected into a **daily summary** and a **weekly review**.
- Tap **Useful** or **Not useful** on an alert, so alert quality can be measured over time.

**Ask from Telegram.** In your linked chat, type `/` to see the commands: `/today` (how your list moved), `/why NVDA` (the saved news, tone and filing next to one company's move), `/world` (world headlines that might matter for your list), `/explain` (a written explanation of your list, one AI request with its cost shown first) and `/watch NVDA` (turn on a company's news watch). Answers are facts and saved evidence only, and they also show up in the app.

**Arrange your pages.** On the home page and each company's summary, choose **Arrange** to drag sections, change their width, hide them or add optional ones: latest activity, price chart, the business, news watch, today's alerts, updates to review and world headlines, plus at-a-glance figures and analyst price targets in Pro. Your layout is saved to your account for each screen size. Phones get one simple column.

**Beginner and Pro modes.** Beginner mode rewords the same evidence in simpler language. Pro mode keeps the detailed tabs. Neither one changes the underlying facts.

## Principles

- **Evidence you can check.** Every conclusion links back to the original source and quote.
- **Honest about gaps.** If a source is unavailable, Fledge says so. Missing data is never shown as "neutral" or zero.
- **Facts and opinions stay separate.** Reported results, management forecasts, analyst estimates, social posts and AI interpretation are never blended into one number.
- **No buy/sell score, no streaks, no pressure.** Deciding not to invest is a valid result.
- **Your notes are private.** Your reasoning, watches and ratings belong to your account only.

## How it works

```text
   Public sources                    Fledge                          You
 ┌──────────────────┐      ┌─────────────────────────┐      ┌──────────────────┐
 │ SEC filings      │      │ 1. Collect              │      │ Web app          │
 │ News & RSS feeds │ ───▶ │ 2. Save with dates and  │ ───▶ │ (company pages,  │
 │ Reddit, HN       │      │    original quotes      │      │  your notes)     │
 │ Prices (Yahoo)   │      │ 3. AI reads the tone    │      │                  │
 │ Analyst targets  │      │ 4. Compare with before  │      │ Telegram         │
 └──────────────────┘      │ 5. Decide who to tell   │      │ (alerts and      │
                           └─────────────────────────┘      │  commands)       │
                                                            │ Daily & weekly   │
                                                            │ summaries        │
                                                            └──────────────────┘
```

1. **Collect.** Background workers regularly fetch filings, news, discussion and prices from public sources.
2. **Save.** Everything is stored with its publication date, source and original wording. Nothing is overwritten. History is append-only, so past readings stay exactly as they were.
3. **Read.** AI classifies each source's tone and what it's about. Every label is tied to the exact passage it came from.
4. **Compare.** Fledge compares the new reading with the last one to see whether anything materially changed.
5. **Route.** Each change is rated by urgency. Urgent ones go to Telegram, the rest to your daily summary.

**One analysis serves everyone.** The AI reading of a company's news is shared. If two people both watch Amazon, the company is analysed once and both of them get the result. Only your watch settings, alerts, ratings and notes are private to you. This keeps the cost of AI low as more people use it.

**Cost control.** AI calls are paid, so each one is recorded in a spending ledger with a daily alert level. Failed calls are kept, never silently retried, and unchanged text is never paid for twice.

### Built with

| Layer | Technology |
| --- | --- |
| Web app | React + Vite |
| Server | Python (FastAPI) |
| Database | PostgreSQL, with per-user row-level security |
| AI | OpenAI models, with prompts and models recorded for every result |
| Alerts | Telegram bot |

## Where it stands

Fledge is an **early product (MVP)** being built as a thesis project. It works end to end: research, saved reasoning, monitoring, alerts and summaries.

Honest limits:
- Sentiment quality is still being measured. In a check against 50 hand-labelled examples, the AI's tone ratings agreed with the human labels 48% of the time. It's a way to spot things worth reading, not a verdict.
- Some sources have partial coverage. Reddit access is limited and X (Twitter) is switched off.
- Price monitoring needs the app running on an awake machine. Fledge doesn't yet catch up on moves it missed while offline.
- It hasn't been tested with real participants yet, and it isn't ready for public launch.

## Try it

Setup, source status, and all the technical detail are in the **[setup and technical reference](docs/setup-and-reference.md)**.

To run it on a Mac, double-click **Start Fledge.command**, or run this from the project folder:

```sh
.venv/bin/python run.py --open
```

It needs your own API keys for news and AI, which go in a private `.env` file that is never committed. Without keys, it runs on built-in demo companies.

## Learn more

- [Documentation index](docs/README.md): every feature and its rules
- [Companion journey and product thinking](docs/features/companion-journey.md)
- [How alerts and Telegram work](docs/features/telegram-alerts.md)
- [Telegram commands](docs/features/telegram-commands.md)
- [Arrangeable home and summary pages](docs/features/workspace-widgets.md)
- [Where the code came from](PROVENANCE.md)
- [Implementation guide for contributors](AGENTS.md)
