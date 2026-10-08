import Select from "./Select";
import { useState } from "react";
import { eventWindows } from "../lib/eventWindows";
const labels = {
  confirmed: "Report matches your required event",
  risk_reported: "Report matches the risk",
  denied_report: "A report denies this claim",
  uncertain: "Evidence does not establish this event",
  conflicting: "Reports conflict",
  not_checked: "Evidence check needed",
  deadline_unconfirmed: "Deadline passed · unconfirmed",
  not_started: "Report window has not started",
};
export const newEvent = () => ({
  condition_id: crypto.randomUUID(),
  description: "",
  evidence_requirement: "",
  role: "required",
  date_basis: "report_publication",
  repeat_months: 0,
  repeat_count: 1,
  window_start: "",
  deadline: "",
});
export function EventSchedule({ event }) {
  if (!event.repeat_months || !event.window_start || !event.deadline)
    return null;
  let periods;
  try {
    periods = eventWindows(event);
  } catch (error) {
    return <p className="warning">{error.message}</p>;
  }
  return (
    <details className="event-schedule">
      <summary>Preview all {periods.length} windows</summary>
      <p className="fine">
        Each window needs its own evidence. Choose Event happened during when
        the event itself must occur in every window. Dates shift from your
        original selection. Month-end selections stay at month end; other dates
        keep their day or use the last day of a shorter month. Monitoring stops
        creating new windows after the last one.
      </p>
      <ol>
        {periods.map((w) => (
          <li key={w.index}>
            {w.window_start} through {w.deadline}
          </li>
        ))}
      </ol>
    </details>
  );
}

