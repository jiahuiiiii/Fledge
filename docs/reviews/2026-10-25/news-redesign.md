# News design and Pro tabs — 25 October 2026

News & discussion now uses the Overview/Summary shared `Card`, `SectionHeader`,
`Button` and `Badge` components. Latest headlines appear in three quiet cards
on desktop and stack on phones. Source/date metadata, exact supplied titles,
three-line snippets and original-story actions remain together. The optional
AI summary remains collapsed. Tone uses a shared panel and inset source cards,
labelled source filters and shared tone badges on analysed rows. Existing
counts, filters, pagination, source evidence and paid/watch actions retain their
original behaviour. The design layer is loaded after legacy global styles so
older report borders and control layouts cannot override it.

Pro navigation follows the [shadcn/ui line-tabs reference](https://ui.shadcn.com/docs/components/base/tabs#line)
using small reusable React primitives in `components/ui/Tabs.jsx`; no dependency
was added. The strip is horizontal at every width with a simple active
underline. Arrow keys wrap, Home/End select endpoints, only the selected tab is
in the normal Tab sequence, and Tab enters the labelled content panel. The
selected item is revealed within the strip on selection and resize, without
scrolling the page. The old phone fade is removed so it cannot obscure the
selected label. Retained views still preserve News filters and paging. Existing
Beginner and recorded-company tab choices are unchanged.

## Verification

- `npm test --prefix frontend`: 214 passed.
- `npm run build --prefix frontend`: passed; the existing warning for a main
  chunk larger than 500 kB remains.
- `tests/browser_news_redesign.cjs`: passed in installed Chrome against an
  authored static fixture. It builds and removes its own temporary fixture;
  it never starts the app or a database. All API and external requests are
  blocked; none were attempted. No browser errors.
- Browser checks cover widths 1440, 1024, 768, 390 and 320; horizontal line
  styling, active-tab visibility, keyboard wrapping/Home/End, focus entering the
  panel, source filtering/pagination retained across tabs, original evidence
  text, Escape/focus return, and empty/withheld/stale readings with disabled AI.
- Desktop and phone viewport screenshots were visually inspected. Initial
  full-page captures were unsuitable for this browser; final artifacts are
  viewport captures at the top of the fixture.
- `git diff --check`: passed.

Screenshots use fictional authored text, not saved owner research:
[desktop](news-screenshots/news-1440.png),
[390 px](news-screenshots/news-390.png),
[320 px](news-screenshots/news-320.png).

To rerun the standalone browser test, set `PLAYWRIGHT_MODULE` to an available
Playwright package and `CHROMIUM_PATH` to an installed Chrome/Chromium executable,
then run `node tests/browser_news_redesign.cjs`. It serves static files on a
random localhost port and closes that server afterwards.

These checks establish presentation and authored interaction behaviour, not
live provider/model quality or independent usability. No live settings,
research, app/database processes, migrations or paid calls were changed. Existing
unrelated working-tree edits were preserved; nothing was committed or pushed.
