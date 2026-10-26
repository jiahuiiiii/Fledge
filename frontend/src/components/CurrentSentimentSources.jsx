import SourceFilters, { SourceLabel, sourceScope } from "./SourceFilters";
import { originalSample } from "../lib/originalSample";
import { sourceHeadline } from "../lib/sourceHeadline";
import SentimentLimits from "./SentimentLimits";
import { useEffect, useState } from "react";
import { stamp } from "./MarketResearch";
import { sourceExclusionLabels } from "../lib/sourceCoverage";
import { Button, Card, Disclosure, MetaRow, SourceChip } from "./ui";

const states = {
  changed: "The inputs selected now differ from the saved sentiment reading.",
  same: "The selected sources and discussion context match the saved reading. Its original labels are unchanged.",
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
  const Container = "div";
  return (
    <section
      className={`original-sample${inline ? " collected-source-reading" : ""}`}
      aria-label={
        inline ? "Collected news and discussion" : "Current sentiment inputs"
      }
    >
      {!inline && <p role="status">{states[data.status]}</p>}
      {!inline && <SentimentLimits value={data.input_limits} />}
      <Container>
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
              <SourceFilters
                selected={selected}
                onChange={setSelected}
                label="Current source type"
                showLabels
              />
              <p className="evidence-counts">
                {counts.selected} eligible from {counts.available} saved texts
                {counts.added != null &&
                  ` · ${counts.added} new since the reading, ${counts.no_longer_selected} dropped, ${counts.retained} kept`}
                .
              </p>
              <Disclosure variant="flush" title="Details and limits">
                <div className="evidence-fineprint">
                  <p className="fine">
                    Selection as of {stamp(data.as_of)}, from locally saved
                    sources in the selected window. Opening this makes no source
                    or AI request; source checks may be older.
                    {data.saved_cutoff &&
                      ` The saved reading used sources up to ${stamp(data.saved_cutoff)}.`}
                  </p>
                  {data.status === "changed" && (
                    <p className="fine">
                      The saved labels still describe the earlier sample. A
                      different selection is not a measured change in sentiment.
                    </p>
                  )}
                  {!!data.parents_changed && (
                    <p className="fine">
                      Saved discussion context differs for {data.parents_changed}{" "}
                      retained messages (availability or age, not only wording).
                    </p>
                  )}
                  {data.comparison_sources_changed && (
                    <p className="fine">
                      The extra news-comparison pool also differs; those reports
                      are not counted here.
                    </p>
                  )}
                  {selected === "hackernews" && (
                    <p className="fine">
                      Tech-community replies are not representative investor
                      sentiment. Open a source to read its saved parent.
                    </p>
                  )}
                  <p className="fine">
                    These texts have no AI labels in this view. A mention may be
                    unrelated to the company; opinions and secondary reporting
                    are not verified facts. Relevance is not assessed here.
                  </p>
                </div>
              </Disclosure>
              {exclusions.length > 0 && (
                <Disclosure variant="flush" title="Excluded before analysis">
                  <div className="evidence-fineprint">
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
                      These texts receive no sentiment label. The saved sources
                      remain in Data &amp; sources.
                    </p>
                  </div>
                </Disclosure>
              )}
            </>
          )}
          {!sources.length && (
            <p>
              No selected texts for this source type. Missing coverage is not
              neutral sentiment.
            </p>
          )}
          {inline ? (
            // Collected but not yet analysed: the same cards as the analysed
            // list, just without a tone label.
            <div className="sentiment-items collected-source-list">
              {shown.map((s) => (
                <Card as="article" variant="flush" className="source-story" key={s.id} data-source-id={s.id}>
                  <MetaRow className="sentiment-source-meta fine">
                    <SourceChip
                      label={s.source}
                      date={`${s.timestamp_basis === "feed_updated" ? "Feed updated · " : ""}${stamp(s.published_at)}`}
                      href={s.url}
                      onOpen={() => onSource(s.id)}
                    />
                  </MetaRow>
                  {sourceHeadline(s) && (
                    <h3>
                      {s.url ? (
                        <a href={s.url} target="_blank" rel="noopener noreferrer">
                          {sourceHeadline(s)}
                        </a>
                      ) : (
                        sourceHeadline(s)
                      )}
                    </h3>
                  )}
                  <p className="story-source-text original-source-text">{s.body}</p>
                </Card>
              ))}
            </div>
          ) : (
            shown.map((s) => (
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
                {(s.in_saved_sample === false || s.has_parent_context) && (
                  <p className="fine">
                    {s.in_saved_sample === false ? "Not in the saved sample" : ""}
                    {s.in_saved_sample === false && s.has_parent_context ? " · " : ""}
                    {s.has_parent_context ? "Saved parent context available" : ""}
                  </p>
                )}
                <p className="original-source-text">{s.body}</p>
                <Button variant="tertiary" size="sm" className="source-link" onClick={() => onSource(s.id)}>
                  Inspect current source ↗
                </Button>
              </article>
            ))
          )}
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
        </div>
      </Container>
    </section>
  );
}
