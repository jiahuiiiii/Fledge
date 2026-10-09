import test from "node:test";
import assert from "node:assert/strict";
import { countedTone, newsSourceStatus } from "./newsPresentation.js";
import { newsTone } from "./companySnapshot.js";
test("stories, relevance and distinct developments remain separate and counts reconcile", () => {
  const result = countedTone({
    selected: 65,
    relevant: 30,
    counted_groups: 20,
    counts: { positive: 8, neutral: 6, mixed: 2, negative: 4, unclear: 0 },
  });
  assert.deepEqual(result, {
    positive: 8,
    neutral: 8,
    negative: 4,
    unclear: 0,
    total: 20,
    selected: 65,
    relevant: 30,
    reconciled: true,
  });
});
test("unclear groups remain in the total; older inconsistent group metadata is identified", () => {
  assert.equal(
    countedTone({ counts: { positive: 2, unclear: 3 }, counted_groups: 4 })
      .total,
    5,
  );
  assert.equal(
    countedTone({ counts: { positive: 2, unclear: 3 }, counted_groups: 4 })
      .reconciled,
    false,
  );
  assert.equal(
    newsTone({
      withheld: true,
      summary: { news: { selected: 65, counts: { positive: 8 } } },
    }),
    null,
  );
});
test("news status counts news feeds only, adds saved Finnhub once, and uses actual latest check", () => {
  const data = {
    provider_status: [
      {
        provider: "a",
        channel: "news",
        status: "failed",
        checked_at: "2026-10-09T05:00:00Z",
      },
      {
        provider: "b",
        channel: "news",
        status: "ready",
        checked_at: "2026-10-09T06:00:00Z",
      },
      { provider: "x", channel: "social", status: "blocked" },
    ],
    market: {
      status: { completed_at: "2026-10-09T05:59:00Z", news_error: null },
    },
    social_status: [
      { enabled: true, error: "failed" },
      { enabled: false, error: "off" },
    ],
  };
  const s = newsSourceStatus(data);
  assert.equal(s.feeds.length, 3);
  assert.equal(s.failed.length, 1);
  assert.equal(s.social.length, 1);
  assert.equal(s.latest, "2026-10-09T06:00:00Z");
  data.provider_status.push({
    provider: "finnhub",
    channel: "news",
    status: "ready",
  });
  assert.equal(newsSourceStatus(data).feeds.length, 3);
});

test("scheduled waits, unchecked feeds, real failures and optional sources stay distinct", () => {
  const result = newsSourceStatus({
    provider_status: [
      {
        provider: "cnbc",
        label: "CNBC",
        channel: "news",
        status: "ready",
        matched: 0,
      },
      {
        provider: "wsj",
        channel: "news",
        status: "deferred",
        checked_at: null,
      },
      {
        provider: "yahoo",
        channel: "news",
        status: "failed",
        message: "HTTP 404",
      },
      { provider: "alpha", channel: "news", status: "not_loaded" },
      { provider: "x", channel: "social", status: "disabled" },
    ],
  });
  assert.equal(result.feeds.length, 4);
  assert.deepEqual(
    result.checked.map((r) => r.provider),
    ["cnbc"],
  );
  assert.deepEqual(
    result.waiting.map((r) => r.provider),
    ["wsj"],
  );
  assert.deepEqual(
    result.failed.map((r) => r.provider),
    ["yahoo"],
  );
  assert.deepEqual(
    result.unchecked.map((r) => r.provider),
    ["alpha"],
  );
  assert.deepEqual(
    result.optional.map((r) => r.provider),
    ["x"],
  );
  assert.equal(result.latest, undefined);
});
