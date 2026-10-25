# Shared UI parts — 25 October 2026

Outside feedback said the site feels inconsistent and has redundant components.
This adds four shared parts and a preview page. No existing page uses them yet.

## Audit before the change

Counts come from pattern matching over `frontend/src` CSS and JSX, so treat
them as close estimates.

| Area | Finding |
| --- | --- |
| Cards | About 78 bordered, rounded boxes with 37 paddings and 11 backgrounds; about 25 separately named card classes. `.evidence-card` is overridden about seven times. |
| Line colours | `--line` (#263043, 71 uses) and `--color-line` (#273142, 164 uses) look the same but are separate. |
| Badges | About 12 pill/tag/status styles with mixed shapes and weights. `.sentiment-tag` is defined three times differently. |
| Tone words | positive/negative/neutral, good/bad/mixed/none and positive/caution are all in use. The ▲▼◆● map is copied in `BeginnerSummary.jsx` and `PortfolioRead.jsx`. |
| Headings | 10 h1, 52 h2, 96 h3, 48 h4; each level is styled at 5–10 sizes, with about 42 header wrapper classes. |
| Buttons | 340 buttons, 170 without a class, styled by about 203 contextual `X button` rules; seven link-style button classes. |

Type sizes and radii already use `tokens.css` about 95% of the time, so the
drift is in component patterns rather than raw values.

## LifeForge UI

The owner preferred LifeForge UI's look. The package was not adopted: it is
CC-BY-NC-SA-4.0 (non-commercial, share-alike), needs React 19 (Fledge uses
18.3.1), and brings about 38 dependencies including Tailwind, daisyUI and
PocketBase. Only the design language was learned from its Storybook; no code
was copied.

Adopted from it: neutral surfaces separated by fill instead of borders,
matching corners on cards and controls, tinted icon tiles beside page and
section titles, and four button levels (primary, secondary, tertiary, plain)
each with a danger form. Not adopted: its low-contrast description text (about
2.5:1 on its dark cards) and its font. Fledge keeps MiSans Latin and its lime
accent.

## What was added

`frontend/src/components/ui/`: `Card`, `SectionHeader`, `Badge`, `Button`, a
small set of line icons, `ui.css` and `UiPreview`. The preview opens at
`/?ui-preview`; it is lazily loaded, calls no API and shows sample text only.
Because the root path is already served, it works in a production build too.

The `--ui-*` colours in `ui.css` are a proposal scoped to these parts, so the
rest of the app is unchanged. Migrated pages would temporarily sit next to the
older blue-tinted surfaces; switching the whole palette is a separate decision.

### Soft and Calm looks — Calm chosen

After seeing the first version, the owner asked whether it felt too cute. Both
looks were compared side by side in the preview, and the owner chose **Calm**.
Its values are now the only ones in `ui.css`; the Soft values and the look
switch were removed. The preview keeps a phone-width toggle.

| Setting | Soft (LifeForge-like) | Calm |
| --- | --- | --- |
| Corners: cards / buttons / badges | 12 / 12 px / full pill | 8 / 6 / 4 px |
| Button height: normal / small | 40 / 32 px | 36 / 28 px |
| Title / button weight | 700 / 600 | 600 / 500 |
| Page / section title | 30 / 20 px | 24 / 17 px |
| Icon tiles on card titles | Yes | No (page and section only) |
| Filled destructive button | Solid pink | Muted red tint |
| Badge tint | 16% | 12% |

Cards use tabular figures so numbers line up. `SectionHeader` ignores `icon`
at card level, so card lists stay quiet.

`Badge` maps good/bad/none to positive/negative/neutral. Any other value,
including a missing one, shows as unknown with a dashed outline rather than a
colour. `caution` from `financialStory.js` is deliberately not mapped yet.

## Verification

- `npm test`: 214 passed, 0 failed. Production build to a scratch directory
  succeeded; the preview is a separate chunk.
- Browser check of `/?ui-preview` on the Vite dev server: no console errors,
  no horizontal overflow at 320 px, focus ring visible on keyboard focus.
- Lowest measured text contrast on the preview is 6.25:1.
- Look switch (before removal): Soft, Calm and side by side rendered with the
  expected values, including two 320 px columns with no overflow.
- After making Calm the default: 214 tests pass, build succeeds, no console
  errors; measured 36 px buttons, 6 px button corners, 8 px card corners, 4 px
  badge corners, 24 px page title, no card-level icon tiles and no overflow.

## First migrated page: home company overview

`CompanyOverview` (the home "All companies" / "My companies" grid) now uses
`SectionHeader`, `Card`, `Badge` and `Button`.

- Heading: page-level `SectionHeader` with an icon tile; the old all-caps
  label is now sentence case; the company count is a `Badge`.
- Cards: `Card as="button"`; figures sit in an inset `Card` instead of between
  divider lines; the ↗ arrow is a chevron; "Open workspace →" lost its arrow.
- "Fictional sample" and "N to review" are `Badge`s instead of inline text.
- "Reload saved data" is a small secondary `Button`. In Beginner mode it is no
  longer rendered rather than hidden by CSS (same visible result).
- News tone stays plain text. The saved value is free text such as "positive
  leaning"; mapping it to a coloured tone badge would be inference.
- No values, calculations, dates or wording of figures changed.

CSS removed: the overview heading, card box, hover, divider and old figure
rules in `CompanyOverview.css`; the duplicate `.company-overview-tone` rules in
`ReadingFlow.css`; the Beginner `.company-overview-heading > button` selector
in `mobile.css`. Class names used by browser tests are kept.

Broad app rules were resizing the shared parts. `.app-shell button` (font size
and 38 px minimum height) and `.app-shell h3` now exclude `.ui-button`,
`.ui-card` and `.ui-section-header__title`. `SectionHeader` renders its label
and description as block spans so page `p` reading styles cannot resize them.

### Verification

- `npm test`: 214 passed, 0 failed; build succeeds; Prettier clean on changed
  files.
- Before/after screenshots were captured with headless Chrome from an isolated
  offline test server (`run.py --port 8843`, disposable `/private/tmp/thesis-browser-*`
  database seeded by `tests/seed_business_browser.py`, frontend built to a
  scratch folder). The live app, its database and `frontend/dist` were not
  touched; the test database was stopped by its exact path afterwards.
  Images are kept locally in `docs/reviews/2026-10-25/overview-screenshots/`
  and are not committed (the repository tracks no screenshots).
- After: Pro and Beginner at 1280 px and Pro at 390 px, no horizontal
  overflow; measured 12 px label, 24 px title, 28 px reload button, 8 px card
  corners; clicking a card opens the company.
- Limits: the seed has no saved prices, so cards show "Price unavailable";
  `browser_company_overview.cjs` was not run because Playwright is not installed
  here; keyboard focus on the cards was not confirmed in the hidden browser
  pane (they are native buttons).
- Palette: at this point the cards used neutral surfaces while the rest of the
  app was blue-tinted slate (resolved below).

## App-wide neutral palette

The owner chose to switch the whole app to the neutral palette so migrated and
older pages match. `tokens.css` now holds neutral greys and the `--ui-*`
colours in `ui.css` point at those tokens, so there is one palette.

| Token | Before (slate) | After (neutral) |
| --- | --- | --- |
| `--color-bg` | #0f141c | #0c0c0e |
| `--color-surface` / `-2` / `-3` | #171e29 / #1d2532 / #263043 | #18181b / #212126 / #2b2b31 |
| `--color-line` / `-strong` | #273142 / #3a4659 | #2e2e35 / #44444c |
| `--color-faint` / `--color-muted` | #7c889b / #a3aebf | #8a8a94 / #a1a1aa |
| `--color-text-2` / `--color-text` | #c9d1dd / #eef2f7 | #d4d4d8 / #fafafa |
| `--color-shadow` | #05080c | #050506 |

Accent, tone, info and chart series colours are unchanged. `--color-faint` was
lightened beyond a plain grey match so its contrast is at least the old value
on every surface (now 5.18:1 on cards, was 4.67:1). `--color-muted` contrast
falls slightly (6.91:1 on cards, was 7.47:1) and stays above 4.5:1.

Hard-coded slate greys were also replaced: the `var()` fallbacks in
`Onboarding.css` and `AccountGate.css`, the price chart's grid and axis greys
in `PriceChart.jsx`, and the browser `theme-color` in `index.html`.
`browser_company_overview.cjs` now expects the new `--color-surface-3` avatar
background, `rgb(43, 43, 49)`.

### Verification

- `npm test`: 214 passed, 0 failed; build succeeds; Prettier clean on changed
  files.
- Before/after screenshots of Home, Summary, Financials, News & discussion
  (1280 px, Pro) and Summary at 390 px, from the same isolated offline test
  server setup; no horizontal overflow before or after. Images are kept
  locally in `docs/reviews/2026-10-25/palette-screenshots/`, not committed.
- Not run: the Playwright browser journeys (Playwright is not installed here).
  `browser_workspace_motion.cjs` expects a row hover of `rgb(27, 39, 33)`,
  which matches neither the old nor the new `--color-surface-2`; it looks stale
  already and was left unchanged.

No live app restart was performed. The running app keeps its current look
until the frontend is rebuilt and installed.

## Installed into the running app

At the owner's request, commit `53a6f01` (without the uncommitted portfolio
edits) was installed into the running app with no restart: built from
`git archive HEAD` in a scratch folder, new assets copied into `frontend/dist`
with `cp -n` (151 old files kept, 19 added), and `index.html` replaced last by
an atomic rename. Port 8841 then served the new bundle; the previous bundle
still answered 200 for tabs already open.

