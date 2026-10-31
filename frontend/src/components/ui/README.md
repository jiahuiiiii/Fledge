# Shared UI

Import components from `./ui` (or `../ui` from a nested component). Use the
existing design tokens rather than adding page-specific colours or corners.
The authored gallery at `/?ui-preview` demonstrates the parts without reading
saved research. These components render presentation only; their callers own
requests, permissions, selection, dates and mutations.

| Component | Use |
| --- | --- |
| `Card` | `panel` for a main surface, `inset` for supporting content, `flush` for divided rows. Supports `as` and keyboard-accessible link/button surfaces. |
| `SectionHeader` | Page, section and card headings. Use `as` to preserve the document heading order. |
| `Button` | Primary, secondary, tertiary and plain actions; `href` renders a link. Icon-only actions require a label. |
| `Badge` | Status or tone. Tone shapes can be omitted with `shape={false}` when the label is sufficient. Unknown data must stay unknown. |
| `Tabs`, `TabsList`, `TabsTrigger` | Horizontal line-style navigation with arrow keys, Home/End and one tab stop. The caller owns the labelled panel and retained view. |
| `Disclosure` | Native `details` with title, optional description and a chevron. Accepts `open`/`onToggle` for controlled or lazy-loaded content. A rich `summary` can replace the default title block; set `indicator={false}` if that summary has its own indicator. Nested toggle events bubble: check `event.target === event.currentTarget` before starting work. |
| `FilterGroup` | Single-choice pressed buttons, using `value`/`onValueChange`. Options have `value`, `label`, optional `count`, `icon`, `ariaLabel`, `title` and `disabled`. Counts remain absent when unknown. These are filters, not tabs. |
| `MetaRow` | A wrapping row of source, time, company and status metadata. Supply semantic `time` elements and the app's Singapore display formatting at the call site. |
| `StoryCard` | Exact supplied headline, metadata, optional tags, text and footer. `href` opens the original; `onOpen` opens an existing evidence dialog. It never invents a summary. Callers apply any bounded preview while retaining full evidence. |
| `EmptyState` | A concise heading, explanation and optional existing actions. Keep loading, failed reads, withdrawn evidence and an actual empty result distinct. |
| `Pagination` | One-based page display and previous/next controls. Callers retain their original zero-based page/cursor and availability cutoff. |
| `Field` | A label, its control and an optional hint or error, wired together for assistive technology. Wrap one control; `Field` injects id, `aria-describedby`, `aria-invalid` and required state. The caller owns value, change and validation. |
| `Toggle` | One on/off switch: a native checkbox with `role="switch"`, a styled track and an optional label/description. `onChange(checked, event)`. Use `compact` for the label-less form with an `aria-label`. For a choice among options use `FilterGroup` or `Tabs`, not a row of toggles. |
| `Modal` | Portal dialog with Escape dismissal, focus trap and restored focus. Canonical version of the existing component. Callers own open state, title and actions. |
| `Select` | Native `select` value/change/form semantics with an owned popup and full keyboard interaction, so the system menu never replaces the app's options. Pass `<option>` children. |
| `Checkbox` | A native checkbox kept for keyboard, form and assistive-technology behaviour, with the app's check mark. Spread input props. |
| `Skeleton` | Loading placeholder with `cards`, `workspace`, `financials`, `chart` and `idea` variants. Keep it distinct from empty and failed states. |

Use quiet filled surfaces and compact headings. Do not add ornamental left-edge
borders or duplicate status/cost explanations. Keep original text and dates,
uncertainty and meaningful action availability near the reading. Paid, refresh,
review and watch actions must remain explicit; composing UI parts never starts
them. Support 320 px layouts, visible keyboard focus and reduced motion.
