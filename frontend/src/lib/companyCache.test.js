import test from "node:test";
import assert from "node:assert/strict";
import { createCompanyCache, keepFinancials } from "./companyCache.js";

test("cache is per account and keeps only the most recent companies", () => {
  const cache = createCompanyCache(2);
  cache.put("a", "x", { data: 1 });
  assert.equal(cache.get("b", "x"), null);
  assert.equal(cache.get(null, "x"), null);
  cache.put("a", "y", { data: 2 });
  cache.get("a", "x"); // x is now the most recent
  cache.put("a", "z", { data: 3 });
  assert.equal(cache.get("a", "y"), null);
  assert.deepEqual(cache.get("a", "x"), { data: 1 });
  cache.put(null, "w", { data: 4 });
  assert.equal(cache.size, 2);
});

test("cache entries merge data and price separately", () => {
  const cache = createCompanyCache();
  cache.put("a", "x", { data: 1 });
  cache.put("a", "x", { priceRead: 2 });
  assert.deepEqual(cache.get("a", "x"), { data: 1, priceRead: 2 });
  cache.clear();
  assert.equal(cache.get("a", "x"), null);
});

test("a read without financials keeps the same company's figures", () => {
  const kept = {
    instrument: { id: "x" },
    financials_pending: false,
    financial_depth: "depth",
    income_flow: "flow",
    segment_revenue: "segments",
  };
  const next = {
    instrument: { id: "x" },
    financials_pending: true,
    financial_depth: null,
    income_flow: null,
    segment_revenue: null,
    news: "new",
  };
  assert.deepEqual(keepFinancials(kept, next), {
    ...next,
    ...kept,
    news: "new",
    financials_pending: false,
  });
  assert.equal(keepFinancials({ ...kept, instrument: { id: "y" } }, next), next);
  assert.equal(keepFinancials({ ...kept, financials_pending: true }, next), next);
  assert.equal(keepFinancials(null, next), next);
  const full = { ...next, financials_pending: false, financial_depth: "fresh" };
  assert.equal(keepFinancials(kept, full), full);
});
