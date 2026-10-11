import test from "node:test";
import assert from "node:assert/strict";
import { growthTakeaway, peTakeaway } from "./overviewTakeaways.js";
const member = (symbol, value, end = "2025-12-31") => ({
  symbol,
  performance: {
    status: "available",
    method: "sec-performance-1",
    reports: {
      annual: {
        form: "10-K",
        period_type: "annual",
        period_end: end,
        accession: symbol,
        metrics: [
          {
            key: "revenue_growth",
            value: String(value),
            unit: "percent",
            start: "2025-01-01",
            end,
            inputs: [
              {
                namespace: "us-gaap",
                concept: "Revenues",
                value: "120",
                unit: "USD",
                start: "2025-01-01",
                end,
                accession: symbol,
              },
              {
                namespace: "us-gaap",
                concept: "Revenues",
                value: "100",
                unit: "USD",
                start: "2024-01-01",
                end: "2024-12-31",
                accession: symbol,
              },
            ],
          },
        ],
      },
    },
  },
});

const ref = (symbol, pe) => ({
  symbol,
  available: true,
  reference: { symbol, metrics: { earnings: { value: String(pe) } } },
});

test("growth takeaway counts comparable peers and averages them", () => {
  const sector = {
    symbol: "AAA",
    members: [
      member("AAA", 20),
      member("BBB", 30),
      member("CCC", 10),
      member("DDD", 50),
      member("OLD", 90, "2025-03-01"),
    ],
  };
  assert.equal(
    growthTakeaway(sector),
    "That is slower than 2 of 3 comparable peers (peer average 30.0%).",
  );
});

test("growth takeaway is withheld without a comparable peer", () => {
  assert.equal(
    growthTakeaway({ symbol: "AAA", members: [member("AAA", 20)] }),
    null,
  );
  assert.equal(growthTakeaway(null), null);
});

test("P/E takeaway compares with the peer average only", () => {
  const sector = {
    symbol: "AAA",
    members: ["AAA", "BBB", "CCC"].map((s) => ({ symbol: s })),
  };
  assert.equal(
    peTakeaway(sector, [ref("AAA", 40), ref("BBB", 50), ref("CCC", 70)]),
    "That is below the 60.0× average of 2 peers on the same measure.",
  );
  assert.equal(peTakeaway(sector, [ref("AAA", 40)]), null);
});
