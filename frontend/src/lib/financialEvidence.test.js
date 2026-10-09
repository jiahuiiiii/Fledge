import test from "node:test";
import assert from "node:assert/strict";
import {
  evidenceValue,
  evidenceSources,
  inputLabel,
  evidenceFormula,
} from "./financialEvidence.js";

test("readable evidence amounts preserve units, signs, zero and small nonzero values", () => {
  assert.equal(evidenceValue("89104000000"), "US$89.1 bil");
  assert.equal(evidenceValue("254340000"), "US$254.34 mil");
  assert.equal(evidenceValue("-3000000"), "−US$3 mil");
  assert.equal(evidenceValue("0"), "US$0");
  assert.equal(evidenceValue("0.001"), "US$0.001");
  assert.equal(evidenceValue("34.33779329", "percent"), "34.34%");
  assert.equal(evidenceValue("46.611", "multiple"), "46.61×");
  for (const invalid of [null, "", true, "NaN", "Infinity"])
    assert.equal(evidenceValue(invalid), "Unavailable");
});
test("report links deduplicate by exact URL without combining different filing vintages", () => {
  const annual = {
    filing_url: "https://www.sec.gov/Archives/annual.htm",
    form: "10-K",
    end: "2025-09-30",
  };
  const quarter = {
    filing_url: "https://www.sec.gov/Archives/quarter.htm",
    form: "10-Q",
    end: "2026-06-30",
  };
  const row = { inputs: [annual, quarter, { ...quarter, end: "2025-06-30" }] };
  assert.deepEqual(
    evidenceSources(row).map((s) => [s.url, s.date]),
    [
      [annual.filing_url, annual.end],
      [quarter.filing_url, quarter.end],
    ],
  );
  assert.deepEqual(evidenceSources({ inputs: [] }), []);
});
test("calculation labels explain fiscal bridge roles without showing filing codes", () => {
  const row = {
    formula:
      "Previous fiscal year + current fiscal year to date − comparable prior fiscal year to date",
    inputs: [{}, {}, {}],
  };
  assert.deepEqual(
    row.inputs.map((input, i) => inputLabel(row, input, i)),
    ["Previous fiscal year", "Current year to date", "Prior year to date"],
  );
  assert.equal(
    inputLabel({}, { concept: "SomeCustomTag" }, 0),
    "Reported figure",
  );
  assert.equal(
    evidenceFormula({
      key: "operating_margin",
      formula: "operating_income / revenue × 100",
    }),
    "Operating income ÷ revenue × 100",
  );
});
