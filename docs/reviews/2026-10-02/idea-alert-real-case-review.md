# Actual-source relevance tests — 2 October 2026

These are developer-authored investment-research situations evaluated against actual stored Finnhub/Reddit sources. The reasoning is authored for testing, not a user's real investment position. Expected distinctions were recorded before paid requests. This is a small development review by the implementing agent, not independent accuracy measurement, investment advice or student validation.

## Cases and results

| Case | Intended distinction | Initial result and correction |
| --- | --- | --- |
| Microsoft, 11 text groups | Capital spending may pressure margins; bullish price targets do not establish paid Copilot adoption or actual revenue. Social economics arguments remain attributed opinion. | Margin concern and future-departure qualifications were preserved. One article saying revenue was needed was incorrectly called support for the user's evidence requirement. Prompt v2 changes it to context; two substantive challenges remain. |
| Apple, 8 text groups | Cost offsets may weaken earnings assumptions; an upcoming Health redesign is not realised sales. Identical substantive Health text counts once. | Cost-offset connections were useful, but a planned redesign was called support for the user's caution about unproven sales. Prompt v2 makes it context; two earnings-related challenges remain. |
| Alphabet, 10 text groups | Paid AI competition and litigation exposure differ from observed revenue or a damages award; social benchmark enthusiasm does not prove paid adoption. | Three substantive challenges and source qualifications were preserved. V2 said no damages had been awarded, exceeding what the supplied snippet establishes. Prompt v3 narrows this to “this is not an award.” |

Across the first 29 classifications, the eleven prewritten source-fidelity criteria matched the parent review, but two additional alert-noise failures were discovered. Both are preserved. The v2 retest met those original criteria plus the two additional context requirements. A further source-limitation wording concern prompted a targeted Google v3 retest; the other two v2 results were retained rather than silently relabelled as v3 tests. The final Google result meets the additional boundary. No automatic paid retry was used.

Only changes to the prompt required new provider calls. Repeating identical completed requests reused their records without another charge. The original source set was held fixed; these tests did not fetch fresh market data or establish prospective detection delay. Selected social posts came from r/stocks; unavailable feeds remain outside coverage. Exact quotations are checked separately from semantic interpretation.

## Local evidence

Private source packets, frozen cases, raw result records, cache checks and budget snapshots are under `.local/live-tests/`:

- `idea-alerts-v1-20261002T023225Z/`: three original paid calls and the two retained noisy supports.
- `idea-alerts-v2-20261002T023545Z/`: three corrective retests against the same cases, with all initial records preserved.
- `idea-alerts-v3-20261002T023845Z/`: targeted Google wording retest, final existing-demo UI check and verification/export records.

The original Google demo reasoning is left unchanged for the UI test. Its question asks for evidence of paid enterprise demand rather than asserting that a launch already proves it. A quiet result is acceptable and should remain inspectable in History.

## Existing demo correction

The original Google demo UI call returned two challenges to presumed AI optimism even though the saved words requested evidence before deciding. This is a retained semantic failure. Prompt v4 adds a separate risk-to-investigate category and prohibits inventing a stance. The old v3 check was marked unresolved, with its text and source evidence preserved. A targeted v4 Microsoft retest checks that an explicit no-margin-pressure belief can still receive a substantive challenge, while a new Google UI check tests the evidence-seeking case. The v4 evidence folder is `idea-alerts-v4-20261002T024442Z/`.

## Final outcome and accounting

The v4 Microsoft check retains two substantive challenges to its explicit margin expectation. The unchanged Google demo produces two **Risks to investigate**, with no supports/challenges to an invented stance. Its launch/benchmark post stays context. The result was generated through the actual app button and verified in Updates; the older v3 demo result remains unresolved in History. Main-owner watches are off.

The three selected final QA records cover 29 source/idea classifications and 58 exact source quotation associations: Microsoft v4 (11), Apple v2 (8), Google v3 (10). Their model/prompt versions are preserved. The final Google demo is an additional 10 classifications under v4. These are not 39 unique sources or an accuracy denominator. Each completed identical request was repeated from cache without another charge. Six actual-record baseline checks (twice per QA company) returned no new sources and made no model call; they do not simulate prospective arrival or establish detection delay. Private HTML examples and `verification.json` are saved in the v4 folder.

This phase used **ten paid requests**, including corrections, for **US$0.492515** confirmed. Total building-period accounting is **US$2.0708375 confirmed + US$0.13926 retained maximum hold**, 85 calls, US$7.7899025 remaining, no new unresolved charge. No automatic paid retry or new budget was introduced.

One minor wording limitation remains in the final Microsoft background explanations: they can refer to a reasoning-segment ID such as “r1”. The visible saved quotation supplies the context, but later wording polish should remove these internal identifiers. Broader source coverage, unseen-case precision/recall and student usefulness remain unverified.
