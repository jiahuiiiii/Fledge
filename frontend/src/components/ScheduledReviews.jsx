import Checkbox from "./Checkbox";
import Select from "./Select";
import LoadingSkeleton from "./LoadingSkeleton";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import { stamp } from "./MarketResearch";
const weekdays = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];
const toDraft = (s) => ({
  enabled: s.enabled,
  weekday: s.weekday,
  time: `${String(Math.floor(s.minute_of_day / 60)).padStart(2, "0")}:${String(s.minute_of_day % 60).padStart(2, "0")}`,
  time_zone: s.time_zone,
});
export default function ScheduledReviews({ onSelect, selected }) {
  const [data, setData] = useState(null),
    [draft, setDraft] = useState(null);
  const [before, setBefore] = useState(""),
    [revision, setRevision] = useState(0);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [message, setMessage] = useState("");
  useEffect(() => {
    let active = true;
    const load = () =>
      api
        .scheduledReviews(before)
        .then((value) => {
          if (!active) return;
          setData(value);
          setDraft((old) => old || toDraft(value.settings));
        })
        .catch((e) => {
          if (active) setError(e.message);
        });
    load();
    const interval = setInterval(load, 30000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [before, revision]);
  const change = (key, value) => {
    setDraft((old) => ({ ...old, [key]: value }));
    setMessage("");
  };
  async function save(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const [hour, minute] = draft.time.split(":").map(Number);
      const value = await api.saveReviewSchedule({
        enabled: draft.enabled,
        weekday: draft.weekday,
        minute_of_day: hour * 60 + minute,
        time_zone: draft.time_zone.trim(),
      });
      setDraft(toDraft(value));
      setData((old) => ({ ...old, settings: value }));
      setMessage(
        value.enabled
          ? "Weekly review schedule saved."
          : "Weekly reviews are off. Saved reviews remain available.",
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function seen(id) {
    setBusy(true);
    setError("");
    try {
      await api.seeReview(id);
      setRevision((v) => v + 1);
      setMessage("Review marked seen. Individual alerts are unchanged.");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section
      className="scheduled-reviews"
      aria-label="Scheduled weekly reviews"
    >
      <div className="market-section-head">
        <h3>Weekly review</h3>
        <span className="status">
          {!data ? "Loading…" : data.settings.enabled ? "Scheduled" : "Off"}
        </span>
      </div>
      <p className="fine">
        A saved in-app summary of your existing updates. No new sources or AI
        calls. Keep the app running for delivery; after time away, it catches up
        with the latest week once.
      </p>
      {data?.settings.next_due_at && (
        <p className="fine">
          Next review:{" "}
          {new Intl.DateTimeFormat(undefined, {
            dateStyle: "medium",
            timeStyle: "short",
            timeZone: data.settings.time_zone,
          }).format(new Date(data.settings.next_due_at))}{" "}
          ({data.settings.time_zone}).
        </p>
      )}
      {data?.settings.error_message && (
        <p className="warning" role="status">
          {data.settings.error_message}{" "}
          {data.settings.retry_after &&
            `Next local attempt ${stamp(data.settings.retry_after)}.`}
        </p>
      )}
      <details className="review-schedule-options">
        <summary>Weekly review settings</summary>
        {draft && (
          <form onSubmit={save}>
            <label className="schedule-toggle">
              <Checkbox
                checked={draft.enabled}
                disabled={busy}
                onChange={(e) => change("enabled", e.target.checked)}
              />
              Enable weekly reviews
            </label>
            <div className="review-filters">
              <label>
                Day
                <Select
                  aria-label="Weekly review day"
                  value={draft.weekday}
                  disabled={busy}
                  onChange={(e) => change("weekday", Number(e.target.value))}
                >
                  {weekdays.map((d, i) => (
                    <option key={d} value={i}>
                      {d}
                    </option>
                  ))}
                </Select>
              </label>
              <label>
                Local time
                <input
                  aria-label="Weekly review time"
                  type="time"
                  required
                  value={draft.time}
                  disabled={busy}
                  onChange={(e) => change("time", e.target.value)}
                />
              </label>
              <label>
                Time zone
                <input
                  aria-label="Weekly review time zone"
                  list="review-time-zones"
                  required
                  maxLength={80}
                  value={draft.time_zone}
                  disabled={busy}
                  onChange={(e) => change("time_zone", e.target.value)}
                />
                <datalist id="review-time-zones">
                  {[
                    "Asia/Singapore",
                    "UTC",
                    "America/New_York",
                    "Europe/London",
                  ].map((z) => (
                    <option key={z} value={z} />
                  ))}
                </datalist>
              </label>
            </div>
            <button type="submit" disabled={busy}>
              {busy ? "Saving…" : "Save weekly schedule"}
            </button>
          </form>
        )}
      </details>
      {error && (
        <p className="warning" role="alert">
          {error}
        </p>
      )}
      {message && (
        <p className="fine" role="status">
          {message}
        </p>
      )}
      <div className="saved-weekly-list">
        {!data && !error && (
          <LoadingSkeleton
            rows={1}
            variant="panel"
            label="Loading saved weekly reviews…"
          />
        )}
        {data?.items.map((r) => (
          <article className="saved-weekly-item" key={r.id}>
            <div>
              <strong>Week ending {stamp(r.scheduled_at)}</strong>
              <p className="fine">
                {r.total} updates · {r.seen_at ? "Seen" : "Ready to review"}
                {r.skipped_occurrences > 0 &&
                  ` · ${r.skipped_occurrences} earlier scheduled weeks skipped`}
              </p>
            </div>
            <div className="sentiment-controls">
              <button
                aria-pressed={selected === r.id}
                onClick={() => onSelect(r.id)}
              >
                Open saved review
              </button>
              {!r.seen_at && (
                <button disabled={busy} onClick={() => seen(r.id)}>
                  Mark review seen
                </button>
              )}
            </div>
          </article>
        ))}
        {data && !data.items.length && (
          <p className="muted">
            No saved weekly reviews yet. You can review current records below.
          </p>
        )}
        {before && (
          <button onClick={() => setBefore("")}>Latest weekly reviews</button>
        )}
        {data?.next_before && (
          <button onClick={() => setBefore(data.next_before)}>
            Older weekly reviews
          </button>
        )}
      </div>
    </section>
  );
}
