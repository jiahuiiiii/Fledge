import { useState } from "react";
import {
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

const SECTIONS = [
  ["Buttons", ButtonBoard],
  ["Badges", Badges],
  ["Section headers", Headers],
  ["Cards", Cards],
  ["Put together", Example],
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
          description="Card, section header, badge and button. Sample text only; nothing here reads your saved research."
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
