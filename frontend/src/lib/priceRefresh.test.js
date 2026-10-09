import test from "node:test";
import assert from "node:assert/strict";
import {
  preferPriceRead,
  priceRefreshDelay,
  latestPriceQuote,
  quoteMovement,
} from "./priceRefresh.js";

test("price updates respect source access, failure and shared cooldown", () => {
  const data = {
    available: true,
    configured: true,
    next_refresh_at: "2026-10-08T15:01:00Z",
  };
  assert.equal(
    priceRefreshDelay(data, Date.parse("2026-10-08T15:00:30Z")),
    30000,
  );
  assert.equal(priceRefreshDelay(data, Date.parse("2026-10-08T15:02:00Z")), 0);
  assert.equal(priceRefreshDelay({ ...data, available: false }), null);
  assert.equal(priceRefreshDelay({ ...data, configured: false }), null);
  assert.equal(priceRefreshDelay({ ...data, error: "Access denied" }), null);
});

const yahoo = (overrides = {}, series = {}) => ({
  available: true,
  snapshot: {
    series: {
      omitted_sessions: 0,
      latest_quote: {
        price: "105",
        quoted_at: "2026-10-08T15:01:00Z",
        session: "regular session",
        ...overrides,
      },
      bars: [
        { date: "2026-10-07", close: "100", provisional: false },
        { date: "2026-10-08", close: "104", provisional: true },
      ],
      ...series,
    },
  },
});

test("Yahoo change uses its own completed close, including negative and zero moves", () => {
  const market = {
    quote: {
      quote: {
        quoted_at: "2026-10-07T15:00:00Z",
        change: "99",
        change_percent: "99",
      },
    },
  };
  assert.deepEqual(quoteMovement(market, yahoo()), {
    change: 5,
    percent: 5,
    referenceDate: "2026-10-07",
  });
  assert.deepEqual(quoteMovement(market, yahoo({ price: "95" })), {
    change: -5,
    percent: -5,
    referenceDate: "2026-10-07",
  });
  assert.deepEqual(quoteMovement(market, yahoo({ price: "100" })), {
    change: 0,
    percent: 0,
    referenceDate: "2026-10-07",
  });
});

test("extended-session comparison observes the New York date and completed closing bar", () => {
  const bars = [
    { date: "2026-10-07", close: "100", provisional: false },
    { date: "2026-10-08", close: "104", provisional: false },
    { date: "2026-10-09", close: "106", provisional: false },
  ];
  assert.equal(
    quoteMovement(
      null,
      yahoo(
        { session: "after-hours", quoted_at: "2026-10-09T00:01:00Z" },
        { bars },
      ),
    ).referenceDate,
    "2026-10-08",
  );
  assert.equal(
    quoteMovement(null, yahoo({ session: "pre-market" }, { bars }))
      .referenceDate,
    "2026-10-07",
  );
});

test("missing or ambiguous Yahoo baselines never borrow another supplier's change", () => {
  const market = { quote: { quote: { change: "5", change_percent: "5" } } };
  for (const history of [
    yahoo({}, { bars: [] }),
    yahoo({}, { omitted_sessions: 1 }),
    yahoo(
      {},
      { bars: [{ date: "2026-10-07", close: "0", provisional: false }] },
    ),
    yahoo(
      {},
      { bars: [{ date: "2026-10-07", close: "100", provisional: true }] },
    ),
    yahoo({ session: "unknown" }),
  ])
    assert.equal(quoteMovement(market, history), null);
  assert.deepEqual(quoteMovement(market, { ...yahoo(), available: false }), {
    change: 5,
    percent: 5,
    referenceDate: null,
  });
});

test("Finnhub zero change survives and missing percentages remain unknown", () => {
  assert.deepEqual(
    quoteMovement({ quote: { quote: { change: "0", change_percent: null } } }),
    { change: 0, percent: null, referenceDate: null },
  );
  assert.equal(
    quoteMovement({ quote: { quote: { change: null, change_percent: "1" } } }),
    null,
  );
});

test("late reads preserve newer prices; company change and withdrawal replace them", () => {
  const newer = {
    data: {
      symbol: "AVGO",
      available: true,
      snapshot: { retrieved_at: "2026-10-08T15:01:00Z" },
    },
  };
  const older = {
    data: { ...newer.data, snapshot: { retrieved_at: "2026-10-08T15:00:00Z" } },
  };
  assert.equal(
    preferPriceRead(newer, older).data.snapshot,
    newer.data.snapshot,
  );
  const withdrawn = {
    data: { symbol: "AVGO", available: false, snapshot: null },
  };
  assert.equal(preferPriceRead(newer, withdrawn), withdrawn);
  const another = { data: { ...older.data, symbol: "MSFT" } };
  assert.equal(preferPriceRead(newer, another), another);
});

test("header uses the newer separately attributed quote and withholds withdrawn data", () => {
  const market = { quote: { quote: { quoted_at: "2026-10-08T15:00:00Z" } } };
  const quote = { quoted_at: "2026-10-08T15:01:00Z", price: "123.45" };
  const history = {
    available: true,
    snapshot: { series: { latest_quote: quote } },
  };
  assert.equal(latestPriceQuote(market, history), quote);
  assert.equal(
    latestPriceQuote(market, { ...history, available: false }),
    null,
  );
  assert.equal(
    latestPriceQuote(
      { quote: { quote: { quoted_at: "2026-10-08T15:02:00Z" } } },
      history,
    ),
    null,
  );
});
