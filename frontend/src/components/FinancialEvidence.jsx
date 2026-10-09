import FilingResolution from "./FilingResolution";
import { day } from "../lib/financialStory";
import {
  evidenceValue,
  evidencePeriod,
  inputLabel,
  evidenceSources,
  evidenceFormula,
} from "../lib/financialEvidence";
import "./FinancialEvidence.css";

export function FinancialEvidenceRow({ row, fallbackUrl, caption }) {
  const sources = evidenceSources(row, fallbackUrl);
  const inputs = [...(row.inputs || [])];
  if (
    row.prior &&
    !inputs.some(
      (input) =>
        input.start === row.prior.start &&
        input.end === row.prior.end &&
        input.concept === row.prior.concept,
    )
  )
    inputs.push(row.prior);
  return (
    <section className="financial-evidence-card">
      <div className="financial-evidence-heading">
        <div>
          {caption && (
            <span className="financial-evidence-caption">{caption}</span>
          )}
          <h3>{row.label || "Reported figure"}</h3>
        </div>
        <strong className="financial-evidence-value">
          {evidenceValue(row.value, row.unit)}
        </strong>
      </div>
      <p className="financial-evidence-period">
        {row.period_label || evidencePeriod(row)}
      </p>
      {row.reason && <p className="financial-evidence-note">{row.reason}</p>}
      {row.explanation && (
        <p className="financial-evidence-note">{row.explanation}</p>
      )}
      {sources.length > 0 && (
        <div
          className="financial-evidence-sources"
          aria-label="Original reports"
        >
          {sources.map((source) => (
            <a
              key={source.url}
              href={source.url}
              target="_blank"
              rel="noreferrer"
            >
              <span>{source.label} ↗</span>
              {source.date && <small>{day(source.date)}</small>}
            </a>
          ))}
        </div>
      )}
      {(inputs.length > 1 || row.formula) && (
        <details className="financial-evidence-calculation">
          <summary>
            {row.calculated || row.formula
              ? "How this is calculated"
              : "Reported figures"}
          </summary>
          {row.formula && <p>{evidenceFormula(row)}</p>}
          <dl>
            {inputs.map((input, index) => (
              <div key={index}>
                <dt>
                  {inputLabel(row, input, index)}
                  <small>{evidencePeriod(input)}</small>
                </dt>
                <dd>{evidenceValue(input.value, input.unit || row.unit)}</dd>
              </div>
            ))}
          </dl>
        </details>
      )}
      <FilingResolution value={row.filing_resolution} />
    </section>
  );
}

export default function FinancialEvidence({ rows = [], children }) {
  const unique = [...new Set(rows.filter(Boolean))];
  const comparison = unique.length === 2 && unique[0].key === unique[1].key;
  return (
    <div className="financial-evidence-view">
      {children && <div className="financial-evidence-summary">{children}</div>}
      <div
        className={`financial-evidence-grid${comparison ? " is-comparison" : ""}`}
      >
        {unique.map((row, index) => (
          <FinancialEvidenceRow
            key={index}
            row={row}
            caption={
              comparison
                ? index === 0
                  ? "Selected period"
                  : "Comparison period"
                : null
            }
          />
        ))}
      </div>
      {unique.length > 0 && (
        <p className="financial-evidence-rounding">
          Figures are rounded for readability. Open a report for the original
          figures.
        </p>
      )}
    </div>
  );
}
