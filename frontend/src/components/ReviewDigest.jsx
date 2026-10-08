import { readableLoad } from "../lib/loading";
import LoadingSkeleton from "./LoadingSkeleton";
import Select from "./Select";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import { stamp } from "./MarketResearch";
import ScheduledReviews from "./ScheduledReviews";
import IdeaAlertChecks from "./IdeaAlertChecks";
import { ResearchAlerts } from "./SentimentPanel";
const statusName = (value) =>
  ({ reviewed: "Reviewed", unresolved: "Left unresolved" })[value] ||
  "Awaiting review";
export default function ReviewDigest({
  onOpen,
  onSource,
  selectedCompanyId = "",
  onCompanyChange,
}) {
  const [savedId, setSavedId] = useState(
    () => new URLSearchParams(window.location.search).get("review_id") || "",
  );
  function selectSaved(id) {
    setSavedId(id);
    setPage(0);
    setCutoff("");
    const url = new URL(window.location.href);
    if (id) url.searchParams.set("review_id", id);
    else url.searchParams.delete("review_id");
    window.history.replaceState(null, "", url);
  }
  const [days, setDays] = useState(7),
    [review, setReview] = useState("all"),
    [page, setPage] = useState(0),
    [cutoff, setCutoff] = useState(""),
    [refresh, setRefresh] = useState(0);
  const company = selectedCompanyId;
  const [data, setData] = useState(null),
    [loading, setLoading] = useState(true),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  useEffect(() => {
    let current = true;
    setLoading(true);
    setData(null);
    setError("");
    readableLoad(
      savedId
        ? api.savedReview(savedId, page)
        : api.researchReview({
            days,
            instrument_id: company,
            review,
            page,
            cutoff,
          }),
    )
      .then((value) => {
        if (current) setData(value);
      })
      .catch((e) => {
        if (current) setError(e.message);
      })
      .finally(() => {
        if (current) setLoading(false);
      });
    return () => {
      current = false;
    };
  }, [days, company, review, page, cutoff, refresh, savedId]);
  function reset() {
    setPage(0);
    setCutoff("");
  }
  function refreshReview() {
    reset();
    setRefresh((x) => x + 1);
  }
  async function acknowledge(kind, id, action) {
    setBusy(true);
    setError("");
    try {
      await (kind === "idea"
        ? api.reviewIdeaAlert(id, action)
        : api.reviewAlert(id, action));
      refreshReview();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  const scoped = (data?.companies || []).filter(
    (c) => savedId || !company || c.id === company,
  );
  const reportQuery = new URLSearchParams({
    days: String(days),
    review,
    cutoff: data?.cutoff || "",
    ...(company ? { instrument_id: company } : {}),
  });
  return (
    <section className="periodic-review" aria-label="Periodic research review">
      <div className="market-section-head">
        <div>
          <span className="section-label">RETURN TO YOUR RESEARCH</span>
          <h2>What changed across my ideas?</h2>
        </div>
        <button onClick={refreshReview} disabled={loading || busy}>
          Refresh saved-record view
        </button>
      </div>
      <p className="fine">
        Review saved updates together. This page does not fetch new sources or
        run AI.
      </p>
      <ScheduledReviews onSelect={selectSaved} selected={savedId} />
      {savedId && (
        <div className="review-carryover">
          <p>
            Saved weekly review. Counts, coverage and acknowledgement status
            reflect when it was prepared. Source access is checked again now.
            Open current Updates to act on an individual alert.
          </p>
          <button onClick={() => selectSaved("")}>
            Back to current review
          </button>
        </div>
      )}
      {!savedId && (
        <div className="review-filters">
          <label>
            Period
            <Select
              aria-label="Review period"
              value={days}
              disabled={busy}
              onChange={(e) => {
                setDays(Number(e.target.value));
                reset();
              }}
            >
              <option value="1">Last 24 hours</option>
              <option value="7">Last 7 days</option>
              <option value="30">Last 30 days</option>
              <option value="0">All retained records</option>
            </Select>
          </label>
          <label>
            Company
            <Select
              aria-label="Review company"
              value={company}
              disabled={busy}
              onChange={(e) => {
                onCompanyChange?.(e.target.value);
                reset();
              }}
            >
              <option value="">All my ideas and watches</option>
              {data?.companies.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.symbol} · {c.name}
                </option>
              ))}
            </Select>
          </label>
          <label>
            Records
            <Select
              aria-label="Review record status"
              value={review}
              disabled={busy}
              onChange={(e) => {
                setReview(e.target.value);
                reset();
              }}
            >
              <option value="all">All statuses</option>
              <option value="pending">Awaiting review</option>
              <option value="unresolved">Left unresolved</option>
              <option value="reviewed">Reviewed</option>
            </Select>
          </label>
        </div>
      )}
      {error && (
        <p className="warning" role="alert">
          {error}
        </p>
      )}
      {loading ? (
        <LoadingSkeleton label="Reading saved records…" />
      ) : (
        data && (
          <>
            <p className="fine">
              Updates recorded{" "}
              {data.window_start
                ? `from ${stamp(data.window_start)}`
                : "across all retained dates"}{" "}
              through {stamp(data.cutoff)}. Coverage and review status read{" "}
              {stamp(data.generated_at)}.
            </p>
            {savedId && (
              <p className="fine">
                Scheduled for {stamp(data.scheduled_at)} (
                {data.schedule_time_zone}). Source access checked{" "}
                {stamp(data.access_checked_at)}.{" "}
                {data.skipped_occurrences > 0 &&
                  `${data.skipped_occurrences} earlier scheduled weeks were skipped; older unreviewed counts remain below.`}
              </p>
            )}
            <div className="review-totals" aria-label="Review totals">
              <div>
                <strong>{data.totals.new_count}</strong>
                <span>updates in this period</span>
              </div>
              <div>
                <strong>{data.totals.pending_count}</strong>
                <span>awaiting review through cutoff</span>
              </div>
              <div>
                <strong>{data.totals.unresolved_count}</strong>
                <span>left unresolved through cutoff</span>
              </div>
              <div>
                <strong>{data.totals.quiet_checks}</strong>
                <span>quiet private checks in period</span>
              </div>
            </div>
            {data.totals.older_pending_count > 0 && (
              <div className="review-carryover">
                <p>
                  {data.totals.older_pending_count} unreviewed updates were
                  recorded before this period.
                </p>
                <button
                  onClick={() => {
                    selectSaved("");
                    setDays(0);
                    setReview("pending");
                    reset();
                  }}
                >
                  Include older unreviewed updates
                </button>
              </div>
            )}
            {!data.companies.length ? (
              <p className="muted">
                Save reasoning or add a company watch to begin a periodic
                review.
              </p>
            ) : (
              <div className="review-companies">
                {scoped.map((c) => (
                  <article className="review-company" key={c.id}>
                    <div className="row">
                      <h3>
                        {c.symbol} <small>{c.name}</small>
                      </h3>
                      <span className="status">{c.status || "Watch only"}</span>
                    </div>
                    <p>{c.question || "No saved reasoning yet."}</p>
                    <p className="fine">
                      {c.new_count} updates in period · {c.pending_count}{" "}
                      awaiting review · {c.unresolved_count} left unresolved.
                    </p>
                    {c.research_action?.action === "unresolved" && (
                      <p className="warning">
                        Research question left unresolved:{" "}
                        {c.research_action.question}
                      </p>
                    )}
                    <p className="fine">
                      Local news/social watch:{" "}
                      {c.coverage.watch?.enabled
                        ? `on · every ${c.coverage.watch.interval_minutes === 60 ? "hour" : "four hours"} · ${c.coverage.watch.match_idea ? (c.coverage.watch.idea_purpose === "question" ? "answers to saved question" : "saved-reasoning connections") : "company updates"}`
                        : "off"}
                      .{" "}
                      {c.coverage.mode === "recorded"
                        ? "Recorded fictional scenario."
                        : c.coverage.filing_watch?.enabled
                          ? "Daily filing checks are on while the app runs."
                          : "Daily filing checks are off; refresh manually."}
                    </p>
                    <p className="fine">
                      Last alert review:{" "}
                      {c.latest_review_at
                        ? stamp(c.latest_review_at)
                        : "None recorded"}
                      .
                    </p>
                    {c.coverage.concerns.length > 0 && (
                      <p className="coverage-note">{c.coverage.concerns[0]}</p>
                    )}
                    <details className="review-coverage">
                      <summary>
                        {c.coverage.concerns.length
                          ? `${c.coverage.concerns.length} source coverage ${c.coverage.concerns.length === 1 ? "note" : "notes"}`
                          : "Inspect source coverage"}
                      </summary>
                      <p className="fine">
                        News check:{" "}
                        {c.coverage.news_checked_at
                          ? stamp(c.coverage.news_checked_at)
                          : "No completed check"}
                        . Analysed sample:{" "}
                        {c.coverage.sentiment_cutoff
                          ? stamp(c.coverage.sentiment_cutoff)
                          : "Not available"}
                        .
                      </p>
                      {c.coverage.concerns.map((note) => (
                        <p key={note}>{note}</p>
                      ))}
                      {!c.coverage.concerns.length && (
                        <p>
                          Recent checks are recorded, but selected feeds and
                          snippets do not cover all news or investor discussion.
                        </p>
                      )}
                    </details>
                    <div className="sentiment-controls">
                      <button
                        onClick={() => {
                          selectSaved("");
                          onCompanyChange?.(c.id);
                          reset();
                        }}
                      >
                        Review {c.symbol} updates
                      </button>
                      <button onClick={() => onOpen(c.id, "workspace")}>
                        Open {c.symbol} research ↗
                      </button>
                      <button onClick={() => onOpen(c.id, "idea")}>
                        Open saved idea ↗
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            )}
            <div className="market-section-head">
              <h3>Saved updates</h3>
              {data.companies.length > 0 && (
                <a
                  href={
                    savedId
                      ? `/api/v1/scheduled-reviews/${savedId}/export`
                      : `/api/v1/research-review/export?${reportQuery}`
                  }
                  download
                >
                  Download this review
                </a>
              )}
            </div>
            <p className="fine">
              Showing {data.records.length ? data.page * data.page_size + 1 : 0}
              –{data.page * data.page_size + data.records.length} of{" "}
              {data.total} matching records. Download includes all matching
              records, up to 1,000; use a shorter period if needed.
            </p>
            {!data.records.length && (
              <p className="muted">
                No saved updates match this view. Check coverage above; this
                does not establish that nothing important happened.
              </p>
            )}
            <div className="review-records">
              {data.records.map((record) => (
                <article
                  className="review-record"
                  key={`${record.kind}:${record.id}`}
                >
                  <div className="row">
                    <strong>
                      {record.detail.symbol} ·{" "}
                      {record.kind === "idea"
                        ? "Saved reasoning"
                        : record.kind === "company"
                          ? "News and sentiment"
                          : "Condition assessment"}
                    </strong>
                    <time>{stamp(record.created_at)}</time>
                  </div>
                  <h4>{record.title}</h4>
                  <p className="fine">{statusName(record.review_action)}</p>
                  {savedId && (
                    <button
                      onClick={() => onOpen(record.instrument_id, "updates")}
                    >
                      Open current Updates ↗
                    </button>
                  )}
                  {record.kind === "condition" ? (
                    <>
                      <p>{record.detail.question}</p>
                      {record.detail.withheld && (
                        <p className="warning">
                          Source access changed. Figures and interpretations are
                          withheld here.
                        </p>
                      )}
                      <button
                        onClick={() =>
                          onOpen(
                            record.instrument_id,
                            "history",
                            record.detail.evaluation_id,
                          )
                        }
                      >
                        Open exact assessment ↗
                      </button>
                    </>
                  ) : (
                    <details>
                      <summary>
                        Inspect this{" "}
                        {record.kind === "idea"
                          ? "reasoning check"
                          : "company alert"}
                      </summary>
                      {record.kind === "idea" ? (
                        <IdeaAlertChecks
                          readOnly={!!savedId}
                          checks={[record.detail]}
                          history
                          busy={busy}
                          onSource={onSource}
                          onOpen={onOpen}
                          onReview={(id, action) =>
                            acknowledge("idea", id, action)
                          }
                        />
                      ) : (
                        <ResearchAlerts
                          readOnly={!!savedId}
                          alerts={[record.detail]}
                          history
                          busy={busy}
                          onSource={onSource}
                          onOpen={onOpen}
                          onReview={(id, action) =>
                            acknowledge("company", id, action)
                          }
                        />
                      )}
                    </details>
                  )}
                </article>
              ))}
            </div>
            <div className="review-pagination">
              <button
                disabled={data.page === 0 || busy}
                onClick={() => {
                  setCutoff(data.cutoff);
                  setPage(data.page - 1);
                }}
              >
                Previous records
              </button>
              <span>Page {data.page + 1}</span>
              <button
                disabled={
                  (data.page + 1) * data.page_size >= data.total || busy
                }
                onClick={() => {
                  setCutoff(data.cutoff);
                  setPage(data.page + 1);
                }}
              >
                Next records
              </button>
            </div>
            <p className="fine">{data.limitation}</p>
          </>
        )
      )}
    </section>
  );
}
