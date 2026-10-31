import SentimentPriceContext from "./SentimentPriceContext";

// compact: alert cards show the quote alone; the reason and the shared
// AI-interpretation note are rendered once by the card instead.
export default function SentimentBasis({ item, compact = false }) {
  if (!item.evidence_policy) return compact ? null : <p>{item.explanation}</p>;
  // Alert cards lead with the quote; the full view keeps its original order.
  const quotes = item.citations.map((c, i) => (
    <blockquote key={i}>{c.quote}</blockquote>
  ));
  return (
    <div className="sentiment-basis">
      {!compact && <p className="fine">{item.explanation}</p>}
      {item.repair && (
        <p className="fine">
          The AI's label and its evidence disagreed. Inconsistent fields were
          removed or marked unclear.
        </p>
      )}
      {item.guard?.applied && (
        <p className="fine">
          Evidence check changed the AI's {item.guard.model_sentiment} label to
          unclear.
        </p>
      )}
      <SentimentPriceContext
        values={item.price_comparisons}
        quotedText={item.citations.map((c) => c.quote)}
      />
      {compact && quotes}
      {item.reporting_basis && (
        <details className="reporting-evidence">
          <summary>{item.reporting_basis.label}</summary>
          {item.reporting_basis.eligible && (
            <p className="fine">
              Reported effect:{" "}
              {item.reporting_basis.impact === "not_stated"
                ? "no clear direction stated"
                : item.reporting_basis.impact}
              . Separate from the article’s overall tone.
            </p>
          )}
          {item.reporting_basis.citations.map((c, i) => (
            <blockquote key={i}>{c.quote}</blockquote>
          ))}
          <p className="fine">
            {item.reporting_basis.eligible
              ? "This excerpt may qualify for a reporting update when it is new to your watch. The claim is not independently verified."
              : "This can inform sentiment, but does not qualify for a company-event alert."}
          </p>
        </details>
      )}
      {!compact && (
        <strong>
          {item.previous_citations?.length
            ? "View used for this label"
            : "Wording used for this label"}
        </strong>
      )}
      {!compact && quotes}
      {!!item.previous_citations?.length && (
        <details>
          <summary>Earlier view in the same post</summary>
          {item.previous_citations.map((c, i) => (
            <blockquote key={i}>{c.quote}</blockquote>
          ))}
        </details>
      )}
      {!compact && (
        <p className="fine">
          Original excerpts selected by AI. The label and any earlier/current
          distinction are interpretations.
        </p>
      )}
    </div>
  );
}
