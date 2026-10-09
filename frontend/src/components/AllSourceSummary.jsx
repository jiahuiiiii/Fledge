import { SourceLabel } from "./SourceFilters";
import { sourceCoverage, sourceExclusionLabels } from "../lib/sourceCoverage";
import "./AllSourceSummary.css";
import { sentimentSummaryLabel } from "../lib/sentimentSummary";

export default function AllSourceSummary({ analysis, providerStatus = [] }) {
  const coverage = sourceCoverage(analysis);
  return (
    <div className="all-source-summary source-analysis-coverage">
      <div className="sentiment-summary">
        <strong>Source coverage</strong>
        <span>
          {analysis.batching?.completed
            ? `${analysis.batching.completed} batches combined`
            : "Saved AI reading"}
        </span>
      </div>
      <div
        className="source-coverage-totals"
        aria-label="Analysis coverage totals"
      >
        {[
          ["Available candidates", coverage.candidates],
          ["Analysed", coverage.analysed],
          ["Relevant to company", coverage.relevant],
          ["Unrelated", coverage.unrelated],
          ["Relevance unclear", coverage.unclear],
        ].map(([label, value]) => (
          <div key={label}>
            <strong>{value ?? "—"}</strong>
            <span>{label}</span>
          </div>
        ))}
      </div>
      <p
        className={`source-coverage-status ${coverage.complete ? "" : "warning"}`}
      >
        {coverage.complete
          ? `Every eligible source in this saved pool was analysed. ${coverage.excluded} excluded before analysis.`
          : `Earlier limited reading: ${coverage.analysed} analysed${coverage.candidates == null ? "" : ` from ${coverage.candidates} candidates`}. Refresh & analyse now covers every eligible saved source in batches.`}
      </p>
      <div
        className="source-summary-list"
        aria-label="Coverage and tone by source"
      >
        {coverage.scopes.map((sample) => {
          const connection = providerStatus.find(
            (item) => item.provider === sample.scope,
          );
          return (
            <div key={sample.scope}>
              <SourceLabel scope={sample.scope} />
              <strong>
                {sample.analysed
                  ? sentimentSummaryLabel(sample.sentimentSummary)
                  : connection?.status === "disabled"
                    ? "Connection off"
                    : "No analysed texts"}
              </strong>
              <dl className="source-coverage-counts">
                <div>
                  <dt>Available</dt>
                  <dd>{sample.candidates ?? "—"}</dd>
                </div>
                <div>
                  <dt>Analysed</dt>
                  <dd>{sample.analysed}</dd>
                </div>
                <div>
                  <dt>Relevant</dt>
                  <dd>{sample.relevant}</dd>
                </div>
              </dl>
              {sample.excludedCount > 0 && (
                <span className="fine">
                  {sample.excludedCount} excluded before analysis
                </span>
              )}
              {sample.unanalysed > 0 && (
                <span className="fine">
                  {sample.unanalysed} outside this saved reading
                </span>
              )}
              {connection?.status !== "ready" &&
                sample.scope === "x" &&
                connection?.message && (
                  <span className="fine">{connection.message}</span>
                )}
            </div>
          );
        })}
      </div>
      <details className="secondary-details">
        <summary>How sources are counted</summary>
        <p>
          Available candidates are locally saved texts in the reading’s date
          window. A company mention alone does not establish usefulness. Each
          eligible text receives a relevance label; unrelated and unclear items
          remain inspectable.
        </p>
        {coverage.scopes
          .filter((sample) => sample.excludedCount)
          .map((sample) => (
            <p key={sample.scope}>
              <SourceLabel scope={sample.scope} />:{" "}
              {Object.entries(sample.excluded)
                .map(
                  ([reason, n]) =>
                    `${sourceExclusionLabels[reason] || reason}: ${n}`,
                )
                .join(" · ")}
            </p>
          ))}
        <p>
          Exact duplicate text is analysed once within its source type. Distinct
          replies from the same thread are included. Missing passages or
          required reply context are excluded with a reason, rather than
          labelled unrelated.
        </p>
        <p>
          Tone counts use relevant text groups. Repeated reporting and comments
          do not establish independent confirmation or a survey of investors.
          News comparison context is bounded within each batch; grouping is not
          exhaustive.
        </p>
      </details>
    </div>
  );
}
