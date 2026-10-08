# Comparing saved sentiment samples

Expand **Compare sentiment samples** in the news/social panel. Choose a later and earlier recorded analysis. The view opens their original news/social summaries side by side, with source cutoffs, saved times and exact source inspection. It does not fetch news/posts, request AI, enable a watch or create a review event.

The comparison separates newly selected text, text no longer selected, unchanged text with different labels, and unchanged text with the same labels. Identity uses each channel and the full stored content hash, including the headline. A changed headline is not hidden by a copied body. A source moving into the sample is not necessarily newly published; one moving out is not a retraction. Comparison-only news is excluded from selected-source change counts.

Labels include relevance, tone, statement type and topic. Wording changes alone do not count as a label change. Method changes (model, prompt or counting policy), changed additional comparison context and changed news grouping links are disclosed separately. A repeated analysis of the same texts does not establish new reporting or a shift in market opinion. This is an irregular sample comparison, not a continuous sentiment index, causal explanation or market-wide trend.

Both samples retain their own news grouping and social classifications. Missing channels are explicit. Historical headlines, snippets/posts and exact cited passages come from that analysis's immutable packet. The existing source-access check applies to both samples and all consumed comparison sources. If either sample is withheld, derived comparison content is also withheld. Reads use one consistent database snapshot.

Twenty samples load per page in descending source-cutoff/saved-time/ID order. The cursor must belong to the selected company. An unchanged cached analysis is not a new entry. No migration, model/prompt change or upstream dependency is needed: the view reuses existing sentiment records and Kestrel-derived source/review controls. This does not reconstruct old operational source-health snapshots; **Watch check history** supplies those for attempts recorded since phase 21.

See the [phase review](../reviews/2026-10-02/sentiment-history-phase-review.md) for automated checks and actual-record verification. Stored sentiment labels remain AI interpretations, not independently verified facts.
