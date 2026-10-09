import SentimentPriceContext from "./SentimentPriceContext";

export default function SentimentBasis({ item }) {
  if (!item.evidence_policy) return <p>{item.explanation}</p>;
  return (
    <div className="sentiment-basis">
      <p className="fine">{item.explanation}</p>
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
      <strong>
        {item.previous_citations?.length
          ? "View used for this label"
          : "Wording used for this label"}
      </strong>
      {item.citations.map((c, i) => (
        <blockquote key={i}>{c.quote}</blockquote>
      ))}
      {!!item.previous_citations?.length && (
        <details>
          <summary>Earlier view in the same post</summary>
          {item.previous_citations.map((c, i) => (
            <blockquote key={i}>{c.quote}</blockquote>
          ))}
        </details>
      )}
      <p className="fine">
        Original excerpts selected by AI. The label and any earlier/current
        distinction are interpretations.
      </p>
    </div>
  );
}
