# Thesis UI directions

Updated 1 October 2026. **The user rejected all three initial directions.** They described them as generic and too similar to an editorial/New York Times experience, and asked for reference to TradingView and a supplied dark trading-interface screenshot. The direction is now a compact research workspace; the user subsequently accepted the recommended **Terminal structure + Radar evidence cards** combination and asked us to build it.

## Revised directions

| Direction | Composition | Reference relationship |
| --- | --- | --- |
| Terminal | Large price/volume chart, compact symbol strip, news/fundamentals panel, persistent thesis and evidence inspector, watchlist | Closest to the chart-centred TradingView direction |
| Radar | Company/event cards with compact price context, feed filters, persistent thesis conditions and selected-evidence inspector | Closer to the supplied dark card/feed screenshot |

Both use near-black surfaces, sans-serif typography, restrained borders and colour, compact financial values and visible source access. They are structural redesigns of the workspace, not recolours of the previous article-like screen. The dark appearance is an exploration of the user's supplied reference; it does not establish a permanent dark-only product requirement.

The Terminal preview supports range changes, candlestick/line switching, chart inspection, news/fundamentals switching, watchlist removal/re-addition and linked evidence selection. Radar supports feed filtering and linked evidence selection. Both support source expansion and review/undo without changing the assessment. These interactions remain local demonstrations.

