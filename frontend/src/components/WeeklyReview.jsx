import { useEffect, useState } from "react";
import { api } from "../api/client";
import { dayLabel } from "../lib/beginnerSummary";
import { stamp } from "./MarketResearch";
import Checkbox from "./Checkbox";
import Modal from "./Modal";
import Select from "./Select";
import LoadingSkeleton from "./LoadingSkeleton";
import { Badge, Button, EmptyState, Pagination } from "./ui";
import "./BeginnerSummary.css";
import "./WeeklyReview.css";

const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const ZONES = ["Asia/Singapore", "UTC", "America/New_York", "Europe/London"];
const KIND = { company: "News", idea: "Your idea", move: "Price move", condition: "Condition" };
const TONE = { "Good news": "good", "Bad news": "bad", "Mixed news": "mixed" };

const toDraft = (s) => ({
  enabled: s.enabled,
  weekday: s.weekday,
  time: `${String(Math.floor(s.minute_of_day / 60)).padStart(2, "0")}:${String(s.minute_of_day % 60).padStart(2, "0")}`,
  time_zone: s.time_zone,
});

// Same grouping as the Overview news list: bad, price moves, mixed, good,
// then everything else. Each line is one saved update.
export function reviewGroups(records = []) {
  const groups = { bad: [], move: [], mixed: [], good: [], other: [] };
  for (const r of records) {
    const d = r.detail || {};
    const key = r.kind === "move" ? "move" : r.kind === "company" ? TONE[d.brief?.tone] || "other" : "other";
    groups[key].push({
      id: `${r.kind}:${r.id}`,
      headline: d.brief?.headline || r.title,
      why: d.brief?.why,
      meta: `${d.symbol || ""} · ${KIND[r.kind] || "Update"} · ${dayLabel(r.created_at)}`,
      instrumentId: r.instrument_id ?? d.instrument_id,
    });
  }
  return groups;
}

export function ReviewList({ groups, onOpenItem, limit = 4 }) {
  const row = (item) => (
    <li key={item.id}>
      <button type="button" className="bs-link" onClick={() => onOpenItem?.(item)}>
        {item.headline}
      </button>
      <small>{item.meta}</small>
      {item.why && <small className="weekly-why">{item.why}</small>}
    </li>
  );
  const group = (label, mood, list) =>
    list.length > 0 && (
      <div className={`bs-group tone-${mood}`} key={label}>
        <h5>
          {label} <Badge>{list.length}</Badge>
        </h5>
        <ul className="bs-headlines">{list.slice(0, limit).map(row)}</ul>
      </div>
    );
  return (
    <>
      {group("Bad news", "bad", groups.bad)}
      {group("Price moves", "none", groups.move)}
      {group("Mixed", "mixed", groups.mixed)}
      {group("Good news", "good", groups.good)}
      {group("Other updates", "none", groups.other)}
    </>
  );
}

