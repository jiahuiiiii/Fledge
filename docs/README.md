# Thesis documentation

Use this index to find feature rules, development setup, testing guidance and earlier project decisions. Start with the [project README](../README.md) for the current user workflow and setup. [AGENTS.md](../AGENTS.md) records implementation constraints and the latest changes.

## Where things live

| Folder | Contents | When to use it |
| --- | --- | --- |
| [features](features/) | Research, sources, sentiment, alerts, valuation and export behaviour | Understand how a feature works and its limits |
| [development](development/) | API conventions and paid-provider controls | Work on integrations or configure the local installation |
| [testing](testing/) | Usability guide, feedback template, sentiment evaluations and alert replay | Test a workflow or inspect evaluation limits |
| [reviews](reviews/) | Dated implementation and verification reports | See what changed, what was checked and which failures remain |
| [archive/planning](archive/planning/) | Original product, architecture, database and UI proposals | Understand the original intent and earlier design choices |
| [archive/status](archive/status/) | Earlier status reports, trackers and requirements audits | Trace implementation history and earlier gap assessments |

Feature documents also retain dated sections. For current controls and scope, read the project README and latest applicable implementation notes; earlier phase descriptions are not new instructions. An archived proposal is not a claim that every proposed feature was built.

## Common starting points

- **Try the app:** [setup and current journey](../README.md), [usability testing guide](testing/wednesday-testing-guide.md), [feedback notes](testing/wednesday-feedback-notes.md).
- **Workspace layout:** [reading journey and evidence dialogs](features/reading-journey.md), [News and discussion UI](reviews/2026-10-09/news-discussion-ui.md), [My ideas UI](reviews/2026-10-09/ideas-ui.md), [Updates cards and disclosure fix](reviews/2026-10-09/updates-ui.md), [redesign verification](reviews/2026-10-09/reading-journey-and-evidence.md), [sidebar/progress controls and spacing](reviews/2026-10-08/layout-controls-and-spacing.md), [Workspace-only idea sidebar and company logos](reviews/2026-10-09/workspace-panels-and-company-logos.md), [compact logo rail and footer removal](reviews/2026-10-09/company-logo-rail-and-footer.md), [company report navigation, source icons and All view](reviews/2026-10-09/research-navigation-and-source-filters.md).
- **Sentiment and alerts:** [discussion themes](features/discussion-themes.md), [discussion summary feedback and actual failure](reviews/2026-10-09/discussion-summary-feedback.md), [bounded analysis batches and saved progress](features/sentiment-batching.md), [news and social watches](features/sentiment-alerts.md), [alerts linked to saved reasoning](features/idea-relevance-alerts.md), [Telegram delivery](features/telegram-alerts.md).
- **Research and prices:** [competitor position](features/competitor-position.md), [actual competitor verification](reviews/2026-10-09/competitor-position.md), [original management outlook](features/original-company-research.md#management-outlook-from-original-releases), [outlook redesign](reviews/2026-10-09/outlook-redesign.md), [outlook verification](reviews/2026-10-09/management-outlook.md), [company questions](features/question-research.md), [financial performance](features/financial-performance.md), [financial-position visuals](reviews/2026-10-09/financial-position-and-forecast-access.md), [reported revenue breakdown](features/original-company-research.md#reported-revenue-breakdown), [revenue verification](reviews/2026-10-09/reported-revenue-breakdown.md), [analyst targets](features/analyst-targets.md), [valuation scenarios](features/valuation-scenarios.md).
- **Business and accounts:** [four-part build audit and remaining access blocker](reviews/2026-10-09/four-part-build-audit.md), [annual peer revenue growth](reviews/2026-10-09/peer-revenue-growth.md), [visual peer comparison and draft preservation](reviews/2026-10-09/peer-comparison.md), [public annual financial forecasts](features/public-financial-forecasts.md), [forecast verification](reviews/2026-10-09/public-financial-forecasts.md), [original filings, business briefs and reviewed peers](features/original-company-research.md), [managed email login and recovery](features/managed-login.md), [implementation and actual access review](reviews/2026-10-09/original-research-and-managed-login.md).
- **Future work:** [business analysis expansion and beginner validation](archive/planning/product-and-launch-plan.md#future-business-analysis).
- **Source coverage:** [multi-source connections and Devvit assessment](features/multi-source-research.md), [Deus social research and Reddit access](features/deus-social-research.md), [working Reddit RSS posts/comments](features/reddit-rss-collection.md), [experimental Reddit HTML collector](features/reddit-html-collector.md), [social platforms](features/social-platforms.md), [current sentiment inputs](features/current-sentiment-sources.md), [news comparisons](features/news-coverage.md).
- **Development:** [API contract](development/api-contract.md), [paid AI controls and installation restriction](development/live-provider-controls.md), [source provenance](../PROVENANCE.md).
- **Evaluation:** [sentiment batching experiment](testing/sentiment-batching.md), [local sentiment model comparison](testing/local-sentiment-models.md), [alert continuity replay](testing/alert-continuity-replay.md), [sentiment and alert readiness](testing/sentiment-alert-readiness.md), [Reddit coverage and pacing review](reviews/2026-10-08/reddit-coverage-and-pacing.md).

## Database and local evidence

The ordered files in [migrations](../migrations/) define the application's database schema. [The archived SQL draft](archive/planning/schema.sql) is an unapplied planning reference; do not run it as a migration.

Private databases, credentials, source captures and test evidence under `.local/` are excluded from Git. A report may reference those local records even though they are not included in a clone. Preserve the report's original dates and limitations when reading its results.

## Keeping the folder organised

Add feature explanations to `features/`, developer setup to `development/`, and test guides or evaluation methods to `testing/`. Keep dated verification reports in `reviews/YYYY-MM-DD/`. Preserve superseded plans and status snapshots in `archive/`; update links when moving a file. Keep this top level for the index.

- [Full-corpus source analysis: batching and coverage redesign](reviews/2026-10-09/full-corpus-source-analysis.md)
- [Sentiment batch output-limit diagnosis and feedback correction](reviews/2026-10-09/sentiment-output-limit-feedback.md)
- [Sentiment low-effort GPT-5.4 tuning and actual test](reviews/2026-10-09/sentiment-low-reasoning.md)
- [NVIDIA comment-wording planning failure and explicit exclusions](reviews/2026-10-09/sentiment-own-wording.md)
