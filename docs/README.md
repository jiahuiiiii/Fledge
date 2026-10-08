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
- **Sentiment and alerts:** [news and social watches](features/sentiment-alerts.md), [alerts linked to saved reasoning](features/idea-relevance-alerts.md), [Telegram delivery](features/telegram-alerts.md).
- **Research and prices:** [company questions](features/question-research.md), [financial performance](features/financial-performance.md), [analyst targets](features/analyst-targets.md), [valuation scenarios](features/valuation-scenarios.md).
- **Source coverage:** [multi-source connections and Devvit assessment](features/multi-source-research.md), [Deus social research and Reddit access](features/deus-social-research.md), [social platforms](features/social-platforms.md), [current sentiment inputs](features/current-sentiment-sources.md), [news comparisons](features/news-coverage.md).
- **Development:** [API contract](development/api-contract.md), [paid AI controls and installation restriction](development/live-provider-controls.md), [source provenance](../PROVENANCE.md).
- **Evaluation:** [local sentiment model comparison](testing/local-sentiment-models.md), [alert continuity replay](testing/alert-continuity-replay.md), [sentiment and alert readiness](testing/sentiment-alert-readiness.md).

## Database and local evidence

The ordered files in [migrations](../migrations/) define the application's database schema. [The archived SQL draft](archive/planning/schema.sql) is an unapplied planning reference; do not run it as a migration.

Private databases, credentials, source captures and test evidence under `.local/` are excluded from Git. A report may reference those local records even though they are not included in a clone. Preserve the report's original dates and limitations when reading its results.

## Keeping the folder organised

Add feature explanations to `features/`, developer setup to `development/`, and test guides or evaluation methods to `testing/`. Keep dated verification reports in `reviews/YYYY-MM-DD/`. Preserve superseded plans and status snapshots in `archive/`; update links when moving a file. Keep this top level for the index.
