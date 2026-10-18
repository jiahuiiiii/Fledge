# Reddit reply parents and label rerun — 18 October 2026

## Finding

Reddit's thread RSS feed has no parent IDs, but each reply's own context feed (`<reply link>/.rss?context=8`) lists the thread post, the reply's ancestor line and the reply. A one-request live probe returned exactly post → parent → reply. This was not tested before; earlier sessions only examined the thread feed.

Reddit ends RSS on 13 November 2026 and stops accepting new API access requests after 31 October 2026, so this route is temporary.

## What changed

- `thesis/research/reddit_parents.py` checks up to three saved replies after each live Reddit refresh (two-minute budget), validates the context feed and stores only the immediate parent in the existing saved-parent records. A fault never fails the refresh. See [the RSS contract](../../features/reddit-rss-collection.md#verified-reply-parents--18-october-2026).
- Sentiment uses a Reddit parent for seven days; Hacker News keeps 24 hours.
- The quality runner gained a `parents` plan variant and `--reuse-settled`, which reads settled answers to byte-identical requests for free and never re-sends a failed one.
- Not yet deployed: the running app needs a deliberate restart from the owner's Terminal.

Tests: 134 Reddit, 435 related sentiment/context/watch (4 skipped), 46 other watch (3 skipped), 34 quality-runner; all offline.

## Rerun

Fetched 16 reply chains for the 50-case set through the shared paced reader (no AI cost, private files only): 15 parents available, 1 removed. Prompt `thesis-source-sentiment-tasks-4`, GPT-5.4, topic plus verified parent, no unordered siblings.

| Context sent | Agreed-rules match | Relevance | Tone | Hard cases |
| --- | --- | --- | --- | --- |
| Full saved thread, unordered | 32/50 | 38/50 | 37/50 | 4/6 |
| Topic + verified parent | **40/50** | 45/50 | 44/50 | 4/6 |

On the 15 replies with a parent: 11/15 match, compared with 3/15 when the full thread was sent.

First attempt stopped after three calls on a runner bug (a private parent lacked an evidence identity); fixed with a test, then completed with identical requests. New spend for both attempts: US$0.203885 over 19 calls, none unresolved. Agreed-rules reference: 14 owner-agreed changes; the original owner file is unchanged.

The agreed reference was settled on this same set, so a small fresh set labelled under the same rules is still the confirmation step before release. Remaining differences: cases 01, 03, 05, 08, 15, 21, 26, 28, 29, 48.

Private output: `.local/live-tests/redesign-phase-5-20261018/parent-context-run2/` (failed first attempt in `parent-context-run1/`).
