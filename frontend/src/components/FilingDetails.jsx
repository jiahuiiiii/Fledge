const names = {
  revenue_growth: "Revenue growth",
  operating_margin: "Operating margin",
};
export default function FilingDetails({ filing }) {
  if (!filing) return null;
  return (
    <section className="filing-details" aria-label="Filing calculation trail">
      <div className="row">
        <h3>From the filing</h3>
        <span className="status">
          {filing.period_type === "annual" ? "Annual" : "Quarterly"}
        </span>
      </div>
      <p>
        {filing.period_start || "Start unavailable"} to {filing.period_end} ·{" "}
        {filing.form}
      </p>
      <a href={filing.filing_url} target="_blank" rel="noopener noreferrer">
        Open original SEC filing ↗
      </a>
      {filing.calculations.map((c) => (
        <details key={c.metric}>
          <summary>
            {names[c.metric]} ·{" "}
            {c.value == null
              ? "Unavailable"
              : `${Number(c.value).toLocaleString("en-GB", { maximumFractionDigits: 2 })}%`}
          </summary>
          <p>{c.formula}</p>
          {c.reason && <p className="warning">{c.reason}</p>}
          {c.inputs.map((f, i) => (
            <div className="raw-fact" key={i}>
              <strong>
                {f.concept === "OperatingIncomeLoss"
                  ? "Operating income"
                  : "Revenue"}
              </strong>
              <span>
                USD{" "}
                {Number(f.value).toLocaleString("en-GB", {
                  maximumFractionDigits: 2,
                })}
              </span>
              <small>
                {f.start} to {f.end} · {f.accession} · {f.concept}
              </small>
            </div>
          ))}
          {c.value != null && (
            <p className="fine">
              Stored calculation: {c.value}%. Display is rounded; monitoring
              uses the stored value.
            </p>
          )}
        </details>
      ))}
      <details>
        <summary>Coverage and calculation limits</summary>
        <ul>
          {filing.limitations.map((text) => (
            <li key={text}>{text}</li>
          ))}
        </ul>
      </details>
    </section>
  );
}
