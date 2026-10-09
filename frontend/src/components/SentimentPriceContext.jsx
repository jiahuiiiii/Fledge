import {
  priceComparisonText,
  priceUnavailableReasons,
} from "../lib/sentimentSummary";

export default function SentimentPriceContext({
  values = [],
  compact = false,
  quotedText = [],
}) {
  const shown = compact
    ? values.filter((value) => value.status === "compared")
    : values;
  if (!shown.length) return null;
  return (
    <div className="sentiment-price-context">
      {shown.map((value, i) => (
        <div key={i}>
          <p className="fine">
            {priceComparisonText(value) ||
              priceUnavailableReasons[value.status] ||
              "Price comparison unavailable."}
          </p>
          {!compact && (
            <>
              {!quotedText.includes(value.quote) && (
                <blockquote>{value.quote}</blockquote>
              )}
              {value.status === "compared" && (
                <p className="fine">
                  Calculation: (${value.amount} − ${value.reference.close}) ÷ $
                  {value.reference.close} × 100 ={" "}
                  {Number(value.difference_percent).toFixed(2)}%. Yahoo Finance
                  completed daily close; capture saved{" "}
                  {value.reference.retrieved_at}. {value.reference.basis}
                </p>
              )}
              <p className="fine">
                Historical price arithmetic provides context. It does not
                establish the author's attitude or a live price.
              </p>
            </>
          )}
        </div>
      ))}
    </div>
  );
}
