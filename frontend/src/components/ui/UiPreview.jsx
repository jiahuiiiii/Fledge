import { useState } from "react";
import {
  Combobox,
  DisclosureGroup,
  EvidenceDialog,
  SourceChip,
  TrendTile,
  Disclosure,
  EmptyState,
  FilterGroup,
  MetaRow,
  Pagination,
  StoryCard,
  Badge,
  BookmarkIcon,
  Button,
  Card,
  ChartIcon,
  ChevronRightIcon,
  ExternalIcon,
  GridIcon,
  NewsIcon,
  PlusIcon,
  SectionHeader,
  TrashIcon,
  Field,
  Toggle,
  Select,
  Checkbox,
} from "./index";
import "./UiPreview.css";

// Preview of the shared UI parts, opened at /?ui-preview. Sample text only:
// it calls no API and shows no saved research.

const VARIANTS = [
  ["primary", "Main action on a screen. Use once per area."],
  ["secondary", "A second choice next to the main action."],
  ["tertiary", "Light actions in the accent colour."],
  ["plain", "Neutral actions such as Close or Cancel."],
];

function ButtonBoard() {
  return (
    <div className="ui-preview__grid">
      {VARIANTS.map(([variant, note]) => (
        <Card key={variant} variant="inset">
          <SectionHeader
            level="card"
            as="h3"
            title={variant}
            description={note}
          />
          <div className="ui-preview__row">
            <Button variant={variant} icon={<BookmarkIcon />}>
              Save
            </Button>
            <Button variant={variant} danger icon={<TrashIcon />}>
              Remove
            </Button>
          </div>
          <div className="ui-preview__row">
            <Button variant={variant} size="sm">
              Small
            </Button>
            <Button variant={variant} size="sm" disabled>
              Disabled
            </Button>
            <Button
              variant={variant}
              size="sm"
              icon={<PlusIcon />}
              aria-label="Add"
            />
          </div>
        </Card>
      ))}
    </div>
  );
}

function Badges() {
  return (
    <div className="ui-preview__grid">
      <Card variant="inset">
        <SectionHeader
          level="card"
          as="h3"
          title="Tone"
          description="An assessment. The shape keeps it readable without colour."
        />
        <div className="ui-preview__row">
          <Badge tone="positive">Positive</Badge>
          <Badge tone="negative">Negative</Badge>
          <Badge tone="mixed">Mixed</Badge>
          <Badge tone="neutral">No clear lean</Badge>
          <Badge tone="unknown">Not enough data</Badge>
        </div>
      </Card>
      <Card variant="inset">
        <SectionHeader
          level="card"
          as="h3"
          title="Status"
          description="A plain label with no judgement."
        />
        <div className="ui-preview__row">
          <Badge>Saved</Badge>
          <Badge status="info">Brief</Badge>
          <Badge status="accent">Watching</Badge>
          <Badge status="new">New</Badge>
        </div>
      </Card>
    </div>
  );
}

function Headers() {
  return (
    <Card>
      <SectionHeader
        level="page"
        as="h3"
        icon={<ChartIcon />}
        title="Page title"
        description="One sentence that says what this page is for."
        actions={<Button variant="primary">Main action</Button>}
      />
      <hr className="ui-preview__rule" />
      <SectionHeader
        level="section"
        as="h3"
        icon={<NewsIcon />}
        eyebrow="Small label"
        title="Section title"
        description="Optional description, kept to one line where possible."
        actions={<Button size="sm">Action</Button>}
      />
      <hr className="ui-preview__rule" />
      <SectionHeader
        level="card"
        as="h3"
        title="Card title"
        actions={
          <Button
            variant="plain"
            size="sm"
            icon={<ChevronRightIcon />}
            aria-label="Open"
          />
        }
      />
    </Card>
  );
}

