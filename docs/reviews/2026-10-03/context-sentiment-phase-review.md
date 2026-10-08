# Phase 35 — using verified conversation context

This is a parent-authored review from five perspectives, not independent consultant signoff or participant research.

| Perspective | Finding | Change and remaining requirement |
| --- | --- | --- |
| Product | Reading an isolated reply can lose the subject of agreement/disagreement. Existing parent inspection did not help the classifier. | Let a new classification use a verified saved parent, with a visible source trail. Broader thread and private-idea interpretation remain incomplete. |
| Research | Parent tone cannot be counted as the commenter's opinion; a new context check cannot establish historical thread wording. | Preserve separate messages, exact dates, child body evidence and parent citations. Ambiguity remains permitted; semantic accuracy needs actual model evaluation. |
| Data/ML | Unbounded context can inflate costs and import missing or unrelated evidence. | At most four exact-child parents, 3,000 bytes each/8,000 combined; require recent available checks and complete passages. Keep one vote per original child and the existing global cost limits. |
| Architecture | Context must survive immutable history without silently changing old labels or leaking withdrawn text. | Pin the parent-result identity; reuse identical content; check withdrawal on every derived read. No new table, provider, model or migration. |
| UX/business | A context-driven relabel is easily mistaken for market movement. | Expose context beside labels/history/alerts and in exports; suppress aggregate reversals when shared-comment context changed. This is a quality safeguard, not proof of return visits or willingness to pay. |

## Verified software behavior

725 integrated backend checks pass with both retained actual SEC corpora. A further 26 focused context/export checks pass after adding an escaped-download/withdrawal test. Twelve frontend checks and the production build pass. The context browser journey exercises a wholly authored, mock-classified sample at 320/390/1440px: four parent messages appear as context, sources remain separate, original/source links work, reads make no paid request, failure recovery works and watches stay off. No authored fixture is installed as actual-company research.

Tests cover exact per-child parent identity, no extra votes, context byte/count bounds, future/stale/failed/removed exclusions, old-reading preservation, identical-recheck caching, malformed/foreign context references, source withdrawal before/during work, changed-context history, reversal suppression with new text, and escaped/withheld alert exports. An initial test placed its cutoff before all source acquisition and therefore had no sample; it was corrected to test the context cutoff directly against the actual source availability. It was a test setup failure, not evidence of classifier quality.

The classifier's new output schema is structurally checked offline. This phase makes no actual model call; whether the model reliably distinguishes disagreement, sarcasm or an unresolved pronoun with the parent remains unverified. The earlier Microsoft theme-check miss and the interrupted Amazon check remain unresolved evaluation evidence and are not erased by this work.

## Actual retained-source verification

The installed input audit and frozen request files record which retained Microsoft/NVIDIA child-parent pairs are selected, compare every supplied parent passage and date to the original retained API responses, and verify that parent text is not added to sample counts. This is read-only input/provenance verification, not a new classification, historical monitoring result or independent accuracy benchmark. Final evidence and installation details are appended below after they are checked.

## Installed input audit and handoff

Evidence: `.local/live-tests/sentiment-context-20261002T220012Z/`. Source/database backup: `.local/backups/phase35-sentiment-context-20261002T220010Z/`. Installation verified that every preexisting row and private configuration value remained unchanged. Schema remains 25; no authored classification was inserted into the main research database.

Read-only projection of the retained actual Microsoft and NVIDIA cases selected sixteen original texts each, including four HN comments each. Two Microsoft parents (five passages) and three NVIDIA parents (three passages) were eligible. All five child/parent identities, parent publication instants and eight supplied parent passages match the retained original API responses. Parent messages are nested context, not additional source items. An initial audit compared equivalent timestamp strings using different timezone offsets; comparison was corrected to the timestamp instant before the audit passed. No source or model request was made.

The requests and review criteria are frozen under `frozen/`, marked undispatched. Existing actual sentiment and theme outputs remain unchanged with their original methods. The app's new context-aware method has not yet been exercised against OpenAI; offline checks and input matching must not be described as semantic accuracy. The authored browser sample demonstrates the interface only.

The original cumulative budget is unchanged: US$7.407271 confirmed, US$0.301565 held, US$2.291164 remaining, 194 calls. The Amazon timeout remains the one currently blocking unresolved charge; its original response is unavailable and no retry was made. All news and filing watches remain off. Phase 34's incomplete actual evaluation and the broader implementation requirements remain open.

Installed-browser review found two older source-view sentences still claiming all AI readings omit parent context. They were corrected to describe the exact saved analysis and distinguish later source inspection from reclassification. The final production build and authored context browser journey pass after that copy correction.
