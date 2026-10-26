import { useState } from "react";
import { stamp } from "./MarketResearch";
import AlertRating from "./AlertRating";
import AlertRoutingPreview from "./AlertRoutingPreview";
import { inboxSummary } from "../lib/inbox";
import { alertEvidenceRows, alertProvenance } from "../lib/alertEvidence";
import { Badge, Button, Card, EvidenceDialog, MetaRow } from "./ui";

const kindName = {
  idea: "Your saved idea",
  company: "Company news",
  condition: "Monitored condition",
  move: "Price move",
};
const reviewName = (action) =>
  ({ reviewed: "Reviewed", unresolved: "Left unresolved" })[action] ||
  "Awaiting review";

// One saved update: a compact summary, the review actions, and a flat
// evidence dialog with just the sources and the useful / not useful rating.
export default function InboxRecord({ record, busy, onOpen, onSource, onReview }) {
  const [open, setOpen] = useState(false);
  const d = record.detail;
  const summary = inboxSummary(record);
  const rows = alertEvidenceRows(record).map((row) => ({
    id: row.id,
    label: row.label,
    meta: `${row.source}${row.publishedAt ? ` · ${stamp(row.publishedAt)}` : ""}`,
    quote: row.quote,
    sourceLabel: row.url ? "Read original" : "View saved source",
    href: row.url,
    onOpen: () => onSource?.(row.source_obj),
  }));
  const canReview = !record.review_action && !d.withheld && d.published !== false;
  return (
    <Card
      as="article"
      className="inbox-record"
      data-kind={record.kind}
      data-record-id={record.id}
    >
      <MetaRow className="inbox-record-head">
        <Badge>{d.symbol}</Badge>
        <span className="inbox-kind">{kindName[record.kind]}</span>
        <time dateTime={record.created_at}>{stamp(record.created_at)}</time>
        <Badge status={record.review_action ? "neutral" : "accent"}>
          {reviewName(record.review_action)}
        </Badge>
      </MetaRow>
      <h3>{summary.title}</h3>
      <p className="inbox-preview">{summary.text}</p>
      {record.kind === "company" && d.preview && (
        <p className="fine">Preview · not sent to Telegram</p>
      )}
      {summary.source && (
        <p className="inbox-source-caption">
          {summary.source}
          {summary.publishedAt ? ` · ${stamp(summary.publishedAt)}` : ""}
          {summary.more > 0 ? ` · +${summary.more} more sources` : ""}
        </p>
      )}
      <AlertRoutingPreview record={record} />
      <div className="inbox-record-footer">
        <Button variant="tertiary" size="sm" onClick={() => setOpen(true)}>
          Inspect evidence
        </Button>
        {canReview && (
          <>
            <Button size="sm" disabled={busy} onClick={() => onReview(record.kind, d.id ?? record.id, "reviewed")}>
              Mark reviewed
            </Button>
            <Button variant="plain" size="sm" disabled={busy} onClick={() => onReview(record.kind, d.id ?? record.id, "unresolved")}>
              Leave unresolved
            </Button>
          </>
        )}
        {d.instrument_id && (
          <Button variant="plain" size="sm" onClick={() => onOpen(d.instrument_id, record.kind === "idea" ? "idea" : "workspace")}>
            Open {d.symbol} ↗
          </Button>
        )}
      </div>
      <EvidenceDialog
        open={open}
        onClose={() => setOpen(false)}
        title={`Evidence · ${d.symbol || kindName[record.kind]}`}
        intro={
          d.withheld
            ? "Source access changed. The evidence is withheld; your review history is kept."
            : null
        }
        rows={rows}
        empty="This update has no saved sources, only price data."
        footer={<AlertRating record={record} />}
        details={alertProvenance(record, stamp)}
      />
    </Card>
  );
}