Reference: the user-supplied dark trading-interface screenshot and [TradingView's official feature overview](https://www.tradingview.com/features/), consulted 1 October 2026 for its chart, fundamentals, watchlist and alert concepts. The visual reference does not authorize adding trade execution, copying brand assets, leaderboards or fabricated performance claims.

All prices, candle/volume data, company names, reports and news excerpts in the revised previews are synthetic. Northstar's 12% revenue growth and 22% operating margin reuse the previous fictional case. A second example user condition, operating margin of at least 20%, illustrates a mixed assessment; neither threshold is an investment recommendation. A sample news report with no company confirmation exercises the uncertainty state. Chart co-occurrence does not establish news causality.

The original pair was presented in a named carousel. The user then accepted the recommendation to combine Terminal structure with Radar cards, a smaller chart and more space for evidence and reasoning. The local app now implements that combination in `frontend/`. Its functional verification is recorded in [implementation status](../status/implementation-status.md). Preview interactions such as review undo and multiple-symbol controls are not promises about the bounded first release.

Verification of the revised previews: both were checked at 320, 358, 736 and 1024 pixels. No horizontal overflow, missing icons or browser script errors were found. Chart range/type, research tabs, watchlist controls, evidence selection, feed filtering, source expansion and review/undo passed local interaction checks. This is preview verification, not application integration or investment-quality validation.

## Initial directions — rejected

The following remain historical design explorations, not current implementation options.

| Direction | Visual and interaction character | Best fit to test | Tradeoff |
| --- | --- | --- | --- |
| Fieldnotes | Warm editorial typography, a research notebook layout, a readable narrative with evidence in the margin | People who want to think through an idea calmly | Less compact for frequent multi-company reviews |
| Clarity | Friendly spacing, rounded surfaces, a guided reading sequence and plain-language prompts | New investors who need help interpreting an update | Guidance can feel slow to experienced users |
| Signal | Precise workspace, compact navigation, side-by-side observations and evidence inspection | People already maintaining several company ideas | More information competes for a beginner's attention |

All three depict the same fictional Northstar Software update: quarterly year-over-year revenue growth falls from 18% to 12%, below an example user-set 15% condition; reported operating margin rises from 21% to 22%; no consensus comparison is available. These values and source excerpts are invented for design comparison. The threshold is not advice or a recommended investment rule.

The shared workflow is to read the original reasoning, inspect the change and source, and mark the update reviewed without changing the assessment. Source details and review acknowledgement work locally in the preview. Preview interactions do not create an account, connect a market feed or save application records.

The initial alternatives were shown in the conversation as a named carousel, with light/dark appearance and responsive layouts. A recorded carousel visit to Fieldnotes was navigation, not approval; the user's later explicit rejection takes precedence.

Whichever direction is selected, preserve source access, visible unknowns, mixed assessments, question-first entry, optional monitoring, accessible controls and an explicit distinction between evidence outcome and review acknowledgement.

Preview verification: all three directions were checked at 320, 358, 736 and 1024 pixels in light and dark appearance. No horizontal overflow or browser script errors were found. Source expansion, local reasoning edits, review acknowledgement and undo worked. These checks apply to the design preview only; no application/backend integration or investment-quality evaluation was performed.

## Full-screen implementation correction — 4 October 2026

The user subsequently identified uneven full-screen spacing and unstable shell placement. The application now fills the desktop viewport, keeps its navigation and bottom status bar in place, and gives the company/research/idea columns independent overflow. Company rows are grouped tightly; the chart, question and research panels share gutters, with deliberate larger breaks between sections. Phones retain document flow and sticky navigation. This updates the implemented layout, not the historical previews. See the [phase 61 review](../../reviews/2026-10-04/fullscreen-layout-phase-review.md) for screenshots and verification limits.

## Readability and contextual navigation — 4 October 2026

The user asked for less small text and clutter. Use readable main text and controls; remove duplicated explanations and disclose optional source metadata, methodology and settings only when opened. Keep concise source-problem indicators and source access apparent. In Updates, the company rail filters the inbox and remains synchronized with its company dropdown; it must not route to Workspace. Explicit research links retain navigation. See the [phase 62 review](../../reviews/2026-10-04/readable-inbox-phase-review.md).

## Consistent controls and stable navigation — 4 October 2026

Use app-rendered dropdown menus with dark surfaces, keyboard navigation and a subtle focus border. Keep the header and rails mounted when switching primary tabs; use skeletons where data is still loading. Company removal hides a sidebar item in this browser, with Undo/Restore, and preserves saved research and monitoring. See the [phase 63 review](../../reviews/2026-10-04/ui-interactions-phase-review.md).

## Shared company scope — 4 October 2026

A selected company follows every main tab. Sidebar and company-dropdown selection changes the company within the current view; explicit open-record/research links can change views. All companies clears the shared scope and displays aggregate lists/overview. The empty URL no longer silently selects a sample. See the [phase64 review](../../reviews/2026-10-04/shared-company-phase-review.md).

## Selective loading — 4 October 2026

Keep the header, company sidebar and grid mounted through company changes. Replace only loading research/idea content with static chart/card skeletons; each slower subsection handles its own pending read. Do not show the old company's actionable data beneath the new company heading. Preserve already-loaded lists on background refresh and offer retry when a read fails. The phase65 implementation supersedes the earlier company-keyed workspace remount. See the [review](../../reviews/2026-10-04/selective-loading-phase-review.md).

## Removal feedback — 4 October 2026

Place the reversible-removal notice directly below the header. Animate its natural-height expansion/collapse and reveal the green surface left to right. Keep named undo and close icon buttons grouped on the right, with visible keyboard focus. Honor reduced motion and make collapsed controls inert. [Phase66 review](../../reviews/2026-10-04/removal-animation-phase-review.md).

## Stable transitions — 4 October 2026

A new company uses one steady skeleton before its workspace/chart/active research inputs reveal together. Keep visited company panels mounted across tabs, retain chart controls, and revalidate saved reads without blanking matching content. Updates shares the same selected-company shell dimensions as Workspace/My ideas/History. Cold skeletons have a short minimum duration; errors finish immediately. This corrects the fast flashes and remounts missed in phase65. [Phase67 review](../../reviews/2026-10-04/stable-transitions-phase-review.md).

## Skeleton motion — 4 October 2026

The user now requests animated skeletons. Use a soft left-to-right shimmer across text bars and chart placeholders, without pulsing the full panel or moving its geometry. Disable the highlight for reduced motion. This supersedes the earlier static-only presentation; loading and retained-view behavior stay unchanged. [Phase68 review](../../reviews/2026-10-04/skeleton-shimmer-phase-review.md).
