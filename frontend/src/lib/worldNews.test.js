import test from "node:test";
import assert from "node:assert/strict";
import { filterArticles, themeCounts, checkBlocker } from "./worldNews.js";

const articles = [
  { id: "1", themes: ["rates", "economy"], mentions: [], links: [] },
  { id: "2", themes: ["geopolitics", "energy"], mentions: [], links: [{}] },
  { id: "3", themes: ["trade"], mentions: ["aapl"], links: [] },
  { id: "4", themes: [], mentions: [], links: [] },
];

test("filters world headlines by theme or by the user's companies", () => {
  assert.deepEqual(filterArticles(articles, "all").map((a) => a.id), ["1", "2", "3", "4"]);
  assert.deepEqual(filterArticles(articles, "rates").map((a) => a.id), ["1"]);
  assert.deepEqual(filterArticles(articles, "mine").map((a) => a.id), ["2", "3"]);
  assert.deepEqual(filterArticles(articles, "regulation"), []);
});

test("counts headlines per theme", () => {
  const counts = themeCounts(articles, [
    { id: "rates", label: "Rates" },
    { id: "trade", label: "Trade" },
    { id: "regulation", label: "Regulation" },
  ]);
  assert.deepEqual(counts.map((t) => t.count), [1, 1, 0]);
});

test("explains why the AI check cannot run", () => {
  const ready = {
    companies: [{ id: "a" }],
    articles,
    ai: { available: true },
  };
  assert.equal(checkBlocker(ready), null);
  assert.match(checkBlocker({ ...ready, companies: [] }), /watchlist/);
  assert.match(checkBlocker({ ...ready, articles: [] }), /Refresh/);
  assert.match(checkBlocker({ ...ready, ai: { available: false } }), /switched on/);
});