## Second migrated page: Summary tab

`BeginnerSummary` (the Summary tab) now uses the shared parts for its four
section cards and titles, "Rate with AI" and "Write my view", the "All news &
posts", "Turn on news alerts" and "World news" links (chevron instead of →),
the inline "Get the latest news" and "Turn on Pro tools" buttons, count
numbers, and world-news effect tags. The effect tags map the saved
`could_help` / `could_hurt` / `mixed_or_unclear` values directly to positive /
negative / mixed tone badges; the wording is unchanged.

Kept as they were: the coloured signal lights and the tinted good/bad/mixed
group boxes (a recent teammate design), headline rows, and `.bs-card`,
`.bs-meaning`, `.bs-meta`, `.bs-note` and light rules, which `PortfolioRead`
still uses. The plain-language reading uses body size under card titles on
this page only.

`BeginnerSummary.css` went from 532 to about 365 lines: rules for 11 class
groups no component uses (`bs-hero`, `bs-oneline`, `bs-price`, `bs-list`,
`bs-head`, `bs-tone(s)`, `bs-chip`, `bs-effect`, `bs-why`, `bs-timeline`,
`bs-day`, `bs-more-row`) and the replaced `bs-more`, `bs-view`, `bs-count`,
`bs-effect-tag`, `.bs-link.inline` and `.bs-rate .primary` rules.

Shared `Button`s now measure 44 px on touch screens, matching the app's
existing touch rule; inline buttons get an invisible 44 px tap area so the
sentence layout does not move.

### Verification

- `npm test`: 214 passed, 0 failed; build succeeds. `BeginnerSummary.jsx` and
  `.css` already failed Prettier before this change and were not reformatted.
- Screenshots of Beginner at 1280 and 390 px and Pro at 1280 px from the
  isolated offline test server; no horizontal overflow. Images are kept
  locally in `docs/reviews/2026-10-25/summary-screenshots/`, not committed.
- Touch: in the browser pane's mobile mode (coarse pointer) every Summary
  button measured 44 px, and the inline "Turn on Pro tools" responds 18 px
  above and below its text.
- Not exercised: world-news effect badges and tone groups (the seed has no
  linked world headlines or rated stories), and the Playwright journeys.
