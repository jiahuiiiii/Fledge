import test from "node:test";
import assert from "node:assert/strict";
import {
  plainSales,
  plainMargin,
  plainCash,
  plainForecast,
  compareVerdicts,
  formatGrowth,
  formatMargin,
  formatPe,
} from "./plainTabs.js";

const period = (values) => ({
  metrics: Object.entries(values).map(([key, value]) => ({ key, value: String(value) })),
});

test("sales says whether the business grew, in plain words", () => {
  const sales = plainSales(period({ revenue: 115e9 }), period({ revenue: 100e9 }), "Acme");
  assert.equal(sales.value, "US$115bn");
  assert.match(sales.text, /Up 15% on a year earlier, so the business is growing/);
  assert.match(plainSales(period({ revenue: 90 }), period({ revenue: 100 })).text, /Down 10%/);
  assert.match(plainSales(period({ revenue: 100.4 }), period({ revenue: 100 })).text, /About the same/);
  assert.equal(plainSales(period({ revenue: 5 }), null).change, null);
  assert.equal(plainSales(period({}), null), null);
});

test("profit per dollar is in cents with a plain comparison", () => {
  assert.equal(plainMargin(period({ operating_margin: 45.6 })).value, "46¢");
  assert.match(plainMargin(period({ operating_margin: 45.6 })).text, /That is high/);
  assert.match(plainMargin(period({ operating_margin: 15 })).text, /typical/);
  assert.match(plainMargin(period({ operating_margin: 4 })).text, /thin/);
  const loss = plainMargin(period({ operating_margin: -12 }), "Acme");
  assert.equal(loss.value, "−12¢");
  assert.match(loss.text, /lost about 12¢ on every \$1/);
});

test("cash left over explains positive and negative", () => {
  assert.match(plainCash(period({ free_cash_flow: 7e9 })).text, /pays its own way/);
  assert.match(plainCash(period({ free_cash_flow: -2e6 })).text, /spent more cash/);
  assert.equal(plainCash(period({})), null);
});

test("forecast uses only current, still-future guidance", () => {
  const forecast = { label: "Revenue", low: "80000000000", high: "81000000000", unit: "USD" };
  const management = {
    releases: [
      {
        current: true,
        sections: [
          { heading: "Old quarter", period_end: "2026-01-01", forecasts: [forecast] },
          { heading: "Next quarter", period_end: "2026-12-31", forecasts: [forecast] },
        ],
      },
    ],
  };
  const read = plainForecast(management, new Date("2026-10-26"));
  assert.equal(read.period, "Next quarter");
  assert.equal(read.value, "Revenue: US$80bn to US$81bn");
  assert.equal(plainForecast({ releases: [{ current: false, sections: [] }] }), null);
  assert.equal(plainForecast(null), null);
});

test("compare verdicts name who the company beats", () => {
  const rows = [
    { symbol: "MSFT", name: "Microsoft", growth: 15, margin: 46, pe: 35 },
    { symbol: "GOOGL", name: "Alphabet", growth: 12, margin: 32, pe: 24 },
    { symbol: "AMZN", name: "Amazon", growth: 11, margin: 11, pe: 38 },
    { symbol: "AAPL", name: "Apple", growth: 18, margin: 31, pe: null },
  ];
  const [growth, margin, pe] = compareVerdicts(rows);
  assert.equal(growth.text, "Sales are growing **faster** than Alphabet and Amazon.");
  assert.equal(growth.tone, "good");
  assert.equal(margin.text, "Keeps **more profit** from each $1 of sales than all 3 peers.");
  assert.match(pe.text, /\*\*pricier\*\* .* than Alphabet\./);
  assert.equal(pe.tone, "neutral");
  assert.deepEqual(compareVerdicts([rows[0]]), []);
  assert.deepEqual(compareVerdicts([{ ...rows[0], growth: null, margin: null, pe: null }, rows[1]]), []);
});

test("table formatting", () => {
  assert.equal(formatGrowth(15.4), "+15%");
  assert.equal(formatGrowth(-3), "−3%");
  assert.equal(formatGrowth(null), "–");
  assert.equal(formatMargin(45.6), "46¢");
  assert.equal(formatPe(34.6), "35×");
});
