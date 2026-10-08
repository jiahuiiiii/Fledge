# Sentiment direction experiment — phase 51

**The candidate was not installed.** Requiring separate positive and negative quotations made the classifier's choices easier to inspect, but reduced matching of the original 34 selected tone criteria from **30 to 29**, and a new authored control response failed validation. The main app retains sentiment method `thesis-source-sentiment-10`, its original saved research and schema 29. Phase 50 weekly reviews remain installed.

## Experiment and intended purpose

The user prioritizes news/social sentiment and useful alerts. Phase 47 still had a missed spending warning, a buyback labelled favourable without the required explicit direction, a plain question labelled unclear and a technical description interpreted as criticism. The candidate `thesis-source-sentiment-11` tested a different output contract: require exact positive/negative excerpts from the item's selected current passages, validate the label against those sides, and show them separately with supporting context. Mixed required both sides; a past attitude or parent-only quote could not supply a current direction.

The candidate also removed a contradictory parent-context instruction that made plain questions unclear even when their meaning was intelligible. It retained the same model, medium reasoning, 9,000-output ceiling, source packets, grouping policy, one-call route and original US$20 ledger. There was no source acquisition or automated publication.

The initial schema exceeded the existing 64,000-byte request bound. Sharing identical enums and removing nonessential schema titles/default metadata made all five frozen requests fit, without dropping sources or increasing limits. The final sizes ranged from 29,133 to 62,935 bytes. Source-specific nested schemas and shared references use the official [Structured Outputs contract](https://developers.openai.com/api/docs/guides/structured-outputs). All five paid requests completed at the provider; one was rejected by the application validator.

## Frozen cases and outcomes

The original Microsoft, NVIDIA, Amazon and fictional phase-47 packets and their criteria remained unchanged. A separate sixteen-item fictional contrast packet covered routine actions versus explicit effects, plain versus evaluative questions, technical descriptions versus criticism, current/past views, parent/child ownership, counterparty effects and negation. These are agent-authored labels and reviews, not an independent benchmark or participant study.

| Packet | Accepted result? | Original selected tone criteria | Findings |
| --- | --- | --- | --- |
| Microsoft | Yes | 8/10, previously 9/10 | The spending warning is now mixed, but two routine departure reports gain negative/mixed labels. |
| NVIDIA | Yes | 9/11, previously 10/11 | The buyback remains positive; a multi-company roundup now assigns general industry framing to NVIDIA. |
| Amazon | Yes | 4/4, previously 4/4 | Selected criteria remain matched; the broader sample still warrants interpretation review. |
| Original fictional controls | Yes | 8/9, previously 7/9 | The plain benchmark question is now neutral; the technical security description remains negative. |
| New fictional direction controls | **No** | All 16 raw tone values match, but there is no accepted result | One item places the same explicitly negative phrase in both positive and negative evidence. The response is rejected rather than silently repaired. |

The accepted four packets contain **51 items** and match **29/34** original criteria. Across all five raw responses there are **67 items, 60 exact directional excerpts, 133 current/earlier passage associations and 13 parent associations**. Exact matching does not prove polarity, target attribution or completeness. The fifth packet's raw label matches must not be counted as a successful structured result.

All original three current/past cases keep their intended directional label, but their current passage lists include earlier context and fail the original exact-separation criteria. Their new directional excerpts select the current attitude. This distinction is useful for diagnosis but does not retroactively turn the original criterion into a pass. The same context inclusion occurs in the additional new-control transition.

Reviewing all 67 items, beyond the selected criteria, reveals further concerns: a technical security practice is treated as disapproval; comparative yield text is assigned negative tone; an ordinary operating agreement's purpose is treated as favourable evidence; and a mixed fictional sentence is duplicated broadly in the positive evidence. The NVIDIA roundup's industry-wide statements are particularly unsuitable as company-specific directional evidence. News-comparison prose is still a separately generated interpretation; the new quotation fields do not verify it.

## Engineering verification and non-installation

The candidate passes **977 isolated backend cases**, including all five retained actual-source corpora. A **102-case focused run** overlaps that suite. Fourteen frontend checks/build and current-sentiment/history browser journeys pass, including 320/390/1440px layouts, exact sources, watch controls, grouped alerts, acknowledgements and old-method warnings. The direction card was inspected at phone width. These are candidate checks, not a new installed-app test count or a semantic-quality pass.

The first focused run found an old authored clarification fixture whose tone changed without supplying the new evidence fields. Its fixture was corrected, preserving the existing scenario. The first history-browser launch failed because the temporary Chromium cache had disappeared; the same journey then passed with installed Chrome. Original failure logs are retained. Targeted undefined-name/syntax checks pass; a preexisting unused import was left unchanged in the frozen candidate.

No application source, frontend build, model profile, provider, migration or historical result was installed or replaced. The candidate's complete source, baseline source, changed files, evaluated source, frozen requests, original responses, test logs and screenshots are preserved locally. The working staging source was restored to the installed baseline after verifying that the candidate archive matched every restored file. This avoids accidentally shipping the unsuccessful contract in a later phase.

## Five-perspective review

These are five perspectives by the implementation agent, not independent consultant signoff.

| Perspective | Review and decision |
| --- | --- |
| Product | Improved traceability is insufficient if routine events acquire extra directional labels. Keep the current classifier until an alternative shows a defensible improvement under the same criteria. |
| UX | Separate favourable/adverse wording makes mistakes visible and the phone card remains compact. Those headings also sound more decisive, so exposing them with worse classification would not be an overall improvement. |
| Research/ML | A schema guarantees permitted structure and exact text, not the meaning of that text. The retained-case regression and contradictory new control are direct evidence against promoting this candidate. |
| Engineering | Source-bound evidence, immutable old records, current source permissions and the existing cost cap work. Preserve the reusable experiment rather than loosening validation or expanding limits merely to obtain green results. |
| Business | Five calls cost US$0.577065. The experiment prevents a misleading release, but establishes neither better alerts nor willingness to pay. More output fields also consume tokens without demonstrated quality benefit. |

The next sentiment experiment should isolate company/author/time attribution and the difference between explicit framing and inferred business consequences before adding another display layer or generic checker. Use unchanged real-source controls and genuine positive/negative cases so reducing false positives does not simply flatten all sentiment. Do not silently broaden labels or alter the frozen criteria to claim a win. Other implementation-plan gaps remain available for continued work; this result is not an impasse or completion of the goal.

## Evidence, preservation and cost

Evidence is under `.local/live-tests/sentiment-direction-20261003T105040Z/`. `baseline-source.tar.gz`, `candidate-source.tar.gz` and `candidate-changes/` preserve reproduction material without credentials; `frozen.json`, call/result/failure files and `counts.json` preserve the original evaluation. No evaluated result was published in the product. All protected records and watch settings remain exact, all source and weekly-review schedules remain off, and schema remains 29.

Five paid requests cost **US$0.577065**. The same cumulative **US$20** ledger now contains **US$12.759387 confirmed**, **US$0.301565 retained historical maximum accounting**, **US$6.939048 available**, **268 calls**, and no new blocking unresolved charge. Both historical ambiguous-call rows retain their original unresolved status and separate maximum-accounting decisions. No automatic retry or additional allowance was introduced.
