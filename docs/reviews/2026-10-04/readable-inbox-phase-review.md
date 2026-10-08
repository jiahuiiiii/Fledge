# Readability and Updates filtering — 4 October 2026

## User request and implementation

The user expects selecting a ticker in Updates to filter updates for that company. The former sidebar called the default Workspace route. Shared inbox filter state now connects sidebar buttons with the existing dropdown. Company changes keep the review-status filter, reset page/cutoff and stay in Updates. An explicit All companies row resets the scope. Older in-flight responses cannot replace the current selection, and prior-company results are withheld while the new query is loading. Companies without an owned idea/watch get an empty inbox message with an explicit research-navigation button. The existing backend 404/access contract is unchanged; unrelated errors remain errors. Filter settings last for this inbox visit and reset on re-entry/reload.

The user also requested a less compact, less cluttered interface. Primary copy and controls now use 14px, secondary metadata generally 12px, and small chrome labels 11px. Repeated source-count, draft and sidebar slogans are removed. Quote retrieval details, stored-price metadata, daily-session inspection, advanced watch settings, private-check setup, sampling methodology and monitoring explanations are available through named native details. Historical checks and discussion themes follow the current sentiment reading. Stale/source-failure/earlier-method states have a visible combined summary with expandable explanations. Omitted-source disclosures retain a visible warning summary and their exact detail. Source quotations and saved model results are unchanged.

## Verification and limitations

- Production build, formatting of changed frontend files and 22 existing frontend tests pass.
- Seven disposable browser journeys pass: mixed-stream inbox; sentiment and independent alert reviews; chart ranges, keyboard sessions and source table; optional watch/context settings; private-alert scope and question focus; original-source reading; omitted-source disclosures. They use authored data/mocked providers and make no live provider call.
- Inbox checks compare exact API record identities, preserve status, reset page two to page one, synchronize both selectors, restore all companies, handle an empty company, and retain existing stale-response/outage/review/source-access cases.
- The initial new inbox check exposed the API's existing no-owned-idea/watch response. The UI now renders that specific response as an empty company scope. It does not fabricate a report or change access rules. The initial failed log is retained.
- Read-only layout checks pass at 2560×1440, 1920×1080, 1440×900, 1280×800, 1024×768, 800×900, 740×900, 390×900 and 320×900. Checks cover shell geometry, scrolling, navigation, source dialogs, readable main copy, collapsed defaults and expanded settings. Installed live-app company filtering is also checked without writes.
- Screenshots of the primary workspace, sentiment area and phone layout were visually inspected. This is Chrome verification, not a full assistive-technology or cross-browser audit.

No backend/schema/model changes, no user-research publication and no paid requests. The unchanged full backend suite was not rerun. Source/build backup: `.local/backups/phase62-readable-inbox-20261004T030107Z/`. Screenshots, installation hashes and logs: `.local/live-tests/readable-inbox-20261004T030107Z/`.

## Five-perspective review

One agent applied these perspectives; these are not independent consultant opinions or user validation.

| Perspective | Assessment |
| --- | --- |
| Product | Company selection follows the current task. Research navigation is an explicit action. |
| UX | Primary information is readable, with less repeated prose. Optional detail has named entry points instead of tiny text. |
| Engineering | Filter state has one owner; API permissions, history and request behavior are preserved. The specific empty-scope response remains covered by regression checks. |
| Accessibility/QA | Native disclosures and labelled controls remain keyboard accessible; narrow layouts and expanded states pass. Broader accessibility testing remains open. |
| Evidence/cost | Important coverage problems remain signposted and original evidence accessible. This UI pass adds no API spend and makes no accuracy claim. |
