import test from "node:test";
import assert from "node:assert/strict";
import {
  sentimentSummaryLabel,
  priceComparisonText,
} from "./sentimentSummary.js";

test("leaning shows its usable denominator and the separate unclear count", () => {
  assert.equal(
    sentimentSummaryLabel({
      tone: "positive leaning",
      counts: { positive: 5, negative: 2, neutral: 2, unclear: 3 },
    }),
    "positive leaning · 5 of 9 clear readings · 3 unclear",
  );
  assert.equal(
    sentimentSummaryLabel({
      tone: "thin sample",
      counts: { positive: 4, unclear: 1 },
    }),
    "thin sample · 4 clear readings · 1 unclear",
  );
});
test("price display formats the server result without calculating a new return", () => {
  assert.equal(
    priceComparisonText({
      status: "compared",
      amount: "340",
      difference_percent: "-5.592269673460321",
      relation: "below",
      reference: { close: "360.14", date: "2026-10-08" },
    }),
    "$340 target · 5.6% below the $360.14 saved close (2026-10-08)",
  );
  assert.equal(priceComparisonText({ status: "unverified_post_time" }), null);
});
