import test from "node:test";
import assert from "node:assert/strict";
import {
  currentCompanyHeadlines,
  mentionsCompany,
  savedDevelopments,
} from "./companyHeadlines.js";

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

const headline = (id, published_at, extra = {}) => ({
  id,
  published_at,
  kind: "news",
  title: "Nvidia announces a product",
  content_hash: id,
  ...extra,
});

test("current headlines recognise established short brands and explicit short-ticker context", () => {
  const micron = { symbol: "MU", name: "MICRON TECHNOLOGY INC" };
  const marvell = { symbol: "MRVL", name: "Marvell Technology Inc." };
  assert.ok(
    mentionsCompany({ title: "SpaceX vs. Micron: which stock?" }, micron),
  );
  assert.ok(mentionsCompany({ title: "Marvell shares rise" }, marvell));
  assert.ok(mentionsCompany({ title: "MU stock outlook" }, micron));
  assert.ok(
    mentionsCompany({ title: "Chipmaker (NASDAQ: MU) reports" }, micron),
  );
  assert.equal(
    mentionsCompany({ title: "A 5 micron measurement" }, micron),
    false,
  );
  assert.equal(
    mentionsCompany({ title: "Micronics equipment" }, micron),
    false,
  );
  assert.equal(
    mentionsCompany({ title: "Marvellous results" }, marvell),
    false,
  );
  assert.equal(
    mentionsCompany(
      { title: "ON the market" },
      { symbol: "ON", name: "ON Semiconductor" },
    ),
    false,
  );
});

test("latest headlines follow current permitted news dates rather than a saved AI reading", () => {
  const data = {
    instrument: { symbol: "NVDA", name: "NVIDIA" },
    documents: [
      headline("old", "2026-10-09T00:00:00Z"),
      headline("new", "2026-10-12T00:00:00Z"),
    ],
    market_news_ids: ["old", "new"],
    sentiment: {
      created_at: "2026-10-09",
      sources: [headline("old", "2026-10-09")],
    },
    market_brief: { points: [{ title: "An older AI point" }] },
  };
  const original = structuredClone(data);
  assert.deepEqual(
    currentCompanyHeadlines(data).map((d) => d.id),
    ["new", "old"],
  );
  assert.deepEqual(data, original);
  data.sentiment = { withheld: true };
  data.market_brief = null;
  assert.deepEqual(
    currentCompanyHeadlines(data).map((d) => d.id),
    ["new", "old"],
  );
});

test("headline preview excludes unavailable, superseded, undated and non-company records", () => {
  const documents = [
    headline("archived", "2026-10-09"),
    headline("current", "2026-10-12", {
      supersedes_id: "archived",
      content_hash: "same",
    }),
    headline("duplicate", "2026-10-11", { content_hash: "same" }),
    headline("withheld", "2026-10-12"),
    headline("undated", "invalid"),
    headline("tangent", "2026-10-12", {
      title: "Other-company market roundup",
    }),
    headline("filing", "2026-10-12", { kind: "filing" }),
  ];
  const data = {
    instrument: { symbol: "NVDA", name: "NVIDIA" },
    documents,
    market_news_ids: documents
      .filter((d) => d.id !== "withheld")
      .map((d) => d.id),
  };
  assert.deepEqual(
    currentCompanyHeadlines(data).map((d) => d.id),
    ["current"],
  );
  data.market_news_ids = [];
  assert.deepEqual(currentCompanyHeadlines(data), []);
  delete data.market_news_ids;
  assert.deepEqual(currentCompanyHeadlines(data), []);
});

test("latest-headline company switches do not inherit old-company sources", () => {
  const documents = [
    headline("nvda", "2026-10-12"),
    headline("avgo", "2026-10-11", { title: "Broadcom results" }),
  ];
  const data = {
    instrument: { symbol: "NVDA", name: "NVIDIA" },
    documents,
    market_news_ids: ["nvda", "avgo"],
  };
  assert.deepEqual(
    currentCompanyHeadlines(data).map((d) => d.id),
    ["nvda"],
  );
  data.instrument = { symbol: "AVGO", name: "Broadcom Inc." };
  assert.deepEqual(
    currentCompanyHeadlines(data).map((d) => d.id),
    ["avgo"],
  );
});
