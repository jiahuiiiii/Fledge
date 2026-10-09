import SourceFilters, { SourceLabel, sourceScope } from "./SourceFilters";
import { originalSample } from "../lib/originalSample";
import { sourceHeadline } from "../lib/sourceHeadline";
import SentimentLimits from "./SentimentLimits";
import { useEffect, useState } from "react";
import { stamp } from "./MarketResearch";
import { sourceExclusionLabels } from "../lib/sourceCoverage";

const states = {
  changed: "The inputs selected now differ from the saved sentiment reading.",
  same: "The selected sources and parent context match the saved reading. Its original labels are unchanged.",
  empty:
    "No complete recent passages are currently eligible for sentiment analysis.",
  no_saved_reading:
    "Sources are available to read before your first sentiment analysis.",
  saved_reading_withheld:
    "The saved reading is unavailable. You can separately inspect currently permitted sources.",
};

export default function CurrentSentimentSources({
  data,
  onSource,
  expanded = false,
  inline = false,
  scope,
}) {
  const [localScope, setSelected] = useState("all");
  const selected = scope || localScope;
  const [page, setPage] = useState(1);
  useEffect(() => setPage(1), [selected, data?.as_of]);
  if (!data) return null;
  const sources =
    selected === "all"
      ? originalSample({ sources: data.sources }, "all")
      : data.sources.filter((source) => sourceScope(source) === selected);
  const scopes = ["news", "reddit", "hackernews", "x"]
    .map((scope) => data.scopes[scope])
    .filter(Boolean);
  const counts =
    selected === "all"
      ? Object.fromEntries(
          [
            "selected",
            "available",
            "added",
            "no_longer_selected",
            "retained",
          ].map((key) => [
            key,
            scopes.every((scope) => Number.isInteger(scope[key]))
              ? scopes.reduce((total, scope) => total + scope[key], 0)
              : null,
          ]),
        )
      : data.scopes[selected];
  const exclusions = Object.entries(data.selection?.scopes || {}).filter(
    ([scope, sample]) =>
      (selected === "all" || scope === selected) &&
      Object.values(sample.excluded || {}).some((count) => count > 0),
  );
  const totalPages = Math.max(1, Math.ceil(sources.length / 6));
  const currentPage = Math.min(page, totalPages);
  const shown = inline
    ? sources.slice((currentPage - 1) * 6, currentPage * 6)
    : sources;
  const Container = inline ? "div" : "details";
  return (
    <section
      className={`original-sample${inline ? " collected-source-reading" : ""}`}
      aria-label={
        inline ? "Collected news and discussion" : "Current sentiment inputs"
      }
    >
      {!inline && <p role="status">{states[data.status]}</p>}
      {!inline && <SentimentLimits value={data.input_limits} />}
      <Container {...(!inline ? { open: expanded || undefined } : {})}>
        {!inline && (
          <summary>
            Read current sources · {data.sources.length} eligible
          </summary>
        )}
        <div className="source-preview-content">
          {inline && (
            <p className="fine" role="status">
              {sources.length} collected{" "}
              {sources.length === 1 ? "source" : "sources"} in this view ·
              original wording, not yet analysed for tone or relevance.
            </p>
          )}
          {!inline && (
            <>
              {data.status === "changed" && (
                <p className="fine">
                  Saved labels still describe the earlier sample. A different
                  source selection is not a measured change in market sentiment.
                </p>
              )}
              <p className="fine">
                Selection as of {stamp(data.as_of)}, from locally saved sources
                in the selected window. Opening this preview makes no source or
                AI request. Source checks may be older; inspect their dates and
                coverage.
              </p>
              {data.saved_cutoff && (
                <p className="fine">
                  Saved sentiment source cutoff {stamp(data.saved_cutoff)}.
                </p>
              )}
              <SourceFilters
                selected={selected}
                onChange={setSelected}
                label="Current source type"
              />
              <p className="fine">
                {counts.selected} eligible from {counts.available} available
                candidate texts. Every eligible candidate will be analysed in
                batches. Relevance has not been assessed in this preview.
              </p>
              {exclusions.length > 0 && (
                <details className="secondary-details">
                  <summary>Excluded before analysis</summary>
                  {exclusions.map(([scope, sample]) => (
                    <p key={scope}>
                      <SourceLabel scope={scope} />:{" "}
                      {Object.entries(sample.excluded)
                        .map(
                          ([reason, count]) =>
                            `${sourceExclusionLabels[reason] || reason}: ${count}`,
                        )
                        .join(" · ")}
                    </p>
                  ))}
                  <p className="fine">
                    These texts receive no sentiment label. Original saved
                    sources remain available in Data &amp; sources.
                  </p>
                </details>
              )}
              {counts.added != null && (
                <p className="fine">
                  Compared with the saved sample: {counts.added} not previously
                  selected, {counts.no_longer_selected} no longer selected,{" "}
                  {counts.retained} retained. These are source-version
                  differences, not counts of new events.
                </p>
              )}
              {!!data.parents_changed && (
                <p className="fine">
                  Saved parent context differs for {data.parents_changed}{" "}
                  retained replies. This can reflect availability or age as well
                  as changed wording.
                </p>
              )}
              {data.comparison_sources_changed && (
                <p className="fine">
                  The additional news-comparison pool also differs. Its reports
                  are not counted or shown as selected sentiment sources here.
                </p>
              )}
              {selected === "hackernews" && (
                <p className="fine">
                  Tech-community replies are not representative investor
                  sentiment. Open a source to inspect its separately saved
                  original parent.
                </p>
              )}
            </>
          )}
          {!sources.length && (
            <p>
              No selected texts for this source type. Missing coverage is not
              neutral sentiment.
            </p>
          )}
          {shown.map((s) => (
            <article key={s.id}>
              <div className="row">
                <span className="fine">
                  <SourceLabel scope={sourceScope(s)}>{s.source}</SourceLabel>
                </span>
                <time>
                  {s.timestamp_basis === "feed_updated" && "Feed updated · "}
                  {stamp(s.published_at)}
                </time>
              </div>
              {sourceHeadline(s) && <h3>{sourceHeadline(s)}</h3>}
              {!inline && (
                <p className="fine">
                  First available here {stamp(s.available_at)}
                  {s.in_saved_sample === false
                    ? " · not in the saved selected sample"
                    : ""}
                  {s.has_parent_context
                    ? " · eligible saved parent context"
                    : ""}
                  .
                </p>
              )}
              <p className="original-source-text">{s.body}</p>
              <button className="source-link" onClick={() => onSource(s.id)}>
                Inspect current source ↗
              </button>
            </article>
          ))}
          {inline && totalPages > 1 && (
            <nav
              className="sentiment-pagination"
              aria-label="Collected source pages"
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
          {!inline && (
            <p className="fine">
              These supplied snippets and posts have no AI labels in this view.
              A mention may be unrelated to the company; public opinions and
              secondary reporting are not verified facts.
            </p>
          )}
        </div>
      </Container>
    </section>
  );
}
