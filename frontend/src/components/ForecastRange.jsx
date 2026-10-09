const number = (value) => {
  if (value == null || !Number.isFinite(Number(value))) return "Not available";
  const n = Number(value);
  const scale = Math.abs(n) >= 1e9 ? 1e9 : Math.abs(n) >= 1e6 ? 1e6 : 1;
  return (
    (n / scale).toLocaleString("en-GB", { maximumFractionDigits: 6 }) +
    (scale === 1e9 ? "bn" : scale === 1e6 ? "m" : "")
  );
};
const exact = (value) => {
  if (value == null) return "Not available";
  const [whole, fraction] = String(value).split(".");
  return (
    whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",") +
    (fraction ? `.${fraction}` : "")
  );
};

export default function ForecastRange({ metric, currency, adjusted = false }) {
  const label =
    metric.key === "eps"
      ? adjusted
        ? "Adjusted earnings per share"
        : "Earnings per share"
      : "Revenue";
  const prefix = currency === "USD" ? "US$" : currency ? `${currency} ` : "";
  const display = (key) =>
    metric.source_display?.[key] ||
    (metric[key] == null || !Number.isFinite(Number(metric[key]))
      ? "Not available"
      : prefix + number(metric[key]));
  const low = Number(metric.low),
    high = Number(metric.high),
    average = Number(metric.average);
  const valid =
    [metric.low, metric.high, metric.average].every(
      (v) => v != null && Number.isFinite(Number(v)),
    ) &&
    low <= average &&
    average <= high;
  const position = valid
    ? high === low
      ? 50
      : ((average - low) / (high - low)) * 100
    : null;
  return (
    <article className="forecast-range">
      <h5>{label}</h5>
      <p className="forecast-average">
        {display("average")}
        <span>average estimate</span>
      </p>
      {valid && (
        <div
          className="forecast-range-plot"
          role="img"
          aria-label={`Forecast range: low ${display("low")}, average ${display("average")}, high ${display("high")}`}
        >
          <div className="forecast-track">
            <span style={{ left: `${position}%` }} />
          </div>
        </div>
      )}
      <div className="forecast-endpoints">
        <span>
          <small>Low estimate</small>
          {display("low")}
        </span>
        <span>
          <small>High estimate</small>
          {display("high")}
        </span>
      </div>
      {metric.analysts != null && (
        <p className="forecast-contributors">
          {metric.analysts} analysts for this metric
        </p>
      )}
      <details>
        <summary>Exact values &amp; definition</summary>
        <p>
          Low {exact(metric.low)} · average {exact(metric.average)} · high{" "}
          {exact(metric.high)}.
        </p>
        <p>
          {metric.basis ||
            (metric.key === "eps"
              ? "The provider does not establish the earnings accounting convention."
              : "Annual revenue estimate under the provider’s reporting convention.")}{" "}
          Currency: {currency || "unspecified"}. The marker shows the average
          within this forecast range; each metric uses its own scale.
        </p>
        {metric.range_average != null && (
          <p>
            The source’s range table rounds its average to{" "}
            {exact(metric.range_average)}. This view retains the more precise
            annual-table average.
          </p>
        )}
      </details>
    </article>
  );
}
