import LoadingSkeleton from "./LoadingSkeleton";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import { stamp } from "./MarketResearch";
const names = {
  completed: "Check completed",
  failed: "Check failed",
  stopped: "Watch stopped or changed",
  running: "No result yet",
  unfinished: "Completion missing",
};
const steps = {
  checked: "Checked",
  shared_recent_check: "Used recent shared coverage",
  completed: "Completed",
  not_run: "Not reached",
};
export default function WatchCheckHistory({ instrumentId, lastCheck }) {
  const [open, setOpen] = useState(false),
    [items, setItems] = useState([]),
    [cursor, setCursor] = useState(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!open) return;
    let active = true;
    setBusy(true);
    api
      .watchChecks(instrumentId)
      .then((d) => {
        if (active) {
          setItems(d.items);
          setCursor(d.next_cursor);
          setError("");
        }
      })
      .catch((e) => active && setError(e.message))
      .finally(() => active && setBusy(false));
    return () => {
      active = false;
    };
  }, [open, instrumentId, lastCheck]);
  async function more() {
    setBusy(true);
    setError("");
    try {
      const d = await api.watchChecks(instrumentId, cursor);
      setItems((p) => [
        ...p,
        ...d.items.filter((i) => !p.some((a) => a.id === i.id)),
      ]);
      setCursor(d.next_cursor);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <details
      className="watch-check-history"
      open={open}
      onToggle={(e) => setOpen(e.currentTarget.open)}
    >
      <summary>Watch check history</summary>
      <p className="fine">
        Scheduled checks recorded by this version of the app. Opening history
        does not refresh sources or request AI analysis. Checks made before this
        history was added are not reconstructed.
      </p>
      {error && (
        <p className="warning" role="alert">
          {error}
        </p>
      )}
      {busy && !items.length && (
        <LoadingSkeleton variant="panel" rows={1} label="Loading checks…" />
      )}
      {!busy && !error && !items.length && (
        <p className="fine">
          No scheduled checks recorded yet. Enable a watch to check while the
          app is running; manual analyses are separate.
        </p>
      )}
      {items.map((c) => (
        <article
          key={c.id}
          className="watch-check"
          aria-label="Scheduled watch check"
        >
          <div className="row">
            <strong>{names[c.status]}</strong>
            <small>{stamp(c.started_at)}</small>
          </div>
          <p>{c.reason}</p>
          {c.details.coverage_gap && (
            <p className="warning">
              Source coverage was incomplete at this check. A quiet result does
              not mean there was no important change.
            </p>
          )}
          <p className="fine">
            {c.match_idea
              ? c.idea_purpose === "question"
                ? "Saved-question answer watch"
                : "Saved-reasoning watch"
              : "Company news and sentiment watch"}{" "}
            ·{" "}
            {c.completed_at
              ? `finished ${stamp(c.completed_at)} · ${Math.round(c.elapsed_seconds)} seconds elapsed`
              : "No finished result is recorded."}
          </p>
          {!c.withheld && (
            <details>
              <summary>What was checked</summary>
              <dl>
                {[
                  ["market", "Company news"],
                  ["social", "Social feeds"],
                  ["analysis", "Sentiment analysis"],
                  ...(c.match_idea
                    ? [
                        [
                          "private",
                          c.idea_purpose === "question"
                            ? "Saved question"
                            : "Saved reasoning",
                        ],
                      ]
                    : []),
                ].map(([key, label]) => (
                  <div key={key}>
                    <dt>{label}</dt>
                    <dd>{steps[c.details[key]] || "Not recorded"}</dd>
                  </div>
                ))}
              </dl>
              {c.include_context && (
                <div className="fine" aria-label="Original reply context check">
                  <p>
                    Original reply context:{" "}
                    {{
                      completed: "checked",
                      partial: "partial coverage",
                      checking: "not completed",
                      source_changed: "a comment changed; analysis stopped",
                    }[c.details.context?.status] || "not reached"}
                    .
                  </p>
                  {c.details.context && (
                    <>
                      <p>
                        {c.details.context.items.length} of{" "}
                        {c.details.context.selected_replies} selected HN replies
                        considered (limit {c.details.context.limit});{" "}
                        {c.details.context.source_requests} original API
                        requests.{" "}
                        {c.details.context.items.filter((i) => i.reused).length}{" "}
                        saved parents reused.
                        {c.details.context.parents_used_by_analysis != null && (
                          <>
                            {" "}
                            {c.details.context.parents_used_by_analysis} parents
                            used by the saved analysis.
                          </>
                        )}
                      </p>
                      {c.details.context.items.some(
                        (i) => i.outcome !== "available",
                      ) && (
                        <p>
                          Some replies had no usable parent check. The saved
                          analysis and its sources show exactly what was
                          supplied; this is not a complete conversation.
                        </p>
                      )}
                    </>
                  )}
                </div>
              )}
              {c.details.failed_stage && (
                <p className="warning">Stopped at: {c.details.failed_stage}.</p>
              )}
              {c.event_version_id && (
                <p className="fine">
                  Approved event check:{" "}
                  {{
                    checked:
                      "New interpretation saved; condition reassessment queued",
                    reused:
                      "Identical eligible inputs; saved interpretation reused without an AI call",
                    no_eligible_evidence: "No eligible reports; no AI call",
                    approval_changed:
                      "Paused: approved revision or watch settings changed",
                    historical_only:
                      "Result retained in history; not applied to current monitoring",
                    stopped: "Watch changed; no event result applied",
                  }[c.details.events] || "No completed event check recorded"}
                  . Event-condition updates appear in the condition stream after
                  reassessment.
                </p>
              )}
              {c.details.selected && (
                <p className="fine">
                  {c.details.selected.news} news stories selected from{" "}
                  {c.details.candidate_news ?? "an unrecorded number of"}{" "}
                  candidates; {c.details.selected.social} social posts selected
                  from {c.details.candidate_social ?? "an unrecorded number of"}{" "}
                  candidates. Selection is bounded; unselected evidence may
                  matter.
                </p>
              )}
              {c.details.cutoff && (
                <p className="fine">
                  Analysis source cutoff {stamp(c.details.cutoff)}. This
                  analysis was originally saved{" "}
                  {stamp(c.details.analysis_saved_at)}.
                </p>
              )}
              {c.details.market_coverage && (
                <p className="fine">
                  Market source last completed{" "}
                  {stamp(c.details.market_coverage.completed_at)}
                  {c.details.market_coverage.news_failed
                    ? " · news retrieval failed"
                    : ""}
                  {c.details.market_coverage.quote_failed
                    ? " · quote retrieval failed"
                    : ""}
                  .
                </p>
              )}
              {!!c.details.provider_coverage?.length && (
                <details className="secondary-details">
                  <summary>Publisher feeds &amp; X connection checks</summary>
                  {c.details.provider_coverage.map((source) => (
                    <p className="fine" key={source.provider}>
                      <strong>{source.label}</strong> · {source.message}
                    </p>
                  ))}
                </details>
              )}
              {c.details.social_coverage?.map((s) => (
                <p key={s.feed} className="fine">
                  {s.label || `Reddit · r/${s.feed}`}:{" "}
                  {!s.enabled
                    ? "disabled"
                    : s.failed
                      ? "last check failed"
                      : s.completed_at
                        ? "checked"
                        : "not checked"}
                  {s.completed_at ? ` · ${stamp(s.completed_at)}` : ""}
                </p>
              ))}
            </details>
          )}
          {!!c.alert_count && (
            <a
              className="source-link"
              href={`/?company=${instrumentId}&view=updates`}
            >
              Review created updates ↗
            </a>
          )}
        </article>
      ))}
      {cursor && (
        <button disabled={busy} onClick={more}>
          Earlier checks
        </button>
      )}
    </details>
  );
}
