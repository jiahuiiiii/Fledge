# Thesis testing guide for Wednesday 7 October

Use this session to judge whether you can research a company, form an idea and follow changes without help. Allow about 45–60 minutes. Start with two companies you know well: one familiar starter such as AAPL or MSFT, and one outside the original six, such as AMD or TSLA. These are test examples, not investment recommendations.

Your research workspace has been reset. Companies, imported sources, saved ideas, analyses, alerts, watches, valuations and history start empty. A recoverable database archive is retained locally. Your API keys, public company directory and cumulative US$30 spending allowance remain in place; previous spending has not been erased. Restarting the app will not restore the fictional demo companies.

## Start the app

Double-click **Start Thesis.command** in the Thesis project folder. If it is already running, open [Thesis](http://127.0.0.1:8841/). Refresh an old browser tab once to load the updated interface. Keep the app running while testing; local scheduled checks need the Mac awake and the app process running.

Expect the empty welcome screen with **Add your first company**. Old bookmarked company links should recover to this screen. No model request should run just because you open the app, search for a company or navigate between tabs.

For the first five minutes, try the interface without reading the detailed steps below. Write down where you hesitate, what you expect to click and anything that feels unnecessary. Then use the checklist to cover the remaining paths.

## The main journey

| Step | What to do | What should happen |
| --- | --- | --- |
| 1. Find a company · 5 min | Search by company name, then ticker. Add your first company. Try a nonsense search too. | Matching name, ticker and exchange are clear. An empty search result gives a useful explanation. Adding opens the selected company's workspace and does not run AI analysis or enable monitoring. |
| 2. Load the evidence · 5–10 min | Choose **Refresh market**, **Refresh filings** and **Refresh daily history** once each. Open **Fundamentals** and inspect a source. | News, quote and filing periods are labelled. Missing data is visibly unavailable, never zero or made up. The chart and facts belong to your selected company. Source links and calculations are inspectable. |
| 3. Investigate a question · 5–10 min | In **Research question**, select a question or use **Edit question** to ask something concrete about the evidence you just loaded. Toggle **Include social discussion**, then choose **Answer this question** once. | Your question stays visible during loading. The answer cites inspectable sources and distinguishes evidence from interpretation. An answer without enough evidence should acknowledge the gap. Check that each citation actually supports the statement. |
| 4. Save an idea · 5 min | Choose **Save my reasoning**. Write your own view, save a draft, then edit it. If useful, add one numerical condition or a dated event condition and review its wording before approving monitoring. | A draft is recoverable. Editing does not silently approve a condition. The displayed comparison, period, date and threshold match what you chose. A previous saved revision remains in history. |
| 5. Check the selling points · 10 min | Open the news/social sentiment area. Choose **Refresh & analyse** once, then inspect the saved sources. If testing monitoring, enable **Watch news + social changes**, open **Check against my idea** and make one explicit check. | News and social discussions stay separate. Coverage, source age and missing channels are visible. Source excerpts are readable. Relevance to your saved idea is understandable. A quiet result is allowed; the app must not invent a change to create an alert. |
| 6. Check continuity · 5 min | Add the second company. Select it, then visit **My ideas**, **Updates** and **History**. Select the first company from each tab's sidebar. Try **All companies**, then reload. | Sidebar clicks filter the current tab. The selected ticker carries across tabs. Your first company's idea does not appear under the second. All companies removes the company filter. Header/sidebar remain stable while changed content loads. |
| 7. Check valuation · 5 min | Open **Valuation**. Fetch available analyst targets and reference data. Try a scenario with your own assumptions, then change one input. | Analyst consensus is separate from your calculated scenario. The graph shows lowest, mean, median and highest targets with the retrieved quote. Upside/downside uses that same quote; no quote means no invented percentage. Source, timestamp, horizon and unavailable inputs are clear. A scenario changes only when its assumptions change; it is not presented as a buy/sell instruction. |
| 8. Check everyday controls · 5 min | Remove a company, undo it, then restore it from **Add company → Manage sidebar**. Try the custom dropdown and checkboxes with Tab, arrow keys, Space and Escape. Resize the window and reload once more. | Removing only hides the sidebar entry; saved research stays. The revert icon and close icon sit together at the far right. The revert icon restores the company; close dismisses the notice. The row and green background animate smoothly. Dialogs close reliably, keyboard focus is visible, controls remain usable on narrow screens, and saved work survives reload. |

## Focused sentiment and alert checks · 15 minutes

Use NVDA or MSFT for the first social check; Hacker News tends to cover technology discussions. AAPL may have a thinner discussion sample. These are testing choices, not stock recommendations.

1. Read three original source excerpts before looking at the labels. Record your own reading: company relevance, current opinion and whether an actual development is stated.
2. Compare **News framing**, **Reddit discussion** and **Hacker News** separately. Inspect the sample date, selected count and distinct authors. Eight posts from one author are not eight independent investors. A missing platform or thin sample should be obvious.
3. Expand the event-evidence detail on a news item. Opinion and vague teasers can affect sentiment while staying ineligible for a company-event alert. A specific rumour must remain unconfirmed. The stated effect of a development is separate from the whole article's tone.
4. With **Watch news + social changes** enabled, try **Check against my idea** with the question-answer focus. Verify the actual source answers your question rather than merely mentioning the same company. A partial answer must not become a complete answer. Keep a screenshot of any mismatch.
5. Enable one news/social watch, inspect its baseline and check history, then turn it off after the exercise. Reopening the same sample must not create duplicate alerts. Changed labels alone, without new sources, must not create new events.
6. In Updates, inspect a source before marking an alert reviewed or unresolved. Confirm that each action persists after reloading and does not change the underlying evidence.

Do not wait for a real market event to finish this session. The local developer tests separately replay an adverse report, an unconfirmed claim, an unchanged duplicate and a genuine correction. Those authored checks are not added to your clean workspace. Your manual session tests whether the explanation and controls make sense; a later prospective monitoring trial is still needed to measure missed alerts and delivery delays.

## Test alerts without wasting the session waiting

To exercise monitoring, enable one watch, read its selected frequency and inspect a manual check against your saved idea. Watch settings and **Check against my idea** are only shown while that watch is enabled. Turning the watch off hides both without clearing their saved choices; saved checks and alerts remain readable. Leave the app running for scheduled checks. The initial watch establishes a baseline; it should not flood Updates with old sources. New eligible information is needed before a meaningful new alert can appear.

Do not judge an empty Updates tab as a failure by itself. Check whether the watch is enabled, when it last ran, what it checked and why it stayed quiet. Record unclear explanations as a UX problem. A real alert arriving during a short session is not guaranteed. Turn off the watch afterwards if you do not want further scheduled acquisition or model spending.

## Avoid repeated waiting and unnecessary calls

- Run each AI action once, then inspect its result. AI analysis can take noticeably longer than navigation. Clicking repeatedly should not be necessary.
- Reopening saved research and changing tabs should use saved information. A new answer or analysis is an explicit paid action under the same remaining build allowance.
- Market refreshes are at least five minutes apart; filings and social acquisition generally have longer cooldowns. Analyst targets are checked once per company per 24 hours. Respect the displayed message instead of retrying repeatedly.
- If a provider reports unavailable or rate-limited, record the exact message and continue another part of the journey. A partial dataset should remain usable.
- Do not paste API keys into feedback or screenshots.

## What to treat as an open limitation

The company directory covers supported US exchange listings, not every worldwide security. Class/preferred symbols and separate workspaces for two share classes of the same issuer are not fully supported. Foreign filers and companies with unusual accounting tags may have incomplete fundamentals. Adding a company does not guarantee every data provider covers it.

Social sources are selected discussions, not a representative survey of investors. Matching for newly added companies is deliberately conservative and may find fewer discussions. Reddit availability can vary. News sentiment, discussion sentiment, analyst targets and your own valuation assumptions should never look interchangeable.

AI citation checks do not prove that an interpretation is correct. Earlier developer tests still found semantic errors in some sentiment and answer cases. If an explanation overstates a source, uses an old opinion as a current view, or calls unrelated information a risk, record it as a correctness issue even when the interface looks polished.

## Record useful feedback

Use [Wednesday feedback notes](wednesday-feedback-notes.md). For each issue, include:

1. The ticker and tab, plus window size or whether the browser was full screen.
2. The exact steps you took.
3. What you expected and what actually happened.
4. A screenshot and the approximate time, particularly for loading or API failures.
5. The impact: **Blocked** means you could not continue; **Confusing** means you continued with uncertainty; **Cosmetic** means appearance only; **Incorrect** means the data or interpretation is wrong.

Finish by answering: Could I explain what this product helps me do? Which part would make me return? What took the most effort? What would stop me trusting it? Which three changes matter most before a pitch?

Keep the first pass focused on that journey. Extra features can wait until these observations show where they would help.
# Telegram delivery — additional Wednesday checks

The top-bar **Telegram** button works before you add a company. Follow [the connection guide](../features/telegram-alerts.md) to add your dedicated bot token, open its link, press Start, and check the linked chat. Send a connection test first; verify both the message in Telegram and the **Delivered** status in Thesis.

Then enable **Send future alerts to this chat** and set up the relevant company watch. The first watch check establishes a quiet baseline; it should not send all existing news. Later published company, saved-idea or monitored-condition alerts should appear once in both Updates and Telegram. A published manual evidence check can also generate a message. The local server and Mac need to remain running.

Check the ticker, reason, source links, news/social distinction and timestamps. For an idea alert, check that the question is your current saved revision. Open sources on your phone, then inspect the full update on this Mac. These are research alerts, not instant price alarms.

Pause Telegram and verify a newly published alert stays in Updates without a Telegram message. Re-enable it: the old alert should remain unsent. Disconnect and verify the chat label disappears. If Telegram cannot confirm delivery, the app should say so and avoid an automatic duplicate. Record the message status and approximate time in your test notes; never copy the bot token.

If no new market evidence arrives while testing, the connection-test message verifies the delivery channel without inventing a real development. Automated coverage separately exercises all three real alert publication paths with fictional/mocked providers. Live Telegram receipt still needs your configured bot and chat.

## Updates for 8 October: questions and source loading

1. Add a company and open it. Initial quotes/news, filings, daily chart and price-reference checks should start together where independent. Inspect **View progress** for each completed step or coverage gap.
2. Use **Refresh research** for the company data. Use **Refresh & analyse** inside news/social sentiment for collection followed by explicit AI analysis. Discussion windows are 24 hours, 7 days (default), or 30 days; news and automatic watches retain seven days. A wider window does not guarantee more Reddit posts.
3. Choose **Add question**, write your own question and save. Reload, switch companies, and return: your question should remain selected and available in the dropdown. Adding a question should not run AI or start monitoring.
4. Choose **Answer this question** in the same card when you want an answer. Review the source links and unknowns. Saving a question and saving/monitoring an investment idea are separate explicit actions.
5. Check the MiSans text and field focus borders. In suggested changes, compare original and proposed content, inspect supporting passages, and verify that nothing applies until review and save.