function Cards() {
  return (
    <div className="ui-preview__grid">
      <Card>
        <SectionHeader
          level="card"
          as="h3"
          title="Panel"
          actions={
            <Button
              variant="plain"
              size="sm"
              icon={<PlusIcon />}
              aria-label="Add"
            />
          }
        />
        <p>
          The standard block. Fill separates it from the page, not a border.
        </p>
        <Card variant="inset">
          <p>An inset sits inside a panel for a quote, a figure or a note.</p>
        </Card>
      </Card>
      <Card>
        <SectionHeader level="card" as="h3" title="Flush rows" />
        <div>
          {["First row", "Second row", "Third row"].map((label) => (
            <Card key={label} variant="flush" as="button" interactive>
              <SectionHeader
                level="card"
                as="span"
                title={label}
                description="Rows in a list, divided by a line."
                actions={<ChevronRightIcon />}
              />
            </Card>
          ))}
        </div>
      </Card>
    </div>
  );
}

function Example() {
  return (
    <div className="ui-preview__grid">
      <Card>
        <SectionHeader
          level="card"
          as="h3"
          eyebrow="Example alert"
          title="Example Co. fell more than the market"
          actions={<Badge status="new">New</Badge>}
        />
        <div className="ui-preview__row">
          <Badge tone="negative">Negative</Badge>
          <Badge status="info">Price move</Badge>
        </div>
        <p>
          Sample text. The session move was larger than the comparison index.
          Two sources mention the same supplier update.{" "}
          <Button variant="tertiary" size="inline">
            Show the evidence
          </Button>
        </p>
        <div className="ui-preview__row">
          <Button variant="primary" size="sm" icon={<ExternalIcon />}>
            Open sources
          </Button>
          <Button variant="plain" size="sm">
            Dismiss
          </Button>
        </div>
      </Card>
      <Card>
        <SectionHeader
          level="card"
          as="h3"
          title="Example watchlist"
          actions={
            <Button variant="tertiary" size="sm" icon={<PlusIcon />}>
              Add
            </Button>
          }
        />
        <div>
          {[
            ["Example A", "positive", "Positive"],
            ["Example B", "mixed", "Mixed"],
            ["Example C", null, "Not enough data"],
          ].map(([name, tone, label]) => (
            <Card key={name} variant="flush" as="button" interactive>
              <SectionHeader
                level="card"
                as="span"
                title={name}
                actions={<Badge tone={tone}>{label}</Badge>}
              />
            </Card>
          ))}
        </div>
      </Card>
    </div>
  );
}

function ReadingParts() {
  const [filter, setFilter] = useState("all");
  const [page, setPage] = useState(1);
  return (
    <div className="ui-preview__grid">
      <div className="ui-preview__section">
        <FilterGroup
          label="Example story filters"
          value={filter}
          onValueChange={setFilter}
          options={[
            { value: "all", label: "All", count: 3 },
            { value: "company", label: "Company", count: 2 },
          ]}
        />
        <StoryCard
          title="Example company announces an expansion"
          href="https://example.com/"
          tags={<Badge>Company news</Badge>}
          meta={
            <>
              <span>Example Wire</span>
              <time dateTime="2026-10-25">25 Oct 2026</time>
            </>
          }
        >
          <p>
            Authored example text. The same story card presents company and
            world headlines.
          </p>
        </StoryCard>
        <Pagination
          page={page}
          totalPages={3}
          onPrevious={() => setPage((n) => n - 1)}
          onNext={() => setPage((n) => n + 1)}
        />
      </div>
      <div className="ui-preview__section">
        <Disclosure
          title="Inspect evidence"
          description="Saved excerpts and original sources"
        >
          <MetaRow>
            <Badge>EXMP</Badge>
            <span>Example source</span>
          </MetaRow>
          <p>
            Native keyboard-accessible disclosure. Reading it makes no request.
          </p>
        </Disclosure>
        <EmptyState
          title="No updates in this view"
          description="Choose another filter to continue."
          actions={<Button variant="tertiary">Show all</Button>}
        />
      </div>
    </div>
  );
}

