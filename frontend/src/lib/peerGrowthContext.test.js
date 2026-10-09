import test from "node:test";
import assert from "node:assert/strict";
import { peerGrowthContext } from "./peerGrowthContext.js";
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
test("peer sentence uses only comparable saved fiscal-year figures, retaining missing peers", () => {
  assert.match(
    peerGrowthContext({
      symbol: "AVGO",
      members: [
        member("AVGO", 20),
        member("AAA", 30),
        member("BBB", 40),
        member("CCC", 10),
        { symbol: "MISSING" },
      ],
    }),
    /slower than 2 of 3 comparable peers/,
  );
  assert.match(
    peerGrowthContext({
      symbol: "AVGO",
      members: [member("AVGO", 20), member("OLD", 90, "2023-12-31")],
    }),
    /unavailable/,
  );
});
