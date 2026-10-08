import { reportStateLabels } from "../lib/reportExpectation";

export function ReportExpectationText({ condition, state }) {
  if (!condition.expected_period_end) return null;
  return (
    <div className="report-expectation">
      {state && (
        <strong className={state.state === "overdue" ? "attention" : ""}>
          {reportStateLabels[state.state] || "Reporting evidence unknown"}
        </strong>
      )}
      <p className="fine">
        Your expectation: {condition.period_type || "quarter"} figures for a
        period ending on or after {condition.expected_period_end}, by{" "}
        {condition.expected_report_by} (inclusive UTC).
      </p>
      {state?.observed_period_end && (
        <p className="fine">
          Assessed figure’s period ended {state.observed_period_end}.
        </p>
      )}
      <p className="fine">
        {state?.state === "withheld"
          ? "Source access changed. This saved reporting assessment is withheld; no new check was made."
          : state?.state === "conflicting"
            ? "Conflicting figures cover the required period. The condition remains unknown; inspect the sources. This is different from a missing filing."
            : state?.state === "overdue"
              ? "This app does not have matching figures. The condition is unknown; the last figure and source remain visible. This does not prove the company filed late."
              : state?.state === "available"
                ? "The required period is available in the saved evidence. Other conditions and age limits still apply; this does not establish when the company filed."
                : "Until that date, saved figures remain subject to your other conditions. After it, missing required figures make this condition unknown. This is your expectation, not a verified company filing date."}
      </p>
    </div>
  );
}

export default function ReportExpectationEditor({
  condition,
  index,
  onChange,
}) {
  return (
    <details
      className="reporting-age-editor report-expectation-editor"
      open={condition.expected_period_end ? true : undefined}
    >
      <summary>When you expect the next figures</summary>
      <div className="report-expectation-fields">
        <label>
          Required reporting period ending on or after
          <input
            type="date"
            aria-label={`Expected period end ${index}`}
            value={condition.expected_period_end || ""}
            onChange={(e) => onChange("expected_period_end", e.target.value)}
          />
        </label>
        <label>
          Figures expected by (inclusive UTC)
          <input
            type="date"
            aria-label={`Expected figures by ${index}`}
            value={condition.expected_report_by || ""}
            onChange={(e) => onChange("expected_report_by", e.target.value)}
          />
        </label>
        <small>
          Optional. Choose both dates or leave both blank. This is your research
          expectation, not a verified company or legal filing deadline. Annual
          figures cannot fill a quarterly requirement. If matching figures are
          missing after your date, this condition becomes unknown and prompts
          review. No extra source or AI call is made by the date change.
        </small>
        {(condition.expected_period_end || condition.expected_report_by) && (
          <button
            className="text-button"
            type="button"
            onClick={() => onChange("clear", "")}
          >
            Clear reporting expectation
          </button>
        )}
      </div>
    </details>
  );
}