export function EventEditor({ events = [], onChange }) {
  const edit = (i, field, value) =>
    onChange(events.map((e, j) => (i === j ? { ...e, [field]: value } : e)));
  return (
    <section className="event-editor">
      <h3>Events to watch</h3>
      <p className="fine">
        Choose an event, the evidence it needs, and whether dates refer to the
        report or the event itself. Up to three events.
      </p>
      {events.map((e, i) => (
        <fieldset className="event-definition" key={e.condition_id}>
          <legend>Event {i + 1}</legend>
          <label>
            Event description
            <input
              aria-label={`Event description ${i + 1}`}
              value={e.description}
              maxLength={400}
              onChange={(x) => edit(i, "description", x.target.value)}
              placeholder="A named product becomes generally available"
            />
          </label>
          <label>
            Evidence required
            <textarea
              aria-label={`Event evidence required ${i + 1}`}
              value={e.evidence_requirement}
              maxLength={600}
              onChange={(x) => edit(i, "evidence_requirement", x.target.value)}
              placeholder="A report explicitly naming the product, market and completed launch; plans or a beta are insufficient."
            />
          </label>
          <label>
            Meaning for this idea
            <Select
              aria-label={`Event role ${i + 1}`}
              value={e.role}
              onChange={(x) => edit(i, "role", x.target.value)}
            >
              <option value="required">Required event</option>
              <option value="risk">Risk to watch</option>
            </Select>
          </label>
          <label>
            What these dates mean
            <Select
              aria-label={`Event date meaning ${i + 1}`}
              value={e.date_basis || "report_publication"}
              onChange={(x) => edit(i, "date_basis", x.target.value)}
            >
              <option value="report_publication">
                Report published during
              </option>
              <option value="event_occurrence">Event happened during</option>
            </Select>
          </label>
          <p className="fine">
            {e.date_basis === "event_occurrence"
              ? "A later report can confirm an earlier event. The source must state the event’s full day, month and year. Missing or ambiguous dates stay unconfirmed; publication time is not substituted."
              : "Only reports published within these inclusive UTC dates count. This does not constrain when the event actually happened."}
          </p>
          <div className="event-dates">
            <label>
              {e.date_basis === "event_occurrence"
                ? "Event happened from"
                : "Reports published from"}
              <input
                aria-label={`${e.date_basis === "event_occurrence" ? "Event" : "Report"} window start ${i + 1}`}
                type="date"
                value={e.window_start}
                onChange={(x) => edit(i, "window_start", x.target.value)}
              />
            </label>
            <label>
              Through deadline (inclusive)
              <input
                aria-label={`${e.date_basis === "event_occurrence" ? "Event" : "Report"} deadline ${i + 1}`}
                type="date"
                min={e.window_start || undefined}
                value={e.deadline}
                onChange={(x) => edit(i, "deadline", x.target.value)}
              />
            </label>
          </div>
          <label>
            Repeat this window
            <Select
              aria-label={`Event repeat interval ${i + 1}`}
              value={e.repeat_months || 0}
              onChange={(x) =>
                onChange(
                  events.map((item, j) =>
                    j === i
                      ? {
                          ...item,
                          repeat_months: Number(x.target.value),
                          repeat_count: Number(x.target.value)
                            ? item.repeat_count > 1
                              ? item.repeat_count
                              : 4
                            : 1,
                        }
                      : item,
                  ),
                )
              }
            >
              <option value={0}>Once</option>
              <option value={1}>Every month</option>
              <option value={3}>Every 3 months</option>
              <option value={12}>Every year</option>
            </Select>
          </label>
          {!!e.repeat_months && (
            <label>
              Number of windows, including the first
              <input
                aria-label={`Event window count ${i + 1}`}
                type="number"
                min="2"
                max="12"
                value={e.repeat_count ?? 4}
                onChange={(x) =>
                  edit(
                    i,
                    "repeat_count",
                    x.target.value === "" ? "" : Number(x.target.value),
                  )
                }
              />
            </label>
          )}
          <EventSchedule event={e} />
          <button
            type="button"
            className="text-button"
            onClick={() => onChange(events.filter((_, j) => i !== j))}
          >
            Remove event {i + 1}
          </button>
        </fieldset>
      ))}
      {events.length < 3 && (
        <button
          type="button"
          className="text-button"
          onClick={() => onChange([...events, newEvent()])}
        >
          + Add event condition
        </button>
      )}
    </section>
  );
}
export function EventDefinitions({ events = [] }) {
  return events.map((e) => (
    <article className="event-definition" key={e.condition_id}>
      <strong>
        {e.role === "risk" ? "Risk to watch" : "Required event"} ·{" "}
        {e.description}
      </strong>
      <p>{e.evidence_requirement}</p>
      <EventSchedule event={e} />
      <p className="fine">
        {e.date_basis === "event_occurrence"
          ? "Event happened"
          : "Reports published"}{" "}
        {e.window_start} through {e.deadline} ·{" "}
        {e.date_basis === "event_occurrence"
          ? "inclusive source-stated calendar dates"
          : "inclusive UTC dates"}
      </p>
    </article>
  ));
}
export default function EventAssessment({
  version,
  evaluation,
  review,
  documents = [],
  onSource,
  onCheck,
  busy,
  unavailableReason,
}) {
  const [selectedPeriods, setSelectedPeriods] = useState({});
  const events = version.events || [];
  const recurring = events.some((e) => e.repeat_months);
  if (!events.length) return null;
  const allowed = new Set(documents.map((d) => d.id));
  const points = evaluation?.event_results || review?.events || [];
  return (
    <section className="event-assessment" aria-label="Event conditions">
      <h3>Event conditions</h3>
      <p className="fine">
        AI interpretation of the selected reports, not verification that an
        event occurred. A rumour, plan, denial or missing report cannot
        establish completion or safety.
      </p>
      {events.map((event) => {
        const point = points.find((p) => p.condition_id === event.condition_id);
        const citations = point?.citations || [];
        const window = point?.window || event;
        const withheld =
          point?.withheld || citations.some((c) => !allowed.has(c.source_id));
        return (
          <article className="event-definition" key={event.condition_id}>
            <span className="section-label">
              {event.role === "risk" ? "RISK TO WATCH" : "REQUIRED EVENT"}
            </span>
            <h4>{event.description}</h4>
            <p>{event.evidence_requirement}</p>
            <p className="fine">
              {event.date_basis === "event_occurrence"
                ? "Event occurrence window"
                : "Report window"}{" "}
              {window.window_start} through {window.deadline}{" "}
              {event.date_basis === "event_occurrence"
                ? "(source-stated dates)"
                : "(UTC)"}
            </p>
            {point?.window && (
              <p className="fine">
                Window {point.window.index} of {point.window.count}. Earlier
                confirmations do not carry into later windows.
              </p>
            )}
            <EventSchedule event={event} />
            {withheld ? (
              <p>
                Interpretation withheld: a cited historical source is
                unavailable.
              </p>
            ) : (
              <>
                <strong>
                  {(point?.state === "not_started" &&
                  event.date_basis === "event_occurrence"
                    ? "Event window has not started"
                    : labels[point?.state || point?.status]) ||
                    "Evidence not checked"}
                </strong>
                {point && <p>{point.explanation}</p>}
                {citations.map((c, i) => (
                  <div key={i}>
                    <blockquote>{c.quote}</blockquote>
                    {c.occurrence_dates?.map((d, j) => (
                      <p className="fine" key={j}>
                        Selected event date: “{d.date_text}” →{" "}
                        {d.date || "No unambiguous calendar day"} ·{" "}
                        {
                          {
                            within_window: "within your window",
                            outside_window: "outside your window",
                            after_report: "after the report date",
                            unknown_date: "timing unconfirmed",
                          }[d.state]
                        }
                      </p>
                    ))}
                    <button
                      className="text-button"
                      onClick={() => onSource(c.source_id)}
                    >
                      Inspect event source {i + 1} ↗
                    </button>
                  </div>
                ))}
              </>
            )}
          </article>
        );
      })}
      {review && (
        <p className="fine">
          Saved evidence check ·{" "}
          {new Date(review.created_at).toLocaleString("en-GB", {
            timeZone: "UTC",
          })}{" "}
          UTC · source cutoff {review.cutoff}. Reopening makes no AI call.{" "}
          {review.omitted_source_count || 0} other source versions and{" "}
          {review.omitted_fragment_count || 0} incomplete passages omitted.
        </p>
      )}
      {review?.applied_to_monitoring === false && (
        <p className="warning">
          {review.historical_window_check
            ? "This check reviews earlier windows. It is saved in history and does not replace the current window’s monitoring result."
            : "This check finished after its window, watch, revision or source snapshot changed. It is retained as history and was not applied to monitoring."}
        </p>
      )}
      {evaluation?.manifest.event_review_reuse && (
        <p className="fine">
          Reused the saved interpretation because the exact event definitions
          and eligible source inputs are unchanged. No new AI call was needed;
          the original check date and source cutoff remain above.
        </p>
      )}
      {(!review || recurring) && onCheck && (
        <>
          {events
            .filter((e) => e.repeat_months)
            .map((e) => (
              <label key={e.condition_id}>
                Window to check · {e.description}
                <Select
                  aria-label={`Window to check for ${e.description}`}
                  value={selectedPeriods[e.condition_id] || ""}
                  onChange={(x) =>
                    setSelectedPeriods({
                      ...selectedPeriods,
                      [e.condition_id]: x.target.value,
                    })
                  }
                >
                  <option value="">Current window</option>
                  {eventWindows(e).map((w) => (
                    <option key={w.index} value={w.index}>
                      Window {w.index}: {w.window_start} – {w.deadline}
                    </option>
                  ))}
                </Select>
              </label>
            ))}
          {recurring && (
            <p className="fine">
              Earlier-window checks use the selected saved source snapshot and
              stay in History. They do not replace current monitoring. Windows
              that have not started cannot be checked. This does not retrieve
              older reports.
            </p>
          )}
          <button
            className="secondary"
            disabled={busy || !!unavailableReason}
            onClick={() =>
              onCheck(
                Object.fromEntries(
                  Object.entries(selectedPeriods)
                    .filter(([, value]) => value)
                    .map(([key, value]) => [key, Number(value)]),
                ),
              )
            }
          >
            {busy ? "Checking event evidence…" : "Check event evidence"}
          </button>
          <p className="fine">
            Explicit AI check of this saved revision and source snapshot. Uses
            the shared building budget. Automatic event checks are optional in
            the news watch settings. Identical eligible inputs reuse a saved
            check. News coverage is limited to available snippets from the
            latest seven days at the snapshot, with up to 12 sources; a longer
            window does not retrieve older reports.
          </p>
          {unavailableReason && <p className="fine">{unavailableReason}</p>}
        </>
      )}
      <p className="fine">
        A required event needs matching reported evidence. A reported risk
        prompts review. Other cases stay unknown, including a deadline passing
        without confirmation. These states are research checks, not investment
        recommendations.
      </p>
    </section>
  );
}
