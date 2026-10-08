# Local API contract

The inspected Kestrel frontend uses `/api/v1`, cookie credentials, string UUIDs, a top-level `result`, and errors shaped as `result.errors[{error_code,error_message}]`. Thesis preserves those conventions while replacing multipart semantic mutations with one transaction. It does not emulate the old authentication, proposal, catalyst, Telegram, stock-list or notification endpoints.

All account context comes from the server's local demo session. Client-supplied owner IDs are rejected as extra fields. Normal reads/writes use the `thesis_app` PostgreSQL login with transaction-local account context. This account is local-demo authentication, not a production account provider.

| Method and route | Behaviour |
| --- | --- |
| `GET /api/v1/session` | Bootstrap the local HttpOnly SameSite=Strict demo cookie; same-origin only. |
| `GET /api/v1/workspace` | Current permitted research, recorded cutoff, source checks, private current idea, full revision/evaluation snapshots and pending/failure state. |
| `POST /api/v1/idea` | Atomic whole-revision save. Requires `expected_revision`; returns 409 on a concurrent change. |
| `POST /api/v1/research-actions` | Append question and `investigate`, `unresolved` or `reject`. |
| `POST /api/v1/evaluations/{uuid}/review` | Append `reviewed` or `unresolved`; repeated/concurrent requests return the existing event and never change the result. |
| `POST /api/v1/demo/advance` | Explicitly advance the fictional corpus, with `expected_stage`; not a live refresh endpoint. |

Mutation requests require `X-Thesis-Request: local-ui`; origin and fetch-site checks reject cross-origin calls. Request models reject unknown fields. A save example:

```json
{
  "expected_revision": 1,
  "question": "Can growth hold up without sacrificing margins?",
  "reasoning": "Renewals may sustain demand; slower growth would challenge my idea.",
  "status": "monitoring",
  "conditions": [{
    "condition_id": "22222222-2222-4222-8222-222222222222",
    "metric": "revenue_growth",
    "operator": ">=",
    "threshold": "15",
    "unit": "percent",
    "basis": "reported",
    "period_type": "quarter"
  }]
}
```

Thresholds are decimal strings. Both revenue growth (year over year) and operating margin use reported calendar-quarter percentage values in this fixture. Monitoring requires reasoning and one to four conditions. A draft permits an empty condition list. `archived` creates a new revision and stops future monitoring. A whole save requires all fields; it does not reinterpret missing fields as PATCH semantics or use the legacy `<None>` sentinel.

A successful save returns `result` containing `thesis_id`, `version_id`, `revision` and optional queued `job`. The UI only reports success after that transaction commits. Evaluation manifests preserve the full condition definitions, all assessed document/fact versions, source checks, cutoff, period, availability policy, evaluator version and explicit model=`none`.

No private reasoning enters the shared source corpus. Historical results are reconstructed using their immutable revision and manifest, never today's thresholds. An old job may finish into its own history but cannot update the current revision pointer. Shared source retrieval is restricted to the authored fictional entitlement and availability cutoff; later restatements cannot enter an earlier assessment.

## Portable review export — phase 8

`GET /api/v1/ideas/versions/{version_id}/review-export` returns an HTML attachment. Optional `evaluation_id` or `comparison_id` selects exactly one record belonging to that owned revision; supplying both is invalid. A comparison can include its own linked numerical assessment. Omitting both exports only the saved definition. The existing local-session and source-access rules apply, with `Cache-Control: no-store`; no provider request is made. This attachment intentionally does not use the ordinary JSON `result` envelope. Errors retain the existing JSON envelope. See [export behavior](../features/review-export.md).

## Event conditions (migration 010)

Complete revision saves accept optional `events` (default empty, maximum three), each with `condition_id`, `description`, `evidence_requirement`, `role` (`required` or `risk`), `window_start` and `deadline` (inclusive UTC publication dates). Numerical `conditions` remain required and may be empty. Monitoring requires substantive reasoning and at least one event or numerical condition. IDs are unique across both lists. Dates must be ordered within ten years.

`POST /api/v1/ideas/versions/{version_id}/event-review` accepts `snapshot_id` and no `evaluation_id`. It makes an explicit metered request or returns the exact cached result. Empty eligible source windows are rejected before dispatch. History includes `events`, `event_reviews` and per-assessment `event_results`. `GET .../review-export?event_review_id=...` exports one selected event check; it is mutually exclusive with comparison/assessment selection. An assessment export includes the exact event check referenced by its manifest. Source access applies at read/export time.

## Typed proposals (migration 011)

