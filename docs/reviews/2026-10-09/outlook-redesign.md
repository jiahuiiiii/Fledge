# Outlook redesign — 9 October 2026

The owner asked to redesign Outlook first after the wider company-page improvements. Outlook now leads with original company guidance, followed by analyst forecasts and an expandable news-expectations reading.

## Presentation and retained behaviour

`OutlookPage` is lazy-loaded and retained across tab navigation. Company guidance has larger figure cards, distinct release/target dates, and an Evidence dialog for each exact original passage and raw value. SEC acceptance and first saved time remain separate from the release’s own dateline. The saved-release selector, historical-version notice, withdrawn/earlier-guidance notice, source errors, existing actual-result comparison and missing-input reasons remain. Longer context, release details and comparison rules start collapsed.

`AnalystForecasts` separates FMP from Stock Analysis/S&P Global. Both use `ForecastRange` cards with a prominent average, labelled low/high endpoints and an average marker within that individual range. The ranges have independent scales; they are not a comparison between metrics or providers. Negative and zero values remain valid; missing endpoints suppress the plotted range; identical bounds put the marker in the middle. Original public display strings and exact saved decimals remain inspectable. No currency, earnings convention, growth calculation, forecast accuracy judgement or combined consensus is inferred.

Currency uncertainty and public adjusted-EPS meaning remain visible. The public annual analyst total stays outside the cards and is not treated as the count for each metric. Observation time, source-page update, unknown underlying forecast date, restricted years, stale/error states and immutable saved observations remain available. A disabled public check shows its next permitted time. Public source withdrawal hides both the current values and history, even if a retained-looking response is supplied. Existing refresh callbacks, pacing, permissions and private peer-editor safeguards are unchanged.

Expectations reported in news start collapsed. Expansion and the mounted reading survive tab navigation; a company change still unmounts the page. Opening the disclosure does not submit an extraction. Saved-reading selection, exact source inspection, export, cached extraction, failure retention and drafting a research question retain the original workflow and explicit AI action.

Colours, text sizes and radii use the existing design tokens. Desktop cards use two columns; phones use one. Keyboard selection, Evidence dialog Escape/focus return and reduced motion remain supported.

## Verification and installation

All 50 current frontend checks, the production build, formatting of changed frontend files and browser-script syntax checks pass. No backend suite was rerun for this frontend change.

Two guarded disposable browser journeys pass against the final candidate. The business journey covers guidance evidence, release history and the existing result comparison, forecast ranges, zero/negative/missing values, withheld public values/history, collapsed news navigation, private peer draft/save/discard protection, keyboard controls and reduced motion. Outlook layouts are checked at 1440/980/390/320px; the broader business journey also retains its 1600px checks. The saved-expectations journey covers history, exact source inspection, inert export, draft without save, cached extraction and failure preserving the saved reading at 1440/390/320px. External requests are blocked, and the decorative Microsoft logo is a controlled missing-image fixture.

Desktop and phone guidance/range screenshots were inspected. They contain authored fixtures, not actual Microsoft results or a new owner-authenticated main-browser inspection. Logs, candidate, source hashes and screenshots are in `.local/live-tests/outlook-redesign-20261009/`; the prior frontend and integration files are in `.local/backups/outlook-redesign-20261009/`.

The verified frontend was installed by an atomic index replacement, after checking that the installed index and tested source hashes had not changed. Older assets remain available. The served index, all 18 candidate assets/font/attribution files and session HTTP 200 (`local-pitch`) were verified. Installed index SHA-256: `bd831995f6d8c849167608bed6b271cbec6dd5d67514116702e52ca887854442`. No server or database restart, owner application write, provider/model request or Telegram dispatch was performed by this task. The existing concurrent price-refresh work was preserved; this report makes no new claim about its backend installation or behaviour. No fresh whole-database fingerprint or global ledger audit was performed.

Keep the failed initial multi-operation CSS patch, initial small analyst-average typography and its corrected preview, and the two first saved-expectations test failures. The first used an ambiguous Research question label that also matched the retained question selector; the second counted a blocked decorative-logo request as unmocked egress. The corrected test targets the draft textbox and mocks that logo. Final runs pass. The final build retains a just-over-500-kB entry-chunk warning; the warning threshold was not raised. Operational inspection mistakes and original logs remain in the session/evidence. No failed candidate was installed.

The earlier four-part research goal, forecast-access limits, FMP denials, Alpha shared controls and provider/AI allowances are unchanged. This is a presentation improvement, not a new financial-data or independent usability-validation result.
