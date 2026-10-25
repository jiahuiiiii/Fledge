import { formatTimestamp } from "../lib/dateTime";
import { useState } from "react";
import { targetRange } from "../lib/targetRange";
import TargetChart from "./TargetChart";
import { Button, Card, Disclosure, SectionHeader } from "./ui";
import "./AnalystTargets.css";

const date = (value) => formatTimestamp(value, { fallback: "Not recorded" });

export default function AnalystTargets({ value, quote, bars = [], onRefresh }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const record = value?.snapshot;
  const data = record?.data;
  const range = targetRange(data?.targets, quote);
  async function refresh() {
    setBusy(true);
    setError("");
    try {
      await onRefresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Card className="analyst-targets" aria-label="Analyst price targets" aria-busy={busy}>
      <SectionHeader
        level="section"
        as="h2"
        title="Analyst price targets"
        description="Published 12-month targets: opinions, not predictions or a probability range."
        actions={
          <Button size="sm" disabled={busy || !value?.available} onClick={refresh}>
            {busy ? "Checking targets…" : "Update data"}
          </Button>
        }
      />
      {data ? (
        <>
          {range ? (
            <TargetChart bars={bars} range={range} />
          ) : (
            <p className="financial-note">
              The saved target range is incomplete or inconsistent. Refresh to check the source.
            </p>
          )}
          <p className="fine target-source">
            <a href={data.url} target="_blank" rel="noreferrer">
              {data.publisher} ↗
            </a>{" "}
            · {data.polled_analysts} analysts · fetched {date(record.retrieved_at)}
            {record.stale && " · over a day old, update before comparing with today’s price"}
          </p>
          <Disclosure variant="flush" title="Source details and limits">
            <p className="fine">
              {data.provider}. {data.page_updated_on && `Source page updated ${data.page_updated_on}. `}
              Potential change is measured from the retrieved quote, excluding dividends. Individual target dates are not supplied. The poll count is not a verified count of contributors; the low target is not a suggested entry price. Refresh is manual, once per company every 24 hours, and uses no AI credits.
            </p>
          </Disclosure>
        </>
      ) : (
        <p className="target-empty">
          {value?.available
            ? "Load the public analyst range for this company. Your scenario assumptions stay unchanged."
            : "This target source is unavailable. You can still build a scenario below."}
        </p>
      )}
      {(error || value?.refresh?.error) && (
        <p role="alert" className="form-error">
          {error || value.refresh.error}
        </p>
      )}
    </Card>
  );
}
