# Deus social research integration

Implemented 8 October 2026. **Latest follow-up:** [working hot-post and comment RSS](reddit-rss-collection.md) supersedes the old Reddit company-search acquisition described below; original denials remain preserved. Follow-up: [broader publisher feeds, Alpha Vantage, X and Devvit assessment](multi-source-research.md). This replaces the old general-feed/short-search acquisition path for company research. [Verification and remaining gaps](../reviews/2026-10-08/deus-social-integration.md).

## What happens when you refresh

1. Search for the selected company, within the chosen discussion window (24 hours, seven days by default, or 30 days).
2. Verify discovered comments at their original source. Search-index snippets are discovery hints, not evidence.
3. Retrieve bounded immediate-parent context before classification. Each reply keeps its own wording, date and source link; a parent is context, not another opinion or an endorsement.
4. Remove exact duplicate texts and limit selection to two items per thread. Alternate available platforms. The existing analysis limits remain eight news and eight social texts, with separate byte/context limits.
5. Classify the selected sources, retaining exact evidence for each label. News, Reddit and Hacker News remain separate. Missing access or no matching posts does not mean neutral sentiment.

First company open and **Refresh research** acquire sources without a paid AI request. **Refresh & analyse** also requests the existing metered analysis. Saved records remain readable. A new method does not relabel old samples or trigger a historical alert backlog.

## Source behaviour

| Source | Collection | Current limitation |
| --- | --- | --- |
| Hacker News | Exact company-name search with typo expansion disabled; original API verification; discovery through up to three company-related stories and eight immediate replies per story; context for up to three direct-search replies | Technology-community discussion, not representative investor sentiment. Search and the original API can omit or remove material. |
| Reddit | Company search across enabled investing communities, up to 50 posts; adapter supports up to 12 immediate replies from each of three matching posts | The actual public comment request returned HTTP 403. Collection is paused until a supported, approved connection is configured. Reply parsing/storage is tested with controlled inputs, not claimed as working live access. |

Hacker News considers up to 40 direct search results and eight story candidates, then verifies a bounded mixture of at most 48 comments. Parent attachment in a model packet still allows at most four parents, 3,000 bytes each and 8,000 combined. A reply discovered only through its thread is excluded from model input if its necessary parent context is unavailable. Not every collected item fits the analysis sample.

The original optional watch context setting remains an additional check of selected saved replies. Discovery now also saves the context it used to identify a reply. Turning that optional check off does not remove already saved context. No existing watch is enrolled or enabled by this integration.

Reddit requests share persistent pacing. A rate-limit rejection pauses requests for the provider's cooldown; HTTP 401/403 stops further attempts, including after restart or workspace reset. There is no mirror, proxy, cookie or user-agent workaround. Historical RSS shutdown handling remains in place.

## Applying for Reddit access

An OpenAI key pays for analysis; it does not grant permission to collect Reddit content.

Use Reddit's [developer API request form](https://support.reddithelp.com/hc/en-us/requests/new?tf_42139884615700=api_request_type_developer_clone&ticket_form_id=14868593862164). Explain the company-research prototype, the communities and posts/comments needed, approximate volume, retention/deletion approach, and proposed processing of selected text by OpenAI. State that the current work is for student testing/pitching and disclose possible monetisation. For commercial use, Reddit provides a [commercial enquiry route](https://support.reddithelp.com/hc/en-us/requests/new?tf_42139884615700=api_request_type_enterprise_clone&ticket_form_id=14868593862164). Approval and allowed uses are Reddit's decision; see its [Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy).

An approved OAuth connection is **not yet implemented** in Thesis. Once Reddit confirms the allowed access method and use, that connector must be added and tested. Do not clear the access-denial state just to resume rejected public requests. Keep any eventual credentials in the private project environment, never in Git or chat.

## What is reused from Deus

The pinned reference is [Deus 74d5aea](https://github.com/c0vo/Deus/tree/74d5aea8b0acf72e1851dfc841f9f1408e9e6609): source fan-in, discovery before enrichment, duplicate handling, bounded reply enrichment, platform-aware investing vocabulary, and complete structured batch classification. Thesis adapts those mechanisms to its PostgreSQL source versions, source permissions, original spending ledger, and existing alert rules.

This does not run the whole Deus application. Its old Reddit-host fallback, Nitter mirrors, numeric sentiment scores, trading predictions, embeddings pipeline and separate provider configuration are not installed. No local FinBERT model has been promoted from the earlier experiment. More collected text does not establish better interpretation, price prediction or alert accuracy.
