import LoadingSkeleton from "./LoadingSkeleton";
import { useEffect, useState } from "react";
import { api } from "../api/client";

const time = (value) =>
  value
    ? new Date(value).toLocaleString("en-GB", {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "Not scheduled";
const labels = {
  changed: "Filing inputs changed",
  unchanged: "Inputs unchanged",
  recent: "Recent attempt · no request",
  failed: "Check failed",
  interrupted: "Completion unconfirmed",
  running: "Checking filings",
};

export default function FilingWatch({
  instrumentId,
  watch,
  configured,
  busy,
  onChange,
}) {
  const [journal, setJournal] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  async function load(before = null) {
    setLoading(true);
    setError("");
    try {
      const result = await api.filingChecks(instrumentId, before);
      setJournal((old) => ({
        ...result,
        items: before ? [...(old?.items || []), ...result.items] : result.items,
      }));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    if (open) load();
  }, [watch?.next_check_at, watch?.lease_until, open]);
  const running =
    watch?.lease_until && new Date(watch.lease_until) > new Date();
  return (
    <section
      className="filing-watch financial-performance"
      aria-label="Daily filing checks"
    >
      <div className="financial-heading">
        <div>
          <span className="section-label">FILING MONITOR</span>
          <h3>Check financial results daily</h3>
        </div>
        <button
          disabled={busy || (!watch?.enabled && !configured)}
          onClick={() => onChange(!watch?.enabled)}
        >
          {watch?.enabled
            ? "Stop daily filing checks"
            : "Start daily filing checks"}
        </button>
      </div>
      <p>
        Checks SEC once when enabled, then every 24 hours while this local app
        runs. New supported figures reassess your approved numerical conditions
        and can appear in Updates. No AI credits are used.
      </p>
      <p className="fine">
        {watch?.enabled
          ? `${running ? "A check is in progress. " : "Daily checks on. "}Next scheduled: ${time(watch.next_check_at)}. An overdue check runs once after reopening.`
          : "Daily checks are off. You can still use Refresh research."}
      </p>
      <p className="fine">
        This checks structured annual and quarterly figures, not every filing or
        announcement. Stopping prevents future checks; an active check may
        finish. Annual figures cannot satisfy quarterly conditions.
      </p>
      {watch?.latest_check && (
        <div className="filing-check" role="status">
          <strong>{labels[watch.latest_check.outcome]}</strong>
          <p>{watch.latest_check.message}</p>
          <span className="fine">
            Last started: {time(watch.latest_check.started_at)}
          </span>
        </div>
      )}
      {!configured && (
        <p className="fine">
          A SEC contact identity is needed before enabling checks.
        </p>
      )}
      <details open={open} onToggle={(e) => setOpen(e.currentTarget.open)}>
        <summary>Daily filing check history</summary>
        <button disabled={loading} onClick={() => load()}>
          Refresh check history
        </button>
        {error && <p role="alert">{error}</p>}
        {loading && !journal && (
          <LoadingSkeleton
            variant="panel"
            rows={1}
            label="Reading saved checks…"
          />
        )}
        {journal?.items.length === 0 && (
          <p>No scheduled filing checks recorded.</p>
        )}
        {journal?.items.map((item) => (
          <article className="filing-check" key={item.id}>
            <h4>{labels[item.outcome]}</h4>
            <p className="fine">
              Scheduled {time(item.scheduled_at)} · Started{" "}
              {time(item.started_at)}
              {item.completed_at
                ? ` · Finished ${time(item.completed_at)}`
                : ""}
            </p>
            <p>{item.message}</p>
            {item.filing && (
              <a href={item.filing.filing_url} target="_blank" rel="noreferrer">
                Open {item.filing.form} filing · period ended{" "}
                {item.filing.period_end}
              </a>
            )}
          </article>
        ))}
        {journal?.next_before && (
          <button disabled={loading} onClick={() => load(journal.next_before)}>
            Older filing checks
          </button>
        )}
        <p className="fine">
          History records scheduled checks only. Manual refreshes appear in
          source coverage. Reading this history makes no source or AI request.
        </p>
      </details>
    </section>
  );
}
