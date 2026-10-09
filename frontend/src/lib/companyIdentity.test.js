import test from "node:test";
import assert from "node:assert/strict";
import { companyName, companyMatches } from "./companyIdentity.js";
test("aliases do not rewrite canonical names or fictional issuers", () => {
  const company = { symbol: "QCOM", name: "QUALCOMM INC/DE", mode: "sec" };
  assert.equal(companyName(company), "Qualcomm");
  assert.equal(company.name, "QUALCOMM INC/DE");
  assert.equal(companyName({ ...company, mode: "recorded" }), company.name);
  assert.equal(
    companyName({
      symbol: "AMD",
      name: "ADVANCED MICRO DEVICES INC",
      mode: "sec",
    }),
    "Advanced Micro Devices",
  );
  assert.equal(
    companyName({
      symbol: "MRVL",
      name: "Marvell Technology, Inc.",
      mode: "sec",
    }),
    "Marvell Technology",
  );
  assert.equal(
    companyName({ name: "Unmapped API Systems", symbol: "ZZZ" }),
    "Unmapped API Systems",
  );
});
test("search retains ticker, display alias and original legal name", () => {
  const company = { symbol: "QCOM", name: "QUALCOMM INC/DE", mode: "sec" };
  for (const query of ["qcom", "Qualcomm", "inc/de", "  QCOM  "])
    assert.equal(companyMatches(company, query), true);
  assert.equal(companyMatches(company, "NVIDIA"), false);
});
