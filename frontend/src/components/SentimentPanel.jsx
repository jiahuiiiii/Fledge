import NewsStatus from "./NewsStatus";
import { countedTone } from "../lib/newsPresentation";
import { modelAvailability } from "../lib/modelAvailability";
import Checkbox from "./Checkbox";
import Select from "./Select";
import SentimentLimits from "./SentimentLimits";
import SentimentBasis from "./SentimentBasis";
import SentimentPriceContext from "./SentimentPriceContext";
import { sentimentSummaryLabel } from "../lib/sentimentSummary";
import DiscussionThemes from "./DiscussionThemes";
import SentimentContext from "./SentimentContext";
import OriginalSample from "./OriginalSample";
import CurrentSentimentSources from "./CurrentSentimentSources";
import WatchCheckHistory from "./WatchCheckHistory";
import SentimentHistory from "./SentimentHistory";
import SourceFilters, { SourceLabel, sourceScope } from "./SourceFilters";
import AllSourceSummary from "./AllSourceSummary";
import { originalSample } from "../lib/originalSample";
import { sourceHeadline } from "../lib/sourceHeadline";
import "./NewsDiscussion.css";
import { useEffect, useState } from "react";
import Modal from "./Modal";
import EvidenceButton from "./EvidenceButton";
import { stamp } from "./MarketResearch";
const names = {
  positive: "Positive",
  negative: "Negative",
  mixed: "Mixed",
  neutral: "Neutral",
  unclear: "Unclear",
};
export default function SentimentPanel({
  data,
  busy,
  modelStatus,
  onAnalyze,
  loadingRun,
  onCheckIdea,
  onWatch,
  onEventWatch,
  onSource,
  onThemeSource,
  onCoverage,
  onThemesChange,
}) {
  const [days, setDays] = useState(
    data.sentiment?.social_lookback_days || loadingRun?.lookback_days || 7,
  );
  const availability = modelAvailability(modelStatus, "briefing_enabled");
  const analysisStep = loadingRun?.steps.find((s) => s.key === "analysis");
  const batchProgress = analysisStep?.batches;
  const [tab, setTab] = useState("news");
  const [relevanceFilter, setRelevanceFilter] = useState("all");
  const [page, setPage] = useState(1);
  const [checkPurpose, setCheckPurpose] = useState("reasoning");
  const channel = tab === "all" ? "all" : tab === "news" ? "news" : "social";
  const platform = tab === "all" || tab === "news" ? null : tab;
  const [evidenceView, setEvidenceView] = useState(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const a = data.sentiment,
    watch = data.news_watch;
  const activeQuestion =
    data.versions?.[0]?.question?.trim() && data.thesis?.status !== "archived";
  const activeReasoning =
    data.versions?.[0]?.reasoning?.trim() && data.thesis?.status !== "archived";
  const approvedEvents =
    data.thesis?.status === "monitoring" &&
    data.versions?.[0]?.events?.length > 0;
  const eventWatchCurrent =
    watch?.event_version_id === data.versions?.[0]?.id && approvedEvents;
  const sample =
    channel === "news"
      ? a?.summary?.news
      : a?.summary?.social_platforms?.[platform] ||
        (platform === "reddit" ? a?.summary?.social : null);
  const counts = countedTone(sample);
  const disabledReason = loadingRun?.active
    ? "A research update is already running. Wait for it to finish."
    : availability.blocked && availability.state !== "running"
      ? availability.message
      : "";
  const pool =
    channel === "news"
      ? a?.coverage?.available_news
      : a?.coverage?.social_platforms?.[platform];
  const sourceOrder = new Map(
    originalSample(a, "all").map((source, index) => [source.id, index]),
  );
  const items = (a?.items || [])
    .filter(
      (item) =>
        tab === "all" ||
        (item.channel === channel &&
          (!platform ||
            (a.sources.find((source) => source.id === item.source_id)
              ?.platform || "reddit") === platform)),
    )
    .sort((left, right) =>
      tab === "all"
        ? (sourceOrder.get(left.source_id) ?? Infinity) -
          (sourceOrder.get(right.source_id) ?? Infinity)
        : 0,
    );
  const coverageLinks = a?.coverage_links || [];
  useEffect(() => setPage(1), [a?.id, tab, relevanceFilter]);
  const filteredItems = items.filter(
    (item) => relevanceFilter === "all" || item.relevance === relevanceFilter,
  );
  const totalPages = Math.max(1, Math.ceil(filteredItems.length / 12));
  const currentPage = Math.min(page, totalPages);
  const shownItems = filteredItems.slice(
    (currentPage - 1) * 12,
    currentPage * 12,
  );
  const sampledFeeds = [
    ...new Set(
      (a?.sources || [])
        .filter(
          (s) => s.kind === "social" && (s.platform || "reddit") === platform,
        )
        .map((s) => s.source),
    ),
  ].join(", ");
  return (
    <section className="sentiment-panel" aria-label="News and social sentiment">
      <div className="market-section-head">
        <div>
          <h2>What’s the tone?</h2>
        </div>
        <div className="sentiment-analyse-action">
          <button
            aria-describedby={
              disabledReason ? "sentiment-disabled-reason" : undefined
            }
            disabled={
              !!loadingRun?.active ||
              (availability.blocked && availability.state !== "running")
            }
            onClick={() => onAnalyze(days)}
          >
            {loadingRun?.active &&
            loadingRun.steps.some((s) => s.key === "analysis")
              ? loadingRun.steps.find((s) => s.key === "analysis")?.status ===
                "running"
                ? "Analysing sentiment…"
                : "Fetching sources · analysis queued…"
              : "Refresh & analyse"}
          </button>
          {disabledReason && (
            <p id="sentiment-disabled-reason" role="status">
              {disabledReason}
            </p>
          )}
        </div>
      </div>
      {batchProgress && analysisStep.status !== "ready" && (
        <div className="sentiment-batch-progress">
          <p className="fine" role="status">
            {batchProgress.message}
          </p>
          <div
            className="research-progress"
            role="progressbar"
            aria-label="Sentiment batches complete"
            aria-valuemin={0}
            aria-valuemax={batchProgress.total}
            aria-valuenow={batchProgress.completed}
          >
            <span
              style={{
                width: `${(batchProgress.completed / batchProgress.total) * 100}%`,
              }}
            />
          </div>
          {!loadingRun.active && (
            <p className="fine">
              Refresh &amp; analyse reuses completed batches when their sources
              and context are unchanged.
            </p>
          )}
        </div>
      )}
      <details className="sentiment-reading-settings">
        <summary>
          Reading settings{" "}
          <span>
            News 7 days · Discussion {days} days · Watch{" "}
            {watch?.enabled ? "on" : "off"}
          </span>
        </summary>
        <div className="sentiment-controls sentiment-toolbar">
          <label>
            Discussion window{" "}
            <Select
              aria-label="Discussion window"
              value={days}
              disabled={!!loadingRun?.active}
              onChange={(e) => setDays(Number(e.target.value))}
            >
              <option value={1}>Past 24 hours</option>
              <option value={7}>Past 7 days · default</option>
              <option value={30}>Past 30 days</option>
            </Select>
          </label>
          <button
            type="button"
            className="source-link"
            aria-haspopup="dialog"
            onClick={() => setSettingsOpen(true)}
          >
            Watch · {watch?.enabled ? "on" : "off"}
          </button>
        </div>
        {(a || watch?.enabled) && (
          <p className="fine sentiment-meta" role="status">
            {a &&
              `AI reading saved ${stamp(a.created_at)} · news 7 days · discussion ${a.social_lookback_days || 7} days`}
            {a && watch?.enabled && " · "}
            {watch?.enabled &&
              `watch on, next check ${stamp(watch.next_check_at)}`}
            {a?.social_lookback_days && a.social_lookback_days !== 7
              ? ". This exploratory window does not publish watch alerts."
              : ""}
          </p>
        )}
      </details>
      <NewsStatus
        data={data}
        availability={availability}
        onCoverage={onCoverage}
      />
      <div className="sample-browse-controls">
        <SourceFilters selected={tab} onChange={setTab} />
        <button
          className="evidence-button"
          onClick={() =>
            setEvidenceView(a && !a.withheld ? "saved" : "current")
          }
          aria-haspopup="dialog"
        >
          Evidence
        </button>
      </div>
      {a?.withheld ? (
        <p className="warning">
          This analysis is withheld because source access changed.
        </p>
      ) : sample || (tab === "all" && a) ? (
        <>
          {a.coverage?.input_limits?.notice && (
            <p className="fine">
              Some sources were omitted. Open Evidence to inspect the limits.
            </p>
          )}
          {tab === "all" ? (
            <AllSourceSummary
              analysis={a}
              providerStatus={data.provider_status}
            />
          ) : (
            <>
              <div className="sentiment-summary">
                <strong>{sentimentSummaryLabel(sample)}</strong>
                <span className="sample-reconciliation">
                  {channel === "news"
                    ? `${sample.selected} stories → ${sample.relevant} relevant → ${counts.total} ${a.summary_policy?.startsWith("sentiment-coverage-") ? "distinct developments" : "text groups"}`
                    : `${sample.selected} texts → ${sample.relevant} relevant → ${counts.total} counted groups`}
                </span>
              </div>
              <p className="fine sample-count-explanation">
                {channel === "news"
                  ? "Repeated coverage counts once in these tone totals. "
                  : "Exact repeated text counts once within this platform. "}
                {Math.max(0, sample.selected - sample.relevant)} texts were
                unrelated or relevance-unclear.
                {!counts.reconciled &&
                  " The earlier saved group total differs; the categories below show the recorded counts."}
              </p>
              <div className="sentiment-counts">
                {Object.entries(names).map(([key, label]) => (
                  <span className={`tone-${key}`} key={key}>
                    {label} <b>{sample.counts[key]}</b>
                  </span>
                ))}
              </div>
              <details className="secondary-details sample-method">
                <summary>Sample details &amp; method</summary>
                {Number.isInteger(pool) && (
                  <p className="fine">
                    Available pool: {pool} candidate texts on this source.{" "}
                    {sample.selected} analysed in this saved reading.
                  </p>
                )}
                <p className="fine">
                  Counted relevant text groups:{" "}
                  {sample.counted_groups ?? sample.relevant}.{" "}
                  {channel === "social"
                    ? "Exact repeated text counts once within this platform. Different comments are not necessarily independent opinions."
                    : a.summary_policy?.startsWith("sentiment-coverage-")
                      ? "Related news reports count once per compared development; each original report and its framing remain below. AI grouping can be wrong. Social opinions stay separate."
                      : "Identical substantive news bodies count once even when headlines differ."}{" "}
                  A direction requires a strict majority with at least{" "}
                  {sample.minimum_directional_groups ?? 3} interpretable groups
                  in this saved method.
                </p>
                {channel === "news" &&
                  a.summary_policy?.startsWith("sentiment-coverage-") && (
                    <p className="fine">
                      Compared with {a.coverage?.comparison_news ?? 0}{" "}
                      additional recent news reports, which are not counted in
                      this sample. This is bounded coverage, not a search of
                      every past report.
                    </p>
                  )}
                <p className="fine">
                  Analysed {stamp(a.created_at)} ·{" "}
                  {a.coverage?.selection?.policy === "sentiment-all-eligible-1"
                    ? "every eligible saved source in the date window, split into batches."
                    : "earlier limited sample. Refresh & analyse now covers every eligible saved source in batches."}{" "}
                  {sample.tone === "thin sample"
                    ? "Too few interpretable items for a directional summary."
                    : ""}{" "}
                  {channel === "social"
                    ? `${a.coverage.platform_authors?.[platform] ?? a.coverage.selected_social_authors} distinct ${(a.coverage.platform_authors?.[platform] ?? a.coverage.selected_social_authors) === 1 ? "author" : "authors"} represented. Selected sources: ${sampledFeeds || "none"}. ${platform === "hackernews" ? "Tech-community comments, not investor consensus." : platform === "x" ? "Original X posts, not investor consensus." : "Public Reddit posts and available replies, not investor consensus."} ${a.coverage.parent_contexts || 0} parent messages supplied across this saved analysis as context, not extra votes. Each author's words are classified separately; ambiguous replies may remain unclear.`
                    : "Provider headlines/snippets, not full articles."}
                </p>
                <p>
                  News framing and expressed social opinions are separate
                  samples. They do not measure all investors or predict returns.
                </p>
              </details>
            </>
          )}
          <div className="sentiment-result-controls">
            <label>
              Show{" "}
              <Select
                aria-label="Source relevance"
                value={relevanceFilter}
                onChange={(event) => setRelevanceFilter(event.target.value)}
              >
                <option value="all">All analysed texts</option>
                <option value="relevant">Relevant to company</option>
                <option value="unrelated">Unrelated</option>
                <option value="unclear">Relevance unclear</option>
              </Select>
            </label>
            <span className="fine">
              {filteredItems.length
                ? `${(currentPage - 1) * 12 + 1}–${Math.min(currentPage * 12, filteredItems.length)} of ${filteredItems.length}`
                : "0 matching texts"}{" "}
              · newest first in All
            </span>
          </div>
          {shownItems.length ? (
            <div className="sentiment-items">
              {shownItems.map((i) => {
                const s = a.sources.find((s) => s.id === i.source_id);
                const comparison = coverageLinks.find(
                  (c) => c.source_id === i.source_id,
                );
                const reference =
                  comparison &&
                  a.sources.find(
                    (s) => s.id === comparison.reference_source_id,
                  );
                return (
                  <article
                    key={i.id}
                    className="source-story"
                    data-source-id={i.source_id}
                  >
                    {s && (
                      <div className="sentiment-source-meta fine">
                        <SourceLabel scope={sourceScope(s)}>
                          {s.source}
                        </SourceLabel>
                        <time>
                          {s.timestamp_basis === "feed_updated" &&
                            "Feed updated · "}
                          {stamp(s.published_at)}
                        </time>
                      </div>
                    )}
                    {sourceHeadline(s) && <h3>{sourceHeadline(s)}</h3>}
                    {s?.body ? (
                      <p
                        className={`story-source-text${s.kind === "social" ? " discussion-text" : ""}`}
                      >
                        {s.body}
                      </p>
                    ) : (
                      <p className="fine">Original text unavailable.</p>
                    )}
                    {comparison && (
                      <p className="fine">
                        {comparison.relation === "repeats"
                          ? "Repeated coverage of an earlier development"
                          : comparison.relation === "adds_detail"
                            ? "Adds detail to an earlier report"
                            : "Reports conflict · inspect both sources"}
                      </p>
                    )}
                    <div className="story-footer">
                      <div className="story-labels">
                        <span className="fine">
                          {i.guard?.applied ? "Checked label" : "AI label"}
                        </span>
                        <span className={`sentiment-tag tone-${i.sentiment}`}>
                          {i.relevance === "relevant"
                            ? names[i.sentiment]
                            : i.relevance === "unrelated"
                              ? "Not about this company"
                              : "Unclear relevance"}
                        </span>
                        <span className="story-statement fine">
                          {i.statement.replaceAll("_", " ")}
                        </span>
                      </div>
                      <EvidenceButton
                        key={`${a.id}:${i.id}`}
                        label="Inspect evidence"
                        title="Story evidence"
                      >
                        {sourceHeadline(s) && <h3>{sourceHeadline(s)}</h3>}
                        {s && (
                          <p className="fine">
                            <SourceLabel scope={sourceScope(s)}>
                              {s.source}
                            </SourceLabel>{" "}
                            · {stamp(s.published_at)}
                          </p>
                        )}
                        <div className="story-full-text">
                          <h3>Original text</h3>
                          <p>{s?.body || "Original text unavailable."}</p>
                        </div>
                        <h3>AI classification</h3>
                        <SentimentBasis item={i} />
                        {comparison && (
                          <details className="coverage-comparison">
                            <summary>
                              {comparison.relation === "repeats"
                                ? "Repeated coverage"
                                : comparison.relation === "adds_detail"
                                  ? "New detail on an earlier report"
                                  : "Conflicting reports"}{" "}
                              · compare reports
                            </summary>
                            <p>{comparison.explanation}</p>
                            {!comparison.explanation_policy && (
                              <p className="fine">
                                Earlier AI-written summary. Check each report
                                for the details it supports.
                              </p>
                            )}
                            <p className="fine">
                              AI comparison of supplied snippets; not
                              independent confirmation.{" "}
                              {comparison.review_note ||
                                (comparison.repeat_suppression_allowed
                                  ? "Watches can keep this repeat quiet when the earlier report has already been seen."
                                  : "New detail and contradictions remain eligible for review.")}
                            </p>
                            <strong>This report</strong>
                            {comparison.citations.map((c, j) => (
                              <blockquote key={j}>{c.quote}</blockquote>
                            ))}
                            <button
                              className="source-link"
                              onClick={() => onSource(i.source_id)}
                            >
                              Inspect this report ↗
                            </button>
                            <strong>
                              {reference?.title || "Earlier report"}
                            </strong>
                            {comparison.reference_citations.map((c, j) => (
                              <blockquote key={j}>{c.quote}</blockquote>
                            ))}
                            <button
                              className="source-link"
                              onClick={() =>
                                onSource(comparison.reference_source_id)
                              }
                            >
                              Inspect compared report ↗
                            </button>
                          </details>
                        )}
                        <details>
                          <summary>Why this label · inspect evidence</summary>
                          {!i.evidence_policy &&
                            i.citations.map((c, j) => (
                              <blockquote key={j}>{c.quote}</blockquote>
                            ))}
                          <SentimentContext value={i.conversation} />
                          <button
                            className="source-link"
                            onClick={() => onSource(i.source_id)}
                          >
                            Open original source ↗
                          </button>
                        </details>
                      </EvidenceButton>
                    </div>
                    <SentimentPriceContext
                      values={i.price_comparisons}
                      compact
                    />
                  </article>
                );
              })}
            </div>
          ) : (
            <p className="muted">
              {items.length
                ? "No analysed texts match this relevance filter."
                : "No analysed texts for this source type. Missing coverage is not neutral sentiment."}
            </p>
          )}
          {totalPages > 1 && (
            <nav
              className="sentiment-pagination"
              aria-label="Analysed source pages"
            >
              <button
                disabled={currentPage === 1}
                onClick={() => setPage(currentPage - 1)}
              >
                Previous sources
              </button>
              <span className="fine">
                Page {currentPage} of {totalPages}
              </span>
              <button
                disabled={currentPage === totalPages}
                onClick={() => setPage(currentPage + 1)}
              >
                Next sources
              </button>
            </nav>
          )}
        </>
      ) : (
        <p className="muted">
          No analysis saved for this source yet. Choose Refresh & analyse to
          check sources and read their tone.
        </p>
      )}
      <DiscussionThemes
        key={`${data.instrument.id}:${a?.id || "empty"}`}
        instrumentId={data.instrument.id}
        analysisId={a?.id}
        scope={tab}
        unavailableReason={
          !a
            ? "Analyse a source sample first, then summarise its discussions."
            : a.withheld
              ? "Source access changed. A new summary cannot be created from this sample."
              : busy
                ? "Wait for the current workspace action to finish. Saved readings remain available."
                : availability.state === "running"
                  ? "Another AI request is running. Wait for it to finish before starting a discussion summary. Saved readings remain available."
                  : availability.message
        }
        onRefresh={onThemesChange}
        onSource={onThemeSource}
      />
      {data.sentiment_inputs?.status === "changed" && (
        <div className="evidence-summary-bar">
          <p>
            New source selection available. Saved labels still describe the
            earlier sample.
          </p>
          <button
            className="source-link"
            onClick={() => setEvidenceView("current")}
          >
            Compare current sources
          </button>
        </div>
      )}
      <Modal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        title="News & discussion · watch"
        className="research-dialog"
        keepMounted
      >
        <div className="watch-settings-dialog">
          <label>
            <Checkbox
              disabled={busy}
              checked={!!watch?.enabled}
              onChange={(e) =>
                onWatch(e.target.checked, watch?.interval_minutes || 60)
              }
            />{" "}
            Watch news + social changes
          </label>
          {watch?.enabled && (
            <label>
              Check every{" "}
              <Select
                aria-label="Watch frequency"
                disabled={busy}
                value={watch.interval_minutes}
                onChange={(e) => onWatch(true, Number(e.target.value))}
              >
                <option value={60}>hour</option>
                <option value={240}>4 hours</option>
              </Select>
            </label>
          )}
          {watch?.enabled && (
            <label className="watch-scope">
              Alerts to receive{" "}
              <Select
                aria-label="Alert focus"
                disabled={busy}
                value={
                  watch.match_idea
                    ? watch.idea_purpose === "question"
                      ? "question"
                      : "idea"
                    : "company"
                }
                onChange={(e) =>
                  onWatch(
                    true,
                    watch.interval_minutes,
                    e.target.value !== "company",
                    undefined,
                    e.target.value === "question" ? "question" : "reasoning",
                  )
                }
              >
                <option value="company">
                  Company news and sentiment changes
                </option>
                <option value="idea" disabled={!activeReasoning}>
                  Changes linked to my saved reasoning
                </option>
                <option value="question" disabled={!activeQuestion}>
                  Answers to my saved question
                </option>
              </Select>
            </label>
          )}
          {watch?.enabled && watch.match_idea && (
            <p className="fine">
              {watch.idea_purpose === "question"
                ? "Question-focused checks look for concrete answers to your saved question. They do not alert on inferred investment risks."
                : "Reasoning checks look for support, challenges, specific risks and answers linked to your saved words."}{" "}
              New eligible text uses another private AI request. Quiet results
              stay in history. Changing focus or reasoning starts a quiet
              baseline for future sources; numerical and event conditions stay
              unchanged.
            </p>
          )}
          {watch?.enabled && (
            <div className="watch-settings-group">
              <details className="secondary-details watch-options">
                <summary>Watch settings</summary>
                <div className="watch-settings-body">
                  <details className="event-watch-control">
                    <summary>
                      Original reply context ·{" "}
                      {watch?.include_context
                        ? watch.enabled
                          ? "on"
                          : "paused"
                        : "off"}
                    </summary>
                    <div className="watch-option-body">
                      <label>
                        <Checkbox
                          disabled={
                            busy || (!watch?.enabled && !watch?.include_context)
                          }
                          checked={!!watch?.include_context}
                          onChange={(e) =>
                            onWatch(
                              !!watch?.enabled,
                              watch?.interval_minutes || 60,
                              undefined,
                              e.target.checked,
                            )
                          }
                        />{" "}
                        Check original reply context during watches
                      </label>
                      <p className="fine">
                        Before sentiment analysis, check up to four selected
                        Hacker News replies and their immediate parents. Recent
                        eligible saved context is reused. This adds source
                        requests, not a separate AI call. Parents remain
                        separate evidence and add no sentiment votes. Partial or
                        failed checks appear in Watch check history.
                      </p>
                      <p className="fine">
                        Turning this off stops scheduled parent lookups. New
                        analyses can still use eligible context already saved
                        with a source.
                      </p>
                    </div>
                  </details>
                  <details className="event-watch-control">
                    <summary>
                      Automatic event checks ·{" "}
                      {watch?.event_version_id
                        ? watch.enabled && eventWatchCurrent
                          ? "on"
                          : "paused"
                        : "off"}
                    </summary>
                    <div className="watch-option-body">
                      <label>
                        <Checkbox
                          disabled={
                            busy ||
                            (!watch?.event_version_id &&
                              (!watch?.enabled || !approvedEvents))
                          }
                          checked={!!watch?.event_version_id}
                          onChange={(e) =>
                            onEventWatch(
                              e.target.checked ? data.versions[0].id : null,
                            )
                          }
                        />{" "}
                        Also check my approved event conditions
                      </label>
                      <p className="fine">
                        At each scheduled news check, assess eligible company
                        reports against the exact approved events. Changed
                        inputs can use an additional private AI request.
                        Identical inputs reuse a saved check. Social sentiment
                        does not confirm an event.
                      </p>
                      {!approvedEvents && (
                        <p className="fine">
                          Save and approve event conditions in your idea to use
                          this option.
                        </p>
                      )}
                      {watch?.event_version_id && !eventWatchCurrent && (
                        <div className="warning" role="status">
                          <p>
                            Event checks are paused because the approved
                            revision changed. Review the current conditions
                            before resuming.
                          </p>
                          {approvedEvents && (
                            <button
                              disabled={busy || !watch?.enabled}
                              onClick={() => onEventWatch(data.versions[0].id)}
                            >
                              Use current approved events
                            </button>
                          )}
                        </div>
                      )}
                      {eventWatchCurrent && watch?.enabled && (
                        <p className="fine">
                          Watching approved event revision{" "}
                          {data.versions[0].revision}. Matching reports update
                          conditions in Updates; they remain AI interpretations,
                          not verified events.
                        </p>
                      )}
                    </div>
                  </details>
                  <p className="fine watch-settings-note">
                    Watches run while this app is open and your Mac is awake.
                    New samples use your AI budget; unchanged samples reuse
                    their analysis. Alerts appear in Updates, with optional
                    delivery through your connected Telegram bot.
                  </p>
                </div>
              </details>
              {data.idea_watch_state && watch?.match_idea && (
                <p className="fine">
                  Idea watch:{" "}
                  {data.idea_watch_state.status === "baseline"
                    ? "baseline established; watching future sources"
                    : data.idea_watch_state.status === "quiet"
                      ? "no new reviewable coverage in this sample; repeats remain in the source view"
                      : "last private relevance check saved"}{" "}
                  · {stamp(data.idea_watch_state.last_check_at)}.
                </p>
              )}
              <details className="secondary-details private-check-options">
                <summary>Check against my idea</summary>
                <div className="private-check-body">
                  <div className="sentiment-controls">
                    <label>
                      Check focus{" "}
                      <Select
                        aria-label="Private check focus"
                        disabled={busy}
                        value={checkPurpose}
                        onChange={(e) => setCheckPurpose(e.target.value)}
                      >
                        <option value="reasoning">
                          Connections to my reasoning
                        </option>
                        <option value="question">
                          Answers to my saved question
                        </option>
                      </Select>
                    </label>
                    <button
                      disabled={
                        busy ||
                        !(checkPurpose === "question"
                          ? activeQuestion
                          : activeReasoning) ||
                        !a ||
                        a.withheld ||
                        !modelStatus?.comparison_enabled ||
                        modelStatus?.budget?.unresolved > 0
                      }
                      onClick={() => onCheckIdea(checkPurpose)}
                    >
                      Check this sample against my idea
                    </button>
                  </div>
                  <p className="fine">
                    {checkPurpose === "question"
                      ? "Looks for concrete answers to the saved question below. Related background stays quiet."
                      : "Looks for support, challenges, specific risks and answers linked to your saved reasoning."}{" "}
                    Explicit private AI check · works with a saved draft.
                  </p>
                  {checkPurpose === "question" && activeQuestion && (
                    <blockquote>
                      <span className="section-label">SAVED QUESTION</span>
                      <br />
                      {data.versions[0].question}
                    </blockquote>
                  )}
                </div>
              </details>
            </div>
          )}
        </div>
      </Modal>
      <Modal
        open={Boolean(evidenceView)}
        onClose={() => setEvidenceView(null)}
        title="News & discussion · evidence"
        className="evidence-dialog"
      >
        <div
          className="dialog-view-switch"
          role="group"
          aria-label="Evidence view"
        >
          {[
            ["saved", "Analysed sample"],
            ["current", "Current sources"],
            ["history", "History"],
          ].map(([key, label]) => (
            <button
              key={key}
              aria-pressed={evidenceView === key}
              onClick={() => setEvidenceView(key)}
            >
              {label}
            </button>
          ))}
        </div>
        <details className="secondary-details sentiment-window-info">
          <summary>Source window &amp; limits</summary>
          <p className="fine">
            Refresh & analyse checks news and discussions, then analyses the
            available passages. News covers 7 days. Discussion searches use your
            selected window. Reddit searches for the company and ticker, with up
            to 50 posts and replies from three threads, so a wider window does
            not guarantee more posts. X recent search returns at most 20
            original posts and only covers the last 7 days, including when you
            select 30 days. Automatic watches keep their 7-day window.
          </p>
        </details>
        {evidenceView === "saved" &&
          (a && !a.withheld ? (
            <>
              <SourceFilters
                selected={tab}
                onChange={setTab}
                label="Evidence source type"
              />
              <OriginalSample
                analysis={a}
                channel={channel}
                platform={platform}
                onSource={onSource}
              />
            </>
          ) : (
            <p>
              No permitted saved analysis is available. Current sources can be
              read separately.
            </p>
          ))}
        {evidenceView === "current" && (
          <CurrentSentimentSources
            data={data.sentiment_inputs}
            onSource={onSource}
            expanded
          />
        )}
        {evidenceView === "history" && (
          <>
            <WatchCheckHistory
              instrumentId={data.instrument.id}
              lastCheck={watch?.last_check_at}
            />
            <SentimentHistory
              key={data.instrument.id}
              instrumentId={data.instrument.id}
              latestId={a?.id}
            />
          </>
        )}
      </Modal>
    </section>
  );
}

function AlertEvidence({ item, sources, onSource, comparison }) {
  const source = sources.find((s) => s.id === item.source_id);
  const reference =
    comparison && sources.find((s) => s.id === comparison.reference_source_id);
  return (
    <div className="alert-evidence">
      <strong>{source?.title || "Source unavailable"}</strong>
      <p className="fine">
        {item.sentiment} · {item.statement.replaceAll("_", " ")} ·{" "}
        {source?.source}
      </p>
      <SentimentBasis item={item} />
      <SentimentContext value={item.conversation} />
      {comparison && (
        <details className="coverage-comparison">
          <summary>
            {comparison.relation === "contradicts"
              ? "Conflicting reports"
              : comparison.relation === "adds_detail"
                ? "Added detail"
                : "Changed wording"}{" "}
            · compare with the earlier report
          </summary>
          <p>{comparison.explanation}</p>
          {!comparison.explanation_policy && (
            <p className="fine">
              Earlier AI-written summary. Check each report for the details it
              supports.
            </p>
          )}
          {comparison.review_note && (
            <p className="warning">{comparison.review_note}</p>
          )}
          <p className="fine">
            This comparison does not establish which claim is true or whether
            the earlier report was formally corrected.
          </p>
          <strong>New report · {stamp(source?.published_at)}</strong>
          {comparison.citations.map((c, j) => (
            <blockquote key={j}>{c.quote}</blockquote>
          ))}
          <strong>Earlier report · {stamp(reference?.published_at)}</strong>
          <p>{reference?.title}</p>
          {comparison.reference_citations.map((c, j) => (
            <blockquote key={j}>{c.quote}</blockquote>
          ))}
          <button className="source-link" onClick={() => onSource(reference)}>
            Inspect earlier report ↗
          </button>
        </details>
      )}
      <button className="source-link" onClick={() => onSource(source)}>
        Inspect alert source ↗
      </button>
    </div>
  );
}

export function ResearchAlerts({
  alerts,
  busy,
  onReview,
  onSource,
  onOpen,
  history = false,
  embedded = false,
  readOnly = false,
}) {
  const [filter, setFilter] = useState(history ? "all" : "pending");
  const selected = (alerts || []).filter(
    (a) => embedded || filter === "all" || !a.review_action,
  );
  return (
    <section className="research-alerts" aria-label="News and sentiment alerts">
      {!embedded && (
        <>
          <div className="row">
            <h2>News & sentiment alerts</h2>
            <label>
              Show{" "}
              <Select
                aria-label="Sentiment alert filter"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
              >
                <option value="pending">Awaiting review</option>
                <option value="all">All alerts</option>
              </Select>
            </label>
          </div>
          <p className="fine">
            Company watch alerts flag a change in selected source coverage. They
            do not automatically decide whether your saved idea is right.
          </p>
        </>
      )}
      {!selected.length && (
        <p className="muted">
          No alerts in this view. Enable a company watch and establish a
          baseline; a quiet list does not mean there is no risk.
        </p>
      )}
      {selected.map((a) => (
        <article className="sentiment-alert" key={a.id}>
          <div className="row">
            <strong>{a.symbol}</strong>
            <small>{stamp(a.created_at)}</small>
          </div>
          {a.withheld ? (
            <p className="warning">
              Evidence is currently unavailable; this alert’s interpretation is
              withheld.
            </p>
          ) : (
            <>
              <h3>{a.payload.title}</h3>
              <p>{a.payload.reason}</p>
              <SentimentLimits
                value={a.source_limits?.current}
                label="Current sample"
              />
              <SentimentLimits
                value={a.source_limits?.previous}
                label="Earlier sample"
              />
              {a.payload.shifts?.map((s) => (
                <p key={`${s.channel}:${s.platform || "legacy"}`}>
                  {s.channel === "news"
                    ? "News"
                    : s.platform === "hackernews"
                      ? "Hacker News"
                      : s.platform === "reddit"
                        ? "Reddit"
                        : s.platform === "x"
                          ? "X"
                          : "Social"}
                  : {s.before.tone} → {s.after.tone} · {s.before.selected} →{" "}
                  {s.after.selected} selected items
                </p>
              ))}
              {a.payload.items?.slice(0, 2).map((i) => (
                <AlertEvidence
                  key={i.source_id}
                  item={i}
                  sources={a.sources}
                  onSource={onSource}
                  comparison={a.payload.coverage_links?.find(
                    (c) => c.source_id === i.source_id,
                  )}
                />
              ))}
              {a.payload.items?.length > 2 && (
                <details>
                  <summary>
                    Inspect {a.payload.items.length - 2} more changed sources
                  </summary>
                  {a.payload.items.slice(2).map((i) => (
                    <AlertEvidence
                      key={i.source_id}
                      item={i}
                      sources={a.sources}
                      onSource={onSource}
                      comparison={a.payload.coverage_links?.find(
                        (c) => c.source_id === i.source_id,
                      )}
                    />
                  ))}
                </details>
              )}
              <details>
                <summary>
                  Previous sample · {stamp(a.payload.previous_cutoff)}
                </summary>
                {a.previous_items?.map((i) => (
                  <AlertEvidence
                    key={i.source_id}
                    item={i}
                    sources={a.previous_sources}
                    onSource={onSource}
                  />
                ))}
              </details>
              {a.payload.saved_idea && (
                <details>
                  <summary>
                    Your reasoning when this alert was created · revision{" "}
                    {a.payload.saved_idea.revision}
                  </summary>
                  <strong>{a.payload.saved_idea.question}</strong>
                  <p>{a.payload.saved_idea.reasoning}</p>
                  <p className="fine">
                    This alert is based on company-source changes, not an AI
                    verdict on this reasoning.
                  </p>
                </details>
              )}
              <button onClick={() => onOpen(a.instrument_id, "idea")}>
                Review my idea ↗
              </button>
            </>
          )}
          {a.review_action ? (
            <p className="fine">
              {a.review_action === "reviewed" ? "Reviewed" : "Left unresolved"}
            </p>
          ) : (
            !readOnly && (
              <div className="sentiment-controls">
                <button
                  disabled={busy}
                  onClick={() => onReview(a.id, "reviewed")}
                >
                  Mark reviewed
                </button>
                <button
                  disabled={busy}
                  onClick={() => onReview(a.id, "unresolved")}
                >
                  Leave unresolved
                </button>
              </div>
            )
          )}
        </article>
      ))}
    </section>
  );
}
