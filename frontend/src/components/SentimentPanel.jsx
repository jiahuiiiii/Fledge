import { NewsFreshness, NewsStatusDetails } from "./NewsStatus";
import {
  Badge,
  Button,
  Card,
  ChartIcon,
  Disclosure,
  MetaRow,
  Pagination,
  SectionHeader,
  SourceChip,
  Tabs,
  TabsList,
  TabsTrigger,
  ToneCard,
} from "./ui";
import { toneOf } from "../lib/tone";
import { countedTone } from "../lib/newsPresentation";
import { modelAvailability } from "../lib/modelAvailability";
import {
  sampleWithheld,
  sourceCoverage,
  withheldAlertNote,
  withheldSourcesNote,
} from "../lib/sourceCoverage";
import Checkbox from "./Checkbox";
import Select from "./Select";
import SentimentLimits from "./SentimentLimits";
import SentimentBasis from "./SentimentBasis";
import SentimentPriceContext from "./SentimentPriceContext";
import { sentimentSummaryParts } from "../lib/sentimentSummary";
import DiscussionThemes from "./DiscussionThemes";
import SentimentContext, { RedditThreadContext } from "./SentimentContext";
import OriginalSample from "./OriginalSample";
import CurrentSentimentSources from "./CurrentSentimentSources";
import WatchCheckHistory from "./WatchCheckHistory";
import { watchFrequencyLabel } from "../lib/watchLanes";
import SentimentHistory from "./SentimentHistory";
import SourceFilters from "./SourceFilters";
import AllSourceSummary, {
  SourceCountingDetails,
  SourceToneSummary,
} from "./AllSourceSummary";
import ToneFilters, { toneNames as names } from "./ToneFilters";
import { originalSample } from "../lib/originalSample";
import { sourceHeadline } from "../lib/sourceHeadline";
import "./NewsDiscussion.css";
import { useEffect, useId, useState } from "react";
import Modal from "./Modal";
import EvidenceButton from "./EvidenceButton";
import { stamp } from "./MarketResearch";
import "./AlertEvidence.css";
import { api } from "../api/client";
import { loadPreviousSample, savedPreviousSample } from "../lib/previousSample";
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
  const [tab, setTab] = useState("all");
  const relevanceFilter = "relevant";
  const [toneFilter, setToneFilter] = useState("all");
  const sourceListId = useId();
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
  const coverage = a && !a.withheld ? sourceCoverage(a) : null;
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
  useEffect(() => setPage(1), [a?.id, tab, relevanceFilter, toneFilter]);
  function filterTone(value) {
    setToneFilter(value);
    setPage(1);
  }
  const filteredItems = items.filter(
    (item) =>
      (relevanceFilter === "all" || item.relevance === relevanceFilter) &&
      (toneFilter === "all" ||
        (item.relevance === "relevant" && item.sentiment === toneFilter)),
  );
  const totalPages = Math.max(1, Math.ceil(filteredItems.length / 6));
  const currentPage = Math.min(page, totalPages);
  const shownItems = filteredItems.slice(
    (currentPage - 1) * 6,
    currentPage * 6,
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
    <Card className="sentiment-panel" aria-label="News and social sentiment">
      <SectionHeader
        icon={<ChartIcon />}
        title="What’s the tone?"
        description="Read each source’s tone, then explore the evidence behind it."
      />
      <div className="sentiment-heading-actions">
        <label className="sentiment-window">
          <span>Discussion window</span>
          <Select
            aria-label="Discussion window"
            value={days}
            disabled={!!loadingRun?.active}
            onChange={(e) => setDays(Number(e.target.value))}
          >
            <option value={1}>Past 24 hours</option>
            <option value={7}>Past 7 days</option>
            <option value={30}>Past 30 days</option>
          </Select>
        </label>
        <Button
          variant="plain"
          className="sentiment-watch-button"
          data-enabled={!!watch?.enabled}
          aria-haspopup="dialog"
          onClick={() => setSettingsOpen(true)}
        >
          <span className="sentiment-watch-dot" aria-hidden="true" />
          Watch · {watch?.enabled ? "on" : "off"}
        </Button>
        <Button
          className="sentiment-analyse-button"
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
        </Button>
      </div>
      {disabledReason && (
        <p
          id="sentiment-disabled-reason"
          className="sentiment-disabled-reason"
          role="status"
        >
          {disabledReason}
        </p>
      )}
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
                width: `${batchProgress.total ? (batchProgress.completed / batchProgress.total) * 100 : 0}%`,
              }}
            />
          </div>
          {!loadingRun.active && (
            <p className="fine">
              Refresh &amp; analyse reuses completed batches when their sources
              and context are unchanged.
            </p>
          )}
          {!loadingRun.active && batchProgress.failure?.split_available && (
            <Button
              variant="plain"
              disabled={availability.blocked}
              onClick={() => onAnalyze(days, { split_failed: true })}
            >
              Retry with smaller batches · paid AI
            </Button>
          )}
        </div>
      )}
      <NewsFreshness data={data} />
      <p className="fine sentiment-reading-limit">
        Tone describes what people and publishers said, not facts, investor consensus or future returns.
      </p>
      <div className="sample-browse-controls">
        <SourceFilters selected={tab} onChange={setTab} showLabels />
        <Button
          variant="tertiary"
          size="sm"
          className="evidence-button"
          onClick={() =>
            setEvidenceView(
              a && !a.withheld && data.sentiment_inputs?.status !== "changed"
                ? "saved"
                : "current",
            )
          }
          aria-haspopup="dialog"
        >
          Evidence
          {data.sentiment_inputs?.status === "changed" && (
            <Badge title="Saved sources have changed since this reading">Sources changed</Badge>
          )}
        </Button>
      </div>
      {a?.withheld ? (
        <>
          <p className="warning">
            This analysis is withheld because source access changed.
          </p>
          <CurrentSentimentSources
            data={data.sentiment_inputs}
            onSource={onSource}
            inline
            scope={tab}
          />
        </>
      ) : sample || (tab === "all" && a) ? (
        <>
          {tab === "all" ? (
            <>
              <SourceToneSummary analysis={a} />
              <Disclosure variant="flush" className="secondary-details" title="Source coverage" description="How sources are counted, what was unavailable and reading limits">
                <AllSourceSummary
                  analysis={a}
                  providerStatus={data.provider_status}
                  showDetails={false}
                />
                <SourceCountingDetails analysis={a} />
                <div className="coverage-notes">
                  {a.repairs?.repaired > 0 && <p className="fine">{`${a.repairs.repaired} of ${a.repairs.total} labels needed repair: the AI's label and its evidence disagreed.`}</p>}
                  {a.stale && <p className="fine">This reading uses a source sample captured over 24 hours ago; newer headlines may not be included.</p>}
                  {a.earlier_method && <p className="fine">Saved with an earlier analysis method.</p>}
                  {coverage && !coverage.complete && <p className="fine">{coverage.unanalysed > 0 ? "Some saved sources are outside this reading." : "Complete coverage of the saved sources is not established."}</p>}
                  {a.coverage?.input_limits?.notice && <p className="fine">Some sources were omitted from the reading.</p>}
                  {withheldSourcesNote(a) && <p className="fine">{withheldSourcesNote(a)}</p>}
                  {watch?.enabled && <p className="fine">Watch on · next check {stamp(watch.next_check_at)}</p>}
                </div>
                <NewsStatusDetails data={data} availability={availability} onCoverage={onCoverage} />
                <p className="fine">Re-reading every saved source with the current model is a new paid reading; earlier readings stay in History.</p>
                <Button variant="plain" size="sm" disabled={!!loadingRun?.active || availability.blocked} onClick={() => onAnalyze(days, { reread: true })}>Re-read everything · paid AI</Button>
              </Disclosure>
              <ToneFilters
                selected={toneFilter}
                onChange={filterTone}
                controls={sourceListId}
              />
            </>
          ) : (
            <>
              <ToneCard as="div" tone={toneOf(sample.tone)} className="sentiment-summary">
                <strong className="ui-tone-card__status"><span className="ui-tone-card__dot" aria-hidden="true" />{sentimentSummaryParts(sample).label.replace(/^./, (c) => c.toUpperCase())}</strong>
                <small className="tone-detail">
                  {sentimentSummaryParts(sample).detail}
                </small>
                <span className="sample-reconciliation">
                  {channel === "news"
                    ? `${sample.selected} stories → ${sample.relevant} relevant → ${counts.total} ${a.summary_policy?.startsWith("sentiment-coverage-") ? "distinct developments" : "text groups"}`
                    : `${sample.selected} texts → ${sample.relevant} relevant → ${counts.total} counted groups`}
                </span>
              </ToneCard>
              <p className="fine sample-count-explanation">
                {channel === "news"
                  ? "Repeated coverage counts once in these tone totals. "
                  : "Exact repeated text counts once within this platform. "}
                {Math.max(0, sample.selected - sample.relevant)} texts were
                unrelated or relevance-unclear.
                {!counts.reconciled &&
                  " The earlier saved group total differs; the categories below show the recorded counts."}
              </p>
              <ToneFilters
                selected={toneFilter}
                onChange={filterTone}
                counts={sample.counts}
                controls={sourceListId}
              />
            </>
          )}
          <div className="sentiment-source-list" id={sourceListId}>
            {toneFilter !== "all" && (
              <p className="fine" role="status">
                Showing {names[toneFilter].toLowerCase()} source labels. Tone
                totals above count groups; this list keeps each matching source.
              </p>
            )}
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
                    <Card
                      as="article"
                      variant="flush"
                      key={i.id}
                      className="source-story"
                      data-source-id={i.source_id}
                    >
                      {s && (
                        <MetaRow className="sentiment-source-meta fine">
                          <SourceChip
                            label={s.source}
                            date={`${s.timestamp_basis === "feed_updated" ? "Feed updated · " : ""}${stamp(s.published_at)}`}
                            href={s.url}
                            onOpen={() => onSource(i.source_id)}
                          />
                        </MetaRow>
                      )}
                      {sourceHeadline(s) && (
                        <h3>
                          {s?.url ? (
                            <a href={s.url} target="_blank" rel="noopener noreferrer">
                              {sourceHeadline(s)}
                            </a>
                          ) : (
                            sourceHeadline(s)
                          )}
                        </h3>
                      )}
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
                            {i.prefilter
                              ? "Quick check"
                              : i.guard?.applied
                                ? "Checked label"
                                : "AI label"}
                          </span>
                          <Badge
                            tone={
                              i.relevance === "relevant"
                                ? i.sentiment
                                : "unknown"
                            }
                          >
                            {i.relevance === "relevant"
                              ? names[i.sentiment]
                              : i.relevance === "unrelated"
                                ? "Not about this company"
                                : "Unclear relevance"}
                          </Badge>
                          {!i.prefilter && (
                            <span className="story-statement fine">
                              {i.statement.replaceAll("_", " ")}
                            </span>
                          )}
                        </div>
                        <EvidenceButton
                          key={`${a.id}:${i.id}`}
                          label="Why this label"
                          title={sourceHeadline(s) || "Why this label"}
                        >
                          <h3>
                            {i.prefilter ? "Quick check" : "AI classification"}
                          </h3>
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
                              <Button
                                variant="plain"
                                className="source-link"
                                onClick={() => onSource(i.source_id)}
                              >
                                Inspect this report ↗
                              </Button>
                              <strong>
                                {reference?.title || "Earlier report"}
                              </strong>
                              {comparison.reference_citations.map((c, j) => (
                                <blockquote key={j}>{c.quote}</blockquote>
                              ))}
                              <Button
                                variant="plain"
                                className="source-link"
                                onClick={() =>
                                  onSource(comparison.reference_source_id)
                                }
                              >
                                Inspect compared report ↗
                              </Button>
                            </details>
                          )}
                          {!i.evidence_policy &&
                            i.citations.map((c, j) => (
                              <blockquote key={j}>{c.quote}</blockquote>
                            ))}
                          <SentimentContext value={i.conversation} />
                          <RedditThreadContext value={i.thread_context} />
                          {s && (
                            <SourceChip
                              label="Open original source"
                              href={s.url}
                              onOpen={() => onSource(i.source_id)}
                            />
                          )}
                        </EvidenceButton>
                      </div>
                      <SentimentPriceContext
                        values={i.price_comparisons}
                        compact
                      />
                    </Card>
                  );
                })}
              </div>
            ) : (
              <p className="muted">
                {items.length
                  ? "No analysed texts match these filters."
                  : "No analysed texts for this source type. Missing coverage is not neutral sentiment."}
              </p>
            )}
            {totalPages > 1 && (
              <Pagination
                className="sentiment-pagination"
                label="Analysed source pages"
                page={currentPage}
                totalPages={totalPages}
                previousLabel="Previous sources"
                nextLabel="Next sources"
                onPrevious={() => setPage(currentPage - 1)}
                onNext={() => setPage(currentPage + 1)}
              />
            )}
          </div>
          {tab === "all" ? null : (
            <details className="secondary-details sample-method">
              <summary>Sample details &amp; method</summary>
              {Number.isInteger(pool) && (
                <p className="fine">
                  Saved sources on this platform: {pool}. {sample.selected}{" "}
                  analysed in this saved reading.
                </p>
              )}
              <p className="fine">
                Distinct reports or posts counted:{" "}
                {sample.counted_groups ?? sample.relevant}.{" "}
                {channel === "social"
                  ? "Exact repeated text counts once within this platform. Different comments are not necessarily independent opinions."
                  : a.summary_policy?.startsWith("sentiment-coverage-")
                    ? "Related news reports count once per compared development; each original report and its framing remain below. AI grouping can be wrong. Social opinions stay separate."
                    : "Identical substantive news bodies count once even when headlines differ."}{" "}
                A positive or negative overall tone needs more than half of the
                items with a clear tone to agree, and at least{" "}
                {sample.minimum_directional_groups ?? 3} items with a clear
                tone.
              </p>
              {channel === "news" &&
                a.summary_policy?.startsWith("sentiment-coverage-") && (
                  <p className="fine">
                    Compared with {a.coverage?.comparison_news ?? 0} additional
                    recent news reports, which are not counted in this sample.
                    Older reports outside this selection were not checked.
                  </p>
                )}
              <p className="fine">
                Analysed {stamp(a.created_at)} ·{" "}
                {a.coverage?.selection?.policy === "sentiment-all-eligible-1"
                  ? "all usable saved sources in the date window."
                  : "a limited selection of saved sources. A new analysis can include every usable saved source."}{" "}
                {sample.tone === "thin sample"
                  ? "Too few items have a clear tone to describe the overall mood."
                  : ""}{" "}
                {channel === "social"
                  ? `${a.coverage.platform_authors?.[platform] ?? a.coverage.selected_social_authors} distinct ${(a.coverage.platform_authors?.[platform] ?? a.coverage.selected_social_authors) === 1 ? "author" : "authors"} represented. Selected sources: ${sampledFeeds || "none"}. ${platform === "hackernews" ? "Tech-community comments, not investor consensus." : platform === "x" ? "Original X posts, not investor consensus." : "Public Reddit posts and available replies, not investor consensus."} ${a.coverage.parent_contexts || 0} parent messages supplied across this saved analysis as context, not extra votes. Each author's words are classified separately; ambiguous replies may remain unclear.`
                  : "Provider headlines/snippets, not full articles."}
              </p>
              {channel === "social" &&
                platform === "reddit" &&
                a.coverage?.reddit_threads > 0 && (
                  <p className="fine">
                    Saved topics and comments were read together. Labels
                    describe each author's own words. Only part of each Reddit
                    discussion is available; unknown reply parents and omitted
                    messages are shown with the label evidence.
                  </p>
                )}
              <p>
                News framing and expressed social opinions are separate samples.
                They do not measure all investors or predict returns.
              </p>
            </details>
          )}
        </>
      ) : (
        <>
          <p className="muted">
            {a && sampleWithheld(a, platform || channel)
              ? "This source's saved tone totals are withheld because they counted a source that is no longer available. Its remaining items are listed under All sources; choose Refresh & analyse for a new reading."
              : disabledReason
                ? "Tone analysis is not available yet. You can read the collected sources below."
                : "No tone analysis saved for this source yet. Read the collected sources below, or choose Refresh & analyse."}
          </p>
          <CurrentSentimentSources
            data={data.sentiment_inputs}
            onSource={onSource}
            inline
            scope={tab}
          />
        </>
      )}
      {a && (
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
                : a.withheld_sources > 0
                  ? "Some saved sources in this sample are no longer available. Choose Refresh & analyse before creating a new summary."
                  : busy
                    ? "Wait for the current workspace action to finish. Saved readings remain available."
                    : availability.state === "running"
                      ? "Another AI request is running. Wait for it to finish before starting a discussion summary. Saved readings remain available."
                      : availability.blocked
                        ? availability.message
                        : ""
          }
          onRefresh={onThemesChange}
          onSource={onThemeSource}
        />
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
                onWatch(e.target.checked, watch?.interval_minutes || 240)
              }
            />{" "}
            Watch news + social changes
          </label>
          {watch?.enabled && (
            <label>
              {watchFrequencyLabel(watch)}{" "}
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
          {watch?.enabled && watch?.lanes_enabled && (
            <p className="fine">
              News checks run every 15 minutes from one hour before the US
              session until one hour after it, and hourly otherwise. Discussions
              use the frequency above.
              {watch.fast_check?.last_check_at && (
                <> Last news check: {stamp(watch.fast_check.last_check_at)}.</>
              )}
              {watch.fast_check?.error && (
                <span className="warning"> {watch.fast_check.error}</span>
              )}
            </p>
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
                              watch?.interval_minutes || 240,
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
                            <Button
                              variant="plain"
                              disabled={busy || !watch?.enabled}
                              onClick={() => onEventWatch(data.versions[0].id)}
                            >
                              Use current approved events
                            </Button>
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
                    <Button
                      variant="plain"
                      disabled={
                        busy ||
                        !(checkPurpose === "question"
                          ? activeQuestion
                          : activeReasoning) ||
                        !a ||
                        a.withheld ||
                        a.withheld_sources > 0 ||
                        !modelStatus?.comparison_enabled
                      }
                      onClick={() => onCheckIdea(checkPurpose)}
                    >
                      Check this sample against my idea
                    </Button>
                  </div>
                  <p className="fine">
                    {checkPurpose === "question"
                      ? "Looks for concrete answers to the saved question below. Related background stays quiet."
                      : "Looks for support, challenges, specific risks and answers linked to your saved reasoning."}{" "}
                    Explicit private AI check · works with a saved draft.
                  </p>
                  {a?.withheld_sources > 0 && (
                    <p className="fine">
                      Some saved sources in this sample are no longer available.
                      Choose Refresh & analyse before checking it against your
                      idea.
                    </p>
                  )}
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
        <Tabs value={evidenceView} onValueChange={setEvidenceView}>
          <TabsList variant="line" aria-label="Evidence view">
            <TabsTrigger value="saved">Analysed sample</TabsTrigger>
            <TabsTrigger value="current">Current sources</TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
          </TabsList>
        </Tabs>
        <p className="evidence-view-note">
          {evidenceView === "saved"
            ? "The exact sources the AI read for this tone reading."
            : evidenceView === "current"
              ? data.sentiment_inputs?.status === "changed"
                ? "What is saved now. Sources added or changed since the reading are not in its tone yet."
                : "What is saved now, which matches the reading."
              : "Earlier readings and watch checks."}
        </p>
        <Disclosure variant="flush" title="Source window and limits" className="sentiment-window-info">
          <p className="fine">
            Refresh &amp; analyse checks news and discussions, then analyses the
            available passages. News covers 7 days. Discussion searches use your
            selected window. Reddit searches for the company and ticker, with up
            to 50 posts and replies from three threads, so a wider window does
            not guarantee more posts. X recent search returns at most 20
            original posts and only covers the last 7 days, including when you
            select 30 days. Automatic watches keep their 7-day window.
          </p>
        </Disclosure>
        {evidenceView === "saved" &&
          (a && !a.withheld ? (
            <>
              <SourceFilters
                selected={tab}
                onChange={setTab}
                label="Evidence source type"
                showLabels
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
    </Card>
  );
}

function AlertEvidence({ item, sources, onSource, comparison }) {
  const source = sources.find((s) => s.id === item.source_id);
  const reference =
    comparison && sources.find((s) => s.id === comparison.reference_source_id);
  const importanceQuotes = (item.importance?.citations || []).filter(
    (c) =>
      c.source_id === item.source_id &&
      !(item.citations || []).some((old) => old.quote === c.quote),
  );
  const tone = item.sentiment || "unclear";
  return (
    <div className="alert-evidence alert-evidence-compact">
      <div className="alert-evidence-head">
        <span className={`alert-tone tone-${tone}`}>
          {tone.charAt(0).toUpperCase() + tone.slice(1)}
        </span>
        <strong>{source?.title || "Source unavailable"}</strong>
      </div>
      <p className="alert-evidence-meta">
        {[
          item.statement?.replaceAll("_", " "),
          source?.source,
          item.importance &&
            `${item.importance.level} importance${item.importance.category ? ` (${item.importance.category.replaceAll("_", " ")})` : ""}`,
        ]
          .filter(Boolean)
          .join(" · ")}
        <Button
          variant="plain"
          className="source-link"
          onClick={() => onSource(source)}
        >
          Inspect source ↗
        </Button>
      </p>
      <SentimentBasis item={item} compact />
      {(item.explanation || importanceQuotes.length > 0) && (
        <details className="alert-why">
          <summary>Why this label</summary>
          {item.explanation && <p>{item.explanation}</p>}
          {item.importance && (
            <p>
              Importance is assessed separately from tone:{" "}
              {item.importance.level}
              {item.importance.category
                ? ` · ${item.importance.category.replaceAll("_", " ")}`
                : ""}
              .
            </p>
          )}
          {importanceQuotes.map((c, i) => (
            <blockquote key={i}>{c.quote}</blockquote>
          ))}
        </details>
      )}
      <SentimentContext value={item.conversation} />
      <RedditThreadContext value={item.thread_context} />
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
          <Button
            variant="plain"
            className="source-link"
            onClick={() => onSource(reference)}
          >
            Inspect earlier report ↗
          </Button>
        </details>
      )}
    </div>
  );
}

// Loads the alert's earlier sample once, when the section is first opened.
function PreviousSample({ alert, onSource }) {
  const [sample, setSample] = useState(() => savedPreviousSample(alert));
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    setSample(savedPreviousSample(alert));
    setError(null);
  }, [alert.id]);
  async function load() {
    if (sample || loading) return;
    setLoading(true);
    setError(null);
    try {
      setSample(await loadPreviousSample(api, alert.id));
    } catch (failure) {
      setError(failure.message || "The earlier sample could not be loaded.");
    } finally {
      setLoading(false);
    }
  }
  return (
    <details onToggle={(event) => event.currentTarget.open && load()}>
      <summary>
        Previous sample · {stamp(alert.payload.previous_cutoff)}
      </summary>
      {sample?.withheld ? (
        <p className="warning">
          Evidence is currently unavailable; this earlier sample is withheld.
        </p>
      ) : sample ? (
        sample.items.map((i) => (
          <AlertEvidence
            key={i.source_id}
            item={i}
            sources={sample.sources}
            onSource={onSource}
          />
        ))
      ) : error ? (
        <p className="warning" role="alert">
          {error}{" "}
          <Button variant="plain" type="button" onClick={load}>
            Try again
          </Button>
        </p>
      ) : (
        <p className="muted" aria-live="polite">
          Loading the earlier sample…
        </p>
      )}
    </details>
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
              {a.preview && !embedded && (
                <p className="fine">Preview · not sent to Telegram</p>
              )}
              <h3>{a.payload.title}</h3>
              <p>{a.payload.reason}</p>
              {withheldAlertNote(a) && (
                <p className="fine">{withheldAlertNote(a)}</p>
              )}
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
              <PreviousSample alert={a} onSource={onSource} />
              <p className="fine alert-ai-note">
                Tone, importance and quoted excerpts are AI interpretations of
                each source. Open a source to check it.
              </p>
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
              <Button
                variant="plain"
                onClick={() => onOpen(a.instrument_id, "idea")}
              >
                Review my idea ↗
              </Button>
            </>
          )}
          {a.review_action ? (
            <p className="fine">
              {a.review_action === "reviewed" ? "Reviewed" : "Left unresolved"}
            </p>
          ) : (
            !readOnly && (
              <div className="sentiment-controls">
                <Button
                  variant="plain"
                  disabled={busy}
                  onClick={() => onReview(a.id, "reviewed")}
                >
                  Mark reviewed
                </Button>
                <Button
                  variant="plain"
                  disabled={busy}
                  onClick={() => onReview(a.id, "unresolved")}
                >
                  Leave unresolved
                </Button>
              </div>
            )
          )}
        </article>
      ))}
    </section>
  );
}
