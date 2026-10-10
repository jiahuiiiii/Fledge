import { SourceLabel } from "./SourceFilters";
import { sourceCoverage, sourceExclusionLabels } from "../lib/sourceCoverage";
import "./AllSourceSummary.css";
import { sentimentSummaryLabel } from "../lib/sentimentSummary";

export default function AllSourceSummary({
  analysis,
  providerStatus = [],
  showDetails = true,
}) {
  const coverage = sourceCoverage(analysis);
  return (
    <div className="all-source-summary source-analysis-coverage">
      <div className="sentiment-summary">
        <strong>Source coverage</strong>
        <span>Saved AI reading</span>
      </div>
      <div
        className="source-coverage-totals"
        aria-label="Analysis coverage totals"
      >
        {[
          ["Available sources", coverage.candidates],
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
          ? `All usable saved sources were analysed. ${coverage.excluded} left out before analysis; see the reasons below.`
          : `This earlier reading covers ${coverage.analysed} sources${coverage.candidates == null ? "" : ` out of ${coverage.candidates} saved`}. A new analysis can include every usable saved source.`}
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
      {showDetails && <SourceCountingDetails analysis={analysis} />}
    </div>
  );
}

export function SourceCountingDetails({ analysis }) {
  const coverage = sourceCoverage(analysis);
  return (
    <details className="secondary-details">
      <summary>How sources are counted</summary>
      <p>
        Available sources are saved news and posts from the dates covered by
        this reading. Mentioning the company does not always make a source
        relevant. You can still open sources labelled unrelated or unclear.
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
        replies from the same thread are included. Missing passages or required
        reply context are excluded with a reason, rather than labelled
        unrelated.
      </p>
      <p>
        Related reports count as one development; identical posts count once
        within their platform. Repeated coverage is not independent
        confirmation, and these posts are not a survey of investors. Sources are
        compared in smaller sets, so some repeated coverage may be missed.
      </p>
    </details>
  );
}
