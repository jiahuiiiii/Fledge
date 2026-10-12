import { stamp } from "./MarketResearch";

export function RedditThreadContext({ value }) {
  if (!value) return null;
  let commentNumber = 0;
  const names = new Map(
    value.messages.map((message) => [
      message.message_key,
      message.role === "topic"
        ? "Discussion topic"
        : `Comment ${++commentNumber}`,
    ]),
  );
  return (
    <details className="conversation-context">
      <summary>Saved discussion supplied to the AI</summary>
      <p className="fine">
        {value.supplied_message_count} of {value.saved_message_count} saved
        messages supplied with this label. {value.limitation}
      </p>
      {!value.topic_available && (
        <p className="fine">
          The original topic was unavailable in this saved sample.
        </p>
      )}
      {value.messages.map((message) => (
        <details key={message.message_key}>
          <summary>{names.get(message.message_key)}</summary>
          {message.role !== "topic" && (
            <p className="fine">
              {message.parent_key
                ? names.has(message.parent_key)
                  ? `Replies to ${names.get(message.parent_key).toLowerCase()}`
                  : "Verified reply parent is outside this excerpt"
                : "Reply parent unknown"}
            </p>
          )}
          {message.passages
            .filter(
              (passage) => message.role === "topic" || passage.id !== "p0",
            )
            .map((passage) => (
              <blockquote key={passage.id}>{passage.quote}</blockquote>
            ))}
          <p className="fine">
            {message.timestamp_basis === "feed_updated"
              ? "Feed updated"
              : "Published"}{" "}
            {stamp(message.published_at)}
          </p>
          <a href={message.url} target="_blank" rel="noopener noreferrer">
            Open original message ↗
          </a>
        </details>
      ))}
    </details>
  );
}

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