export default function WeeklyReview({ open, onClose, onOpen, onChanged }) {
  const [list, setList] = useState(null);
  const [draft, setDraft] = useState(null);
  const [selected, setSelected] = useState("");
  const [page, setPage] = useState(0);
  const [review, setReview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!open) return;
    let active = true;
    api
      .scheduledReviews()
      .then((value) => {
        if (!active) return;
        setList(value);
        setDraft(toDraft(value.settings));
        setSelected((old) => old || value.items[0]?.id || "");
      })
      .catch((e) => active && setError(e.message));
    return () => {
      active = false;
    };
  }, [open]);

  useEffect(() => {
    if (!open || !selected) {
      setReview(null);
      return;
    }
    let active = true;
    setReview(null);
    api
      .savedReview(selected, page)
      .then((value) => active && setReview(value))
      .catch((e) => active && setError(e.message));
    return () => {
      active = false;
    };
  }, [open, selected, page]);

  const change = (key, value) => {
    setDraft((old) => ({ ...old, [key]: value }));
    setMessage("");
  };
  async function save(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const [hour, minute] = draft.time.split(":").map(Number);
      const value = await api.saveReviewSchedule({
        enabled: draft.enabled,
        weekday: draft.weekday,
        minute_of_day: hour * 60 + minute,
        time_zone: draft.time_zone.trim(),
      });
      setDraft(toDraft(value));
      setList((old) => ({ ...old, settings: value }));
      setMessage(value.enabled ? "Schedule saved." : "Weekly reviews are off. Saved reviews stay available.");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function markSeen() {
    setBusy(true);
    setError("");
    try {
      await api.seeReview(selected);
      const value = await api.scheduledReviews();
      setList(value);
      onChanged?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const current = list?.items.find((r) => r.id === selected);
  const groups = reviewGroups(review?.records);
  return (
    <Modal open={open} onClose={onClose} title="Weekly review" className="weekly-review-modal">
      <div className="weekly-body">
      <form className="weekly-settings" onSubmit={save}>
        <label className="weekly-toggle">
          <Checkbox
            checked={!!draft?.enabled}
            disabled={busy || !draft}
            onChange={(e) => change("enabled", e.target.checked)}
          />
          Send me a weekly review
        </label>
        {draft && (
          <div className="weekly-fields">
            <label>
              Day
              <Select aria-label="Weekly review day" value={draft.weekday} disabled={busy} onChange={(e) => change("weekday", Number(e.target.value))}>
                {WEEKDAYS.map((d, i) => (
                  <option key={d} value={i}>
                    {d}
                  </option>
                ))}
              </Select>
            </label>
            <label>
              Time (24-hour)
              <input aria-label="Weekly review time" type="time" required value={draft.time} disabled={busy} onChange={(e) => change("time", e.target.value)} />
            </label>
            <label>
              Time zone
              <Select aria-label="Weekly review time zone" value={draft.time_zone} disabled={busy} onChange={(e) => change("time_zone", e.target.value)}>
                {[...new Set([draft.time_zone, ...ZONES])].map((z) => (
                  <option key={z} value={z}>
                    {z}
                  </option>
                ))}
              </Select>
            </label>
            <Button type="submit" variant="primary" disabled={busy}>
              {busy ? "Saving…" : "Save"}
            </Button>
          </div>
        )}
        <p className="fine">
          {list?.settings.next_due_at
            ? `Next review ${stamp(list.settings.next_due_at)}. `
            : ""}
          A saved summary of your existing updates; no new sources or AI calls. The app must be running to deliver it.
        </p>
        {list?.settings.error_message && <p className="warning" role="status">{list.settings.error_message}</p>}
        {message && <p className="fine" role="status">{message}</p>}
        {error && <p className="warning" role="alert">{error}</p>}
      </form>

      <section className="weekly-latest" aria-label="Latest review">
        <div className="weekly-latest-head">
          <h3>{current ? `Week ending ${stamp(current.scheduled_at)}` : "Latest review"}</h3>
          {list?.items.length > 1 && (
            <Select aria-label="Choose a weekly review" value={selected} onChange={(e) => { setPage(0); setSelected(e.target.value); }}>
              {list.items.map((r) => (
                <option key={r.id} value={r.id}>
                  {stamp(r.scheduled_at)}
                </option>
              ))}
            </Select>
          )}
        </div>
        {!list && !error && <LoadingSkeleton rows={2} variant="panel" label="Loading weekly reviews…" />}
        {list && !list.items.length && (
          <EmptyState title="No weekly review yet" description="The first one is saved at your next scheduled time." />
        )}
        {current && (
          <p className="fine">
            {current.total} updates · {current.seen_at ? "Seen" : "Ready to review"}{" "}
            {!current.seen_at && (
              <Button variant="tertiary" size="inline" disabled={busy} onClick={markSeen}>
                Mark seen
              </Button>
            )}
          </p>
        )}
        {current && !review && <LoadingSkeleton rows={3} variant="panel" label="Reading this review…" />}
        {review && (
          <>
            {review.records.length ? (
              <ReviewList groups={groups} onOpenItem={(item) => { onClose(); onOpen(item.instrumentId, "updates"); }} />
            ) : (
              <p className="fine">No saved updates in this week.</p>
            )}
            {review.total > review.page_size && (
              <Pagination
                label="Review pages"
                page={page + 1}
                totalPages={Math.ceil(review.total / review.page_size)}
                disabled={busy}
                onPrevious={() => setPage((n) => n - 1)}
                onNext={() => setPage((n) => n + 1)}
              />
            )}
            <p className="fine">
              <a href={`/api/v1/scheduled-reviews/${selected}/export`} download>Download this review</a>
            </p>
          </>
        )}
      </section>
      </div>
    </Modal>
  );
}
