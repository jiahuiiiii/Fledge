import test from "node:test";
import assert from "node:assert/strict";
import {
  number,
  money,
  previousYear,
  incomeInsights,
  balanceInsights,
  balanceBlocks,
  blockLayout,
  historyPath,
  borrowingTrend,
} from "./financialStory.js";
const row = (key, value, end = "2025-09-30", start = null) => ({
  key,
  label: key,
  value,
  end,
  start,
  inputs: [{ concept: key }],
});
const period = (end, values) => ({
  end,
  metrics: Object.entries(values).map(([key, value]) =>
    row(key, value, end, "2024-10-01"),
  ),
});

test("missing and nonfinite amounts never become zero; signed amounts remain", () => {
  for (const value of [null, undefined, "", NaN, Infinity])
    assert.equal(number(value), null);
  assert.equal(money("0"), "US$0");
  assert.equal(money("-1000000000"), "−US$1bn");
});
test("year comparison requires the preceding fiscal year and same revenue concept", () => {
  const current = period("2025-09-30", { revenue: "120" }),
    prior = period("2024-09-30", { revenue: "100" });
  assert.match(incomeInsights(current, prior)[0].text, /20.0% higher/);
  assert.equal(previousYear([period("2023-09-30", {})], current), null);
  prior.metrics[0].inputs[0].concept = "DifferentDefinition";
  assert.equal(incomeInsights(current, prior)[0].tone, "unknown");
  prior.metrics[0].inputs[0].concept = "revenue";
  prior.metrics[0].value = "0";
  assert.equal(incomeInsights(current, prior)[0].tone, "unknown");
});

test("growth carries its selected fiscal basis and both original comparison windows", () => {
  const current = period("2025-09-30", { revenue: "120" }),
    prior = period("2024-09-30", { revenue: "100" });
  prior.metrics[0].start = "2023-10-01";
  const trailing = incomeInsights(current, prior, "trailing")[0],
    annual = incomeInsights(current, prior, "annual")[0];
  assert.equal(trailing.basis, "Trailing 12 months");
  assert.equal(annual.basis, "Fiscal year");
  assert.match(
    trailing.period,
    /1 Oct 2024 – 30 Sept? 2025 vs 1 Oct 2023 – 30 Sept? 2024/,
  );
  assert.equal(annual.text, trailing.text);
  assert.deepEqual(trailing.rows, [current.metrics[0], prior.metrics[0]]);
});
test("loss and negative cash remaining are explained without ratings", () => {
  const current = period("2025-09-30", {
    revenue: "100",
    net_income: "-20",
    net_margin: "-20",
    operating_cash: "8",
    capital_spending: "10",
    free_cash_flow: "-2",
  });
  const readings = incomeInsights(current, null);
  assert.match(readings[1].text, /lost US\$20.0/);
  assert.match(readings[2].text, /fell short by US\$2/);
  assert.doesNotMatch(
    JSON.stringify(readings),
    /high quality|healthy|satisfactory/,
  );
});
test("missing current obligations stay unknown and cash does not establish repayment ability", () => {
  const current = {
    end: "2025-09-30",
    metrics: [
      row("current_assets", "60"),
      row("current_liabilities", null),
      row("debt", "68"),
      row("cash", "25"),
      row("net_debt", "43"),
      row("debt_equity", null),
    ],
  };
  assert.equal(balanceInsights(current)[0].tone, "unknown");
  assert.match(balanceInsights(current)[1].text, /US\$43 remains/);
});

test("cash remaining preserves the broader productive-asset definition", () => {
  const current = period("2025-09-30", {
    operating_cash: "30",
    capital_spending: "10",
    free_cash_flow: "20",
  });
  current.metrics.find((m) => m.key === "free_cash_flow").spending_basis =
    "productive_assets";
  const reading = incomeInsights(current, null).find((r) =>
    r.title.startsWith("Cash left"),
  );
  assert.match(reading.text, /software and other intangible assets/);
  assert.match(reading.text, /left US\$20/);
});
test("balance map reconciles classified and unclassified amounts and withholds negative equity", () => {
  const current = {
    end: "2025-09-30",
    metrics: [
      row("assets", "200"),
      row("liabilities", "90"),
      row("equity", "110"),
      row("cash", "25"),
      row("debt", "68"),
      row("payables", "8"),
      row("other_assets", "175"),
      row("other_liabilities", "14"),
    ],
  };
  assert.equal(
    balanceBlocks(current, "assets").reduce(
      (sum, r) => sum + Number(r.value),
      0,
    ),
    200,
  );
  assert.equal(
    balanceBlocks(current, "funding").reduce(
      (sum, r) => sum + Number(r.value),
      0,
    ),
    200,
  );
  current.metrics.find((r) => r.key === "other_assets").value = "174";
  assert.equal(balanceBlocks(current, "assets"), null);
  current.metrics.find((r) => r.key === "equity").value = "-10";
  assert.equal(balanceBlocks(current, "funding"), null);
});
test("treemap areas retain proportions, fill the canvas and do not overlap", () => {
  const rows = [100, 40, 25, 15, 10, 8, 2].map((value, i) =>
    row(String(i), String(value)),
  );
  const layout = blockLayout(rows, 500, 320);
  for (const tile of layout) {
    assert.ok(
      Math.abs(
        (tile.width * tile.height) / (500 * 320) - Number(tile.value) / 200,
      ) < 1e-12,
    );
    assert.ok(
      tile.x >= 0 &&
        tile.y >= 0 &&
        tile.x + tile.width <= 500.00001 &&
        tile.y + tile.height <= 320.00001,
    );
    for (const other of layout.filter((o) => o !== tile))
      assert.ok(
        Math.min(tile.x + tile.width, other.x + other.width) -
          Math.max(tile.x, other.x) <
          1e-9 ||
          Math.min(tile.y + tile.height, other.y + other.height) -
            Math.max(tile.y, other.y) <
            1e-9,
      );
  }
});
test("history gaps and changed net-result definitions break paths; bridge input count does not", () => {
  const rows = ["2021", "2022", "2023", "2024", "2025"].map((year) =>
    period(`${year}-09-30`, { net_income: "10" }),
  );
  rows[1].metrics[0].value = null;
  rows[3].metrics[0].label = "Parent income";
  rows[4].metrics[0].label = "Parent income";
  rows[4].metrics[0].inputs.push({ concept: "net_income" });
  const path = historyPath(
    rows,
    "net_income",
    (r) => r.end.slice(0, 4),
    (v) => v,
  );
  assert.equal((path.match(/M/g) || []).length, 3);
  assert.equal((path.match(/L/g) || []).length, 1);
  assert.equal(
    (
      historyPath(
        [rows[0], rows[4]],
        "net_income",
        () => 0,
        () => 0,
      ).match(/M/g) || []
    ).length,
    2,
  );
});

test("borrowing trend describes a compatible ratio change without assuming repayment", () => {
  const current = period("2025-09-30", { debt_equity: "60" }),
    prior = period("2024-09-30", { debt_equity: "80" });
  assert.equal(borrowingTrend(current, prior).title, "Borrowing / equity fell");
  assert.match(borrowingTrend(current, prior).detail, /does not establish/);
  prior.metrics[0].value = null;
  assert.equal(borrowingTrend(current, prior), null);
});
