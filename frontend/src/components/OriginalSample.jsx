import SentimentLimits from "./SentimentLimits";
import { stamp } from "./MarketResearch";
import { originalSample } from "../lib/originalSample";
import { SourceLabel, sourceScope } from "./SourceFilters";
import { sourceHeadline } from "../lib/sourceHeadline";
import { Button, Disclosure } from "./ui";

export default function OriginalSample({
  analysis,
  channel,
  platform,
  onSource,
}) {
  const sources = originalSample(analysis, channel, platform);
  return (
    <section className="original-sample" aria-label="Original selected sources">
      <SentimentLimits value={analysis.coverage?.input_limits} />
      <p className="evidence-counts">
        {sources.length} selected{" "}
        {channel === "all"
          ? "sources"
          : channel === "news"
            ? "reports"
            : "posts"}{" "}
        · newest first · sources up to {stamp(analysis.cutoff)}.
      </p>
      <Disclosure variant="flush" title="How to read this sample">
        <div className="evidence-fineprint">
          <p className="fine">
            These are the original supplied texts, including items the AI
            considered unrelated. AI labels are hidden here, and this view makes
            no new source or AI request.
          </p>
          <p className="fine">
            {channel === "all"
              ? "News uses publisher headlines and snippets; public discussions are attributed opinions."
              : channel === "news"
                ? "Provider headlines and snippets may be incomplete; open the publisher for the full report."
                : "Public discussions are attributed opinions or reports, not verified company facts."}{" "}
            {platform === "hackernews" &&
              (analysis.coverage?.parent_contexts
                ? `${analysis.coverage.parent_contexts} saved parent messages were supplied as separate context. `
                : "This analysis read the comments alone. ")}
            Comparison-only reports are excluded, so this is the same selected
            sample, not the whole feed.
          </p>
        </div>
      </Disclosure>
      {sources.length ? (
        sources.map((s) => (
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
            <p className="original-source-text">{s.body}</p>
            <Button
              variant="tertiary"
              size="sm"
              className="source-link"
              onClick={() => onSource(s.id)}
            >
              Inspect original source ↗
            </Button>
          </article>
        ))
      ) : (
        <p>
          No{" "}
          {channel === "all"
            ? "sources"
            : channel === "news"
              ? "news reports"
              : "social posts"}{" "}
          were selected. Missing coverage is not neutral sentiment.
        </p>
      )}
    </section>
  );
}
