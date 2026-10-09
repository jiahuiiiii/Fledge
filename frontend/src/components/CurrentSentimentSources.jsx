import SourceFilters, { SourceLabel, sourceScope } from "./SourceFilters";
import { originalSample } from "../lib/originalSample";
import SentimentLimits from "./SentimentLimits";
import { useState } from "react";
import { stamp } from "./MarketResearch";

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
}) {
  const [selected, setSelected] = useState("all");
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
  return (
    <section className="original-sample" aria-label="Current sentiment inputs">
      <p role="status">{states[data.status]}</p>
      <SentimentLimits value={data.input_limits} />
      <details open={expanded || undefined}>
        <summary>Read current sources · {data.sources.length} selected</summary>
        <div className="source-preview-content">
          {data.status === "changed" && (
            <p className="fine">
              Saved labels still describe the earlier sample. A different source
              selection is not a measured change in market sentiment.
            </p>
          )}
          <p className="fine">
            Selection as of {stamp(data.as_of)}, from locally saved sources in
            the selected window. Opening this preview makes no source or AI
            request. Source checks may be older; inspect their dates and
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
            {counts.selected} selected from {counts.available} available
            candidate texts. Selection is bounded; other material may matter.
          </p>
          {counts.added != null && (
            <p className="fine">
              Compared with the saved sample: {counts.added} not previously
              selected, {counts.no_longer_selected} no longer selected,{" "}
              {counts.retained} retained. These are source-version differences,
              not counts of new events.
            </p>
          )}
          {!!data.parents_changed && (
            <p className="fine">
              Saved parent context differs for {data.parents_changed} retained
              replies. This can reflect availability or age as well as changed
              wording.
            </p>
          )}
          {data.comparison_sources_changed && (
            <p className="fine">
              The additional news-comparison pool also differs. Its reports are
              not counted or shown as selected sentiment sources here.
            </p>
          )}
          {selected === "hackernews" && (
            <p className="fine">
              Tech-community replies are not representative investor sentiment.
              Open a source to inspect its separately saved original parent.
            </p>
          )}
          {!sources.length && (
            <p>
              No selected texts for this source type. Missing coverage is not
              neutral sentiment.
            </p>
          )}
          {sources.map((s) => (
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
              <h3>{s.title}</h3>
              <p className="fine">
                First available here {stamp(s.available_at)}
                {s.in_saved_sample === false
                  ? " · not in the saved selected sample"
                  : ""}
                {s.has_parent_context ? " · eligible saved parent context" : ""}
                .
              </p>
              <p className="original-source-text">{s.body}</p>
              <button className="source-link" onClick={() => onSource(s.id)}>
                Inspect current source ↗
              </button>
            </article>
          ))}
          <p className="fine">
            These supplied snippets and posts have no AI labels in this view. A
            mention may be unrelated to the company; public opinions and
            secondary reporting are not verified facts.
          </p>
        </div>
      </details>
    </section>
  );
}
