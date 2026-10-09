import test from "node:test";
import assert from "node:assert/strict";
import { mentionsCompany, savedDevelopments } from "./companyHeadlines.js";

test("unanalysed headline browsing requires an explicit company mention", () => {
  const company = { symbol: "AVGO", name: "Broadcom Inc." };
  assert.ok(mentionsCompany({ title: "Broadcom seeks financing" }, company));
  assert.ok(
    mentionsCompany(
      { title: "Chip stocks", body: "NASDAQ:AVGO fell." },
      company,
    ),
  );
  assert.equal(
    mentionsCompany(
      { title: "VYM and HDV: dividend ETFs", body: "AI momentum" },
      company,
    ),
    false,
  );
  assert.equal(
    mentionsCompany({ title: "Broadcompany announcement" }, company),
    false,
  );
  assert.ok(
    mentionsCompany(
      { title: "New Example reports", body: "" },
      { symbol: "NEX", name: "New Example, Inc." },
    ),
  );
  assert.equal(
    mentionsCompany(
      { title: "On the market" },
      { symbol: "ON", name: "ON Semiconductor Corporation" },
    ),
    false,
  );
  assert.ok(
    mentionsCompany(
      { title: "$ON results" },
      { symbol: "ON", name: "ON Semiconductor Corporation" },
    ),
  );
});

test("development preview uses permitted saved reports and safe repeat decisions", () => {
  const analysis = {
    items: ["a", "b", "c"].map((source_id) => ({
      source_id,
      channel: "news",
      relevance: "relevant",
      reporting_basis: { eligible: true },
    })),
    sources: ["a", "b", "c"].map((id, i) => ({
      id,
      kind: "news",
      published_at: `2026-10-0${i + 1}`,
      comparison_only: id === "c",
    })),
    coverage_links: [
      {
        source_id: "b",
        relation: "repeats",
        repeat_suppression_allowed: false,
      },
    ],
  };
  assert.deepEqual(
    savedDevelopments(analysis).map((s) => s.id),
    ["b", "a"],
  );
  analysis.coverage_links[0].repeat_suppression_allowed = true;
  assert.deepEqual(
    savedDevelopments(analysis).map((s) => s.id),
    ["a"],
  );
  assert.deepEqual(savedDevelopments({ ...analysis, withheld: true }), []);
});
