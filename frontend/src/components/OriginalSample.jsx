import SentimentLimits from "./SentimentLimits";
import { stamp } from "./MarketResearch";
import { originalSample } from "../lib/originalSample";

export default function OriginalSample({
  analysis,
  channel,
  platform,
  onSource,
}) {
  const sources = originalSample(analysis, channel, platform);
  return (
    <section className="original-sample" aria-label="Original selected sources">
      <h3>Read the same sample yourself</h3>
      <SentimentLimits value={analysis.coverage?.input_limits} />
      <p className="fine">
        {sources.length} selected {channel === "news" ? "reports" : "posts"} ·
        newest first · source cutoff {stamp(analysis.cutoff)}. These are the
        original supplied texts, including items the AI considered unrelated.
        This view hides AI labels and grouping; it makes no new source or AI
        request.
      </p>
      <p className="fine">
        {channel === "news"
          ? "Provider headlines and snippets may be incomplete; open the original publisher for the full report."
          : "Public discussions are attributed opinions or reports, not verified company facts."}{" "}
        {platform === "hackernews" && (
          <>
            {analysis.coverage?.parent_contexts
              ? `${analysis.coverage.parent_contexts} saved parents were supplied separately to this analysis; their evidence is shown beside the AI labels.`
              : "This saved analysis read the comments alone."}{" "}
            Inspect a source to read its saved parent; loading context does not
            change an earlier label.{" "}
          </>
        )}
        Comparison-only reports are excluded so this is the same selected
        sample, not the whole available feed. Your saved reasoning stays in the
        idea panel.
      </p>
      {sources.length ? (
        sources.map((s) => (
          <article key={s.id}>
            <div className="row">
              <span className="fine">{s.source}</span>
              <time>{stamp(s.published_at)}</time>
            </div>
            <h3>{s.title}</h3>
            <p className="original-source-text">{s.body}</p>
            <button className="source-link" onClick={() => onSource(s.id)}>
              Inspect original source ↗
            </button>
          </article>
        ))
      ) : (
        <p>
          No {channel === "news" ? "news reports" : "social posts"} were
          selected. Missing coverage is not neutral sentiment.
        </p>
      )}
    </section>
  );
}
