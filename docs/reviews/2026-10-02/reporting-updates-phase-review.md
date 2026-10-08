# Report changes that sentiment alone misses — phase 25

2 October 2026. Parent-authored five-perspective review, not an independent panel or participant study. This addresses the user's priority of useful alerts and news/social analysis within the local pitch MVP.

## Finding and implemented change

Reviewing the source-to-alert sequence exposed a delivery gap: an explicitly linked clarification, completion or contradiction could be neutral or favourable, so the company rule omitted it unless a directional aggregate reversed. The app could show an adverse original report while leaving the later clarification silent.

Company watches now include cited updates to an exact earlier report they actually saw. `adds_detail`, `contradicts` and conservative numeric/status-wording changes qualify without an adverse-tone requirement. These reports share the existing grouped reporting alert with other new adverse news. Both source passages and dates are inspectable in the alert and weekly export. A comparison is not proof that either report is true or that a formal correction occurred.

Freshness, exact and semantic-repeat suppression, current source access, owner isolation, revision history and review independence remain in force. An unseen comparison-only source does not establish prior watch history. No schema, classifier prompt, model or provider change is needed. The existing private saved-reasoning watch remains separate; this rule adds no duplicate company stream to that mode.

## Evidence

Evidence directory: `.local/live-tests/reporting-updates-20261002T085233Z/`.

The initial authored regression produced **seven failures and one pass** before the change. It reproduced missed neutral/favourable details and contradictions, missing earlier-report evidence and omitted guarded status changes. A later assertion correction changed an overly exact title substring check, not the expected alert behavior. The retained logs distinguish those failures.

An offline before/after replay froze five existing source/model comparisons from the phase-19 v4 retest. Three contain actual Microsoft reporting; two are explicitly authored fixtures. The candidate does not relabel the stored model output or make another API call. It constructs the preceding selected subset and whether the reference had been seen. This is a delivery-rule exercise, not a historical reconstruction or prospective latency measurement.

| Saved comparison | Stored tone | Previous behavior | Revised behavior |
| --- | --- | --- | --- |
| Actual Microsoft executive departure, added context | Negative | Adverse alert, without the comparison | Same reporting group with both source passages |
| Actual Wells Fargo Microsoft note, added upside framing | Positive | No alert | Update to seen reporting with both passages |
| Actual Microsoft executive departure, added timing/reason | Negative | Adverse alert, without the comparison | Same reporting group with both passages |
| Authored planned launch followed by reported completion | Positive | No alert | Reported update, without claiming independent verification |
| Authored resignation rumour followed by denial | Neutral | No alert | Conflicting reports presented together |

All five retain a linked update when the earlier exact report is marked seen, none treats an unseen reference as watch history, and all five are quiet after the new report is seen. Three formerly silent cases now alert. Source quotations match their original passage IDs. The v4 classifications and comparisons are saved development outputs, not newly established classifier accuracy. Other links or missing events were not exhaustively evaluated.

The integrated authored sequence separately exercised the actual acquisition/persistence/classification interfaces with mocked transport, scheduled-check history, original alert review, neutral clarification, repeated cached checks, a failed source step, recovery and permission withdrawal/restoration. It preserves exactly two reporting alerts, independent review states and no extra model invocation on repeats/recovery. The download includes both source passages and withholds them after withdrawal.

## Verification and cost

- **541 backend tests** pass using both retained public SEC corpora; the final focused set passes 63 checks.
- Seven frontend checks and the production build pass. The new reporting-update browser journey passes at 320/390/1440px, including both source dialogs, review persistence and inert export. Phone/desktop screenshots were visually inspected.
- Source and model transports in routine tests are mocked; no live acquisition, new paid request, watch enrollment or external notification is part of this phase.
- Original cumulative budget remains **US$5.071161 confirmed + US$0.13926 maximum hold**, with **US$4.789579 remaining** and 151 calls. The original interrupted call's actual charge is still unsettled.

## Five-perspective review

| Perspective | Assessment | Next concern |
| --- | --- | --- |
| Product | Fixes an asymmetric experience where bad news could alert but its clarification did not | Whether the added reports deserve attention still depends on user questions and source quality; alert volume is not value |
| UX | Seeing both passages explains why a neutral item produced an update; old and new reviews remain separate | Three update sections expose the system's separate streams and make the page long; a clearer combined review inbox is the next useful presentation improvement |
| Engineering | Reuses existing comparison, deduplication, schema and source-permission contracts | A whole consumed packet can become withheld after one source loses access; historical alerts must not silently disappear or reveal derived text |
| Research | Frozen actual-output replays identify a concrete delivery failure beyond classifier labels | Semantic linking remains an AI judgment. Numeric/status guards are conservative text checks, not proof of a correction. Broad recall and detection delay remain unmeasured |
| Business | This change requires no additional supplier, API key or model spending | It strengthens a pitch demonstration, not evidence of subscription demand or cost per retained customer |

The full plan remains incomplete. Participant comprehension/return value, broader social/news coverage, structured expectations and remaining financial/valuation capabilities are still unresolved. Production hosting, billing and external messaging remain outside current scope.


## Installed verification

Backup: `.local/backups/phase25-reporting-20261002T085818Z/`. Installation preserved every preexisting database row and private configuration value. The installed code reproduces the five candidate replay results exactly. The original sentiment browser journey also passes, and the running main workspace retains its saved NVIDIA sample and source-coverage warning. Main-account ideas, watches and publications are unchanged; watches remain off, so no demonstration alert was inserted into the user's research. Spending remains unchanged. `installed-final-verification.json` records installed source hashes, state checks and retained evidence.