`POST /api/v1/proposals/generate` accepts company `instrument_id`, current `snapshot_id`, nullable `base_version_id`, and a `question` for a starting idea. Returns explanation and pending typed proposals. The workspace exposes their before/after candidates, source citations, pending/stale/approved/rejected status and accepted revision. `POST /api/v1/proposals/approve` accepts one to three distinct `proposal_ids` and the complete reviewed `definition` using the ordinary `SaveIdea` contract. It atomically creates one revision and immutable decisions, or returns the same accepted revision for an identical repeated approval. `POST /api/v1/proposals/{id}/approve` supports a single complete definition; `POST .../{id}/reject` records a rejection. Source or base changes return a conflict on approval. Both source/owner gates still apply when reopening old proposals. No generation or decision occurs on GET.

## Private news/social relevance checks (migration 013)

- `POST /api/v1/companies/{instrument_id}/idea-alert-check`: explicit check of `analysis_id` and `version_id` UUIDs. The server supplies the owner; neither ID permits crossing company/owner boundaries.
- `POST /api/v1/idea-alerts/{check_id}/review`: append-only `reviewed` or `unresolved` acknowledgement. Identical repetition is idempotent; a conflicting acknowledgement fails.
- `GET /api/v1/idea-alerts/{check_id}/export`: inert private HTML, through the same owner/source boundary, with no source/model request.
- Existing news-watch configuration accepts optional `match_idea`; omission preserves the prior choice. Enabling it requires active saved reasoning and establishes a quiet baseline. The configured interval remains 60 or 240 minutes.
- Workspace state adds owner-scoped `idea_alerts`, the selected company's `idea_watch_state` and `news_watch.match_idea`. Company unread counts include published unreviewed checks.

Relations are `supports`, `challenges`, `risk`, `context`, `unclear` and `unrelated`. The first three can publish; risks do not assert the user holds a directional belief. Exact selected source and reasoning segments, revision, cutoff, model and prompt version travel with each immutable result. A stale or disabled completion can be saved historically without publication. Existing same-origin/session protections apply.

## Periodic research review (phase 13)

`GET /api/v1/research-review` reads the current owner's saved condition changes, company alerts and published private reasoning checks. Filters are `days` (0 for all retained records, 1, 7 or 30; default 7), timezone-aware nonfuture `cutoff` (default now), optional owned `instrument_id`, `review` (`all`, `pending`, `unresolved` or `reviewed`) and nonnegative zero-based `page`. Responses include exact counts, company overviews, current coverage and up to twenty timeline entries. Keep the returned cutoff for later pages. The period bounds app-record creation; current review acknowledgements and coverage are labelled with generation time. These are owner-scoped, repeatable-read transactions with no supplier/model call.

`GET /api/v1/research-review/export` accepts the same period/company/status filters and produces an inert private HTML attachment containing all matches. It refuses more than 1,000 records with a narrowing instruction. Same-origin/session protections and source access still apply; withdrawn evidence withholds affected interpretations and figures. The attachment uses `Cache-Control: no-store`; errors retain the JSON envelope. No digest job, automatic delivery, new model summary or schema table is introduced.

## Financial performance (migration 014)

The workspace response adds `performance` for SEC companies, or null for recorded scenarios. Available data includes immutable `snapshot_id`, `payload_id`, method, first-recorded and latest checked timestamps, source status, limitations and independently selected `reports.annual` / `reports.quarter`. Each report has accession/form/publication/end/filing URL and fifteen metric rows with exact decimal strings, units, input dates, source inputs, optional same-filing comparison and missing reason. No request or mutation occurs during GET. Existing explicit SEC refresh transaction creates/reuses the financial snapshot. Source withdrawal returns `status=unavailable` and no reports. No private fields or model call is introduced.

## Valuation scenarios (migration 015)

- `GET /api/v1/companies/{instrument_id}/valuation`: available reference rows plus the current owner's saved-comparison index.
- `POST /api/v1/companies/{instrument_id}/multiples/refresh`: one explicit bounded Finnhub basic-financials check; no automatic source/model work on reads.
- `POST /api/v1/valuation/preview`: company UUID, current `performance_id`, title, `method` (`earnings` or `sales`), integer `years` 1–5, positive `growth_step`/`margin_step` up to 50 and one to three named cases. Each case has decimal growth (−100 to 200), positive multiple (up to 200), rationale, optional `reference_id`, and net margin (−100 to 100) for earnings only. No inferred annualisation. Returns assumptions, pinned source packet and deterministic results/sensitivity, without persistence.
- `POST /api/v1/valuation/save`: the same body plus UUID `request_id`. Recomputes and saves atomically; an identical repeated request returns its prior record, changed-body identity conflicts, and a changed current financial base conflicts.
- `GET /api/v1/valuations/{id}` and `GET .../{id}/export`: exact owned saved record or inert HTML attachment. Source withdrawal withholds source/derived values, not recorded user assumptions. Old source values survive later corrections. JSON routes retain the normal envelope and local-session protections; downloads are no-store attachments.
