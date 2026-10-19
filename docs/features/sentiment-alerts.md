# News, social sentiment and local watches

This document describes the phase 11 company-level sentiment and watch layer. Phase 12 adds [private checks and alerts linked to saved reasoning](idea-relevance-alerts.md), including qualitative drafts. Statements below about company-based alerts describe this layer, not the full current product.

Phase 19 adds [explicit comparisons of news coverage](news-coverage.md). Related reports can count as one development while retaining each source and its framing. Only justified repeats may inherit seen-report identity; added details and contradictions stay eligible for review. This supersedes the original exact-body-only and no-semantic-clustering limits below within a bounded seven-day sample. Old stored analyses retain their original policy.

The main pitch workflow is now source → separate news/social labels → grouped change alert → exact evidence → saved-idea review. The collection/classification mechanisms adapt Deus; the workspace and review patterns extend the existing Kestrel adaptation. This is the new implementation priority requested by the user, ahead of extra valuation breadth.

## Visible reading controls — 11 October 2026

**What’s the tone?** keeps **Discussion window** and **Watch · on/off** directly to the left of **Refresh & analyse**. They are always visible, without opening a Reading settings disclosure. On narrow screens the window and watch share a row above the refresh button. Controls retain labelled keyboard interaction and at least 44px touch targets.

The watch button opens the existing settings dialog; it does not switch monitoring on or off by itself. Window choices remain 24 hours, seven days and thirty days; selecting one changes the next manual reading, not the displayed saved result or the automatic seven-day watch. Saved-reading dates/window and the next watch check stay below the header. Existing disabled-action reasons remain linked to the refresh button. No acquisition, analysis, scheduling or accounting behavior changes.

[Implementation and verification](../reviews/2026-10-11/tone-header.md).

## User flow

Choose Microsoft, Apple or Alphabet. Refresh market data and social posts, then choose **Analyse sentiment**. Company news and Reddit discussion have separate counts, explanations and exact cited passages. Open the original source from any item. Missing coverage is not neutral sentiment; a directional summary requires at least three interpretable text groups and a strict majority in that direction. Identical substantive news bodies count once even when titles differ; conflicting labels within a group become mixed or unclear. Social coverage shows represented authors, three communities and the absence of comments/other platforms.

Turn on **Watch news + social changes** to check hourly or every four hours while the local app runs. It is off by default, starts no immediate paid call and shares the original budget. The first analysis establishes a baseline. Repeated unchanged requests use the existing analysis. Summary policy is versioned separately from the model request, so changing code-owned counts reuses the same paid response. A due watch fetches news and social sources, analyses a changed sample and stores alerts in **Updates**. Turning the watch off fences unfinished checks before publication; an already dispatched model request cannot be cancelled or refunded.

A change from positive-leaning to negative-leaning, or the reverse, produces one grouped sample alert when new content exists. Newly seen adverse/mixed news classified as a reported development or rumour produces one grouped news alert. Rumours remain unconfirmed. Opinion alone does not become a reported business event. Previously seen content stays suppressed even after falling out of the selected sample. These policies are product rules, not calibrated investment signals. Different wording about the same underlying event may still create another alert; semantic event clustering is incomplete.

Alerts preserve both analysis IDs, source cutoffs and the saved reasoning revision, if present. Mark reviewed, leave unresolved, or open the idea. The current alert rule is company-based; attaching saved reasoning does not establish a private AI relevance judgment. Event criteria and explicit private comparisons remain available separately.

## Boundaries

Reddit collection reads at most 50 recent public posts from each of r/stocks, r/investing and r/wallstreetbets, with a shared 15-minute cooldown. It does not search all Reddit history. Company aliases select candidates; the model must determine relevance. Latest post versions and current news from seven days are eligible. Since 9 October, analysis includes every eligible saved original in bounded requests of up to eight sources; see [whole-source batching and exclusions](sentiment-batching.md). Source versions, not live webpages, support the stored quotations. Finite recent coverage can miss important opinions. No claims of market consensus, verified events or trading accuracy are made.

Both channels use the existing pinned OpenAI reasoning model and cumulative ledger, with no automatic paid retry. Structured output must classify every selected item once and cite its own original passages. Exact passages do not by themselves establish correct interpretation. Provider denials, old analyses and failures are visible. Source access withdrawal withholds affected analysis/alerts. Social HTML is normalized to plain text. Author hashes serve sample counts and are not passed into classification.

Migration 012 adds public immutable post/analysis records and private row-scoped watches, seen-content records, alerts and review acknowledgements. Baseline and alert analysis foreign keys enforce company membership. A claim token fences disabled/reconfigured checks; source cutoffs prevent late results from moving a watch backwards. Alert insertion, baseline movement and seen-content recording are atomic. Restart catches up one due check, not every missed hour. PostgreSQL remains the only database.

No external notification destinations, account integrations, new provider keys or production deployment were added. The public RSS interface was reachable in the development probe; availability remains external and is not a production guarantee.

## Verification

Initial offline integration: 290 backend tests with the saved actual SEC corpus, plus five frontend checks and a successful production build. Twenty-three final sentiment-specific checks cover source validation/denial, deduplication, thin samples, malformed responses, quotes, cache reuse, source withdrawal, private reviews, old-result fencing, opt-in scheduling and repeat suppression. All provider calls in these tests are mocked. Browser and actual-source/model results are recorded separately in the phase review as they complete.


## Later reporting clarifications — phase 25

Company watches also retain new cited details/contradictions linked to exact earlier reporting they saw, regardless of adverse tone. Alerts and weekly exports show both reports. [Rules and limits](reporting-updates.md). Earlier descriptions restricting reporting alerts to adverse/mixed items describe the initial rule. No old alerts are backfilled.

## Displayed lean — 18 October 2026

The owner found that almost every reading showed "mixed / balanced": the saved rule needs a strict majority of all counted groups, and neutral factual news is usually the largest group. On 18 October META news had 26 positive and 9 negative groups among 87 and still showed mixed.

Readings now display a lean (`sentiment-lean-1`) computed from the saved counts when they are shown. A side leads when it has at least twice the other side's groups, with at least five positive plus negative groups. With fewer, the reading shows "mostly neutral" if neutral is the largest group, otherwise mixed. Neutral and mixed counts are listed separately. Thin samples and separate platform samples are unchanged. The same 18 October counts give META positive leaning, while GOOGL (21/13), AVGO (21/13) and NVDA (22/19) stay mixed.

The saved summary, its `sentiment-coverage-9` policy, answer reuse and opinion-change alerts are unchanged; the stored majority tone is shown beside the lean as `majority_tone`. Changing the policy would have forced paid re-reads of every saved reading. Older readings get the displayed lean too, from their own counts.