function SharedPickers() {
  const [open, setOpen] = useState(false);
  const [picked, setPicked] = useState("");
  return (
    <div className="ui-preview__grid">
      <div className="ui-preview__section">
        <Combobox
          label="Example peer search"
          placeholder="Search companies"
          options={[
            { value: "EXA", label: "Example Co", hint: "EXA" },
            { value: "SMP", label: "Sample Corp", hint: "SMP" },
          ]}
          onSelect={setPicked}
        />
        <p className="fine">Picked: {picked || "nothing yet"}</p>
        <TrendTile
          title="Revenue growth"
          value="12.0%"
          caption="Sample period"
          points={[1, 3, 2, 5, null, 6]}
          onOpen={() => setOpen(true)}
        />
        <SourceChip
          label="Example Wire"
          date="25 Oct 2026"
          href="https://example.com/"
        />
      </div>
      <div className="ui-preview__section">
        <DisclosureGroup>
          <Disclosure title="First detail">
            <p>Authored example.</p>
          </Disclosure>
          <Disclosure title="Second detail">
            <p>Authored example.</p>
          </Disclosure>
        </DisclosureGroup>
      </div>
      <EvidenceDialog
        open={open}
        onClose={() => setOpen(false)}
        title="Example evidence"
        rows={[
          {
            id: 1,
            label: "Revenue",
            value: "US$1.0bn",
            meta: "Year to 30 Jun 2026",
            href: "https://example.com/",
            sourceLabel: "Annual report",
          },
        ]}
      />
    </div>
  );
}

function FormControls() {
  const [range, setRange] = useState("month");
  const [alerts, setAlerts] = useState(true);
  const [agreed, setAgreed] = useState(false);
  return (
    <div className="ui-preview__grid">
      <div className="ui-preview__section">
        <Field label="Reporting period" hint="Sample control, no data saved.">
          <Select
            value={range}
            onChange={(event) => setRange(event.target.value)}
            aria-label="Reporting period"
          >
            <option value="month">Past month</option>
            <option value="quarter">Past quarter</option>
            <option value="year">Past year</option>
          </Select>
        </Field>
        <Field label="Watchlist name" error="This name is already in use.">
          <input className="ui-input" defaultValue="Example list" />
        </Field>
      </div>
      <div className="ui-preview__section">
        <Toggle
          checked={alerts}
          onChange={setAlerts}
          label="Price-move alerts"
          description="Example toggle; changes nothing here."
        />
        <label className="ui-preview__check">
          <Checkbox
            checked={agreed}
            onChange={(event) => setAgreed(event.target.checked)}
          />
          <span>Show an authored example row</span>
        </label>
      </div>
    </div>
  );
}

const SECTIONS = [
  ["Buttons", ButtonBoard],
  ["Badges", Badges],
  ["Section headers", Headers],
  ["Cards", Cards],
  ["Form controls", FormControls],
  ["Put together", Example],
  ["Reading and evidence", ReadingParts],
  ["Pickers, trends and evidence", SharedPickers],
];

export default function UiPreview() {
  const [narrow, setNarrow] = useState(false);
  return (
    <main className="ui-preview">
      <div className={`ui-preview__frame${narrow ? " is-narrow" : ""}`}>
        <SectionHeader
          level="page"
          icon={<GridIcon />}
          title="Shared UI parts"
          description="Shared cards, controls and reading patterns. Authored examples only."
          actions={
            <Button
              variant="plain"
              size="sm"
              aria-pressed={narrow}
              onClick={() => setNarrow((value) => !value)}
            >
              Phone width
            </Button>
          }
        />
        {SECTIONS.map(([title, Body]) => (
          <section key={title} className="ui-preview__section">
            <SectionHeader title={title} />
            <Body />
          </section>
        ))}
      </div>
    </main>
  );
}
