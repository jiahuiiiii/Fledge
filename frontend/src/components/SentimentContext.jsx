import { stamp } from "./MarketResearch";

export default function SentimentContext({ value, purpose = "label" }) {
  if (!value) return null;
  return (
    <details className="conversation-context">
      <summary>Parent context used for this {purpose}</summary>
      <p className="fine">
        Separate {value.parent_type === "story" ? "story" : "message"} ·{" "}
        {purpose === "finding"
          ? "not another source or independent confirmation"
          : purpose === "connection"
            ? "not a separate source connection"
            : "not another sentiment vote"}
        .
      </p>
      {value.parent_type === "story" && <h4>{value.title}</h4>}
      {value.citations.map((c) => (
        <blockquote key={c.passage_id}>{c.quote}</blockquote>
      ))}
      <p className="fine">
        Published {stamp(value.published_at)} · checked{" "}
        {stamp(value.checked_at)}.
      </p>
      <p className="fine">{value.limitation}</p>
      {value.body && (
        <details>
          <summary>Read the saved parent text</summary>
          <blockquote>{value.body}</blockquote>
        </details>
      )}
      <a href={value.url} target="_blank" rel="noopener noreferrer">
        Open cited parent discussion ↗
      </a>
    </details>
  );
}
