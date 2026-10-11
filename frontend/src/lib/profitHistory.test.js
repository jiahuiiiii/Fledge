import test from "node:test";
import assert from "node:assert/strict";
import { consistentProfitRows, profitOptions } from "./profitHistory.js";
import { historyPath, metric } from "./financialStory.js";
const fact = (key, value) => ({
  key,
  value,
  unit: "USD",
  start: "2021-09-03",
  end: "2022-09-01",
  label:
    key === "net_parent"
      ? "Net income attributable to parent"
      : "Net result including non-controlling interests",
  inputs: [
    {
      concept: key === "net_parent" ? "NetIncomeLoss" : "ProfitLoss",
      value,
      filing_url: "https://www.sec.gov/example",
    },
  ],
});
const row = (end, parent, whole) => {
  const p = fact("net_parent", parent),
    w = fact("net_consolidated", whole);
  p.end = w.end = end;
  return {
    id: end,
    end,
    metrics: [
      { key: "revenue", value: "100" },
      p,
      w,
      { ...(whole !== null ? w : p), key: "net_income" },
    ],
  };
};
const fixture = () => ({
  status: "available",
  annual: [
    row("2022-09-01", "8687000000", "8687000000"),
    row("2023-08-31", "-5833000000", null),
  ],
});

test("MU positive-to-negative profit connects using its available parent-only history", () => {
  const story = fixture(),
    before = structuredClone(story),
    choice = profitOptions(story)[0];
  assert.equal(choice.key, "net_parent");
  const rows = consistentProfitRows(story.annual, choice.key);
  assert.deepEqual(
    rows.map((r) => metric(r, "net_income").value),
    ["8687000000", "-5833000000"],
  );
  assert.equal(
    (
      historyPath(
        rows,
        "net_income",
        (r) => r.end,
        (v) => v,
      ).match(/L/g) || []
    ).length,
    1,
  );
  assert.equal(
    metric(rows[0], "net_income").inputs,
    metric(story.annual[0], "net_parent").inputs,
  );
  assert.equal(metric(rows[0], "revenue"), metric(story.annual[0], "revenue"));
  assert.deepEqual(story, before);
});

test("one default uses all period types and prefers parent on equal coverage", () => {
  const story = fixture();
  story.quarterly = [row("2023-11-30", "1", "2")];
  story.trailing = [row("2023-11-30", "1", "2")];
  assert.equal(profitOptions(story)[0].key, "net_parent");
  story.annual[1] = row("2023-08-31", "2", "3");
  assert.equal(profitOptions(story)[0].key, "net_parent");
  for (const kind of ["annual", "quarterly", "trailing"])
    assert.ok(
      consistentProfitRows(story[kind], "net_parent").every(
        (r) =>
          metric(r, "net_income").label === "Net income attributable to parent",
      ),
    );
});

test("whole-group default is used when that is the better-covered saved series", () => {
  const story = {
    status: "available",
    annual: [row("2022-09-01", null, "20"), row("2023-08-31", "18", "21")],
  };
  assert.equal(profitOptions(story)[0].key, "net_consolidated");
  assert.deepEqual(
    consistentProfitRows(story.annual, "net_consolidated").map(
      (r) => metric(r, "net_income").value,
    ),
    ["20", "21"],
  );
});

test("explicit whole-group selection leaves missing whole-group results unknown", () => {
  const story = fixture();
  const rows = consistentProfitRows(story.annual, "net_consolidated");
  assert.equal(metric(rows[1], "net_income").value, null);
  assert.match(
    metric(rows[1], "net_income").reason,
    /Whole group.*not available/,
  );
  assert.doesNotMatch(
    historyPath(
      rows,
      "net_income",
      () => 0,
      (v) => v,
    ),
    /L/,
  );
});

test("a conflicting consolidated result cannot be hidden by selecting the parent", () => {
  const story = fixture();
  const original = metric(story.annual[1], "net_income");
  original.value = null;
  original.reason = "Conflicting values in the selected filing.";
  original.inputs = [
    { concept: "ProfitLoss", value: "10" },
    { concept: "ProfitLoss", value: "11" },
  ];
  assert.deepEqual(
    metric(consistentProfitRows(story.annual, "net_parent")[1], "net_income"),
    original,
  );
});

test("withdrawn or older histories do not acquire a new scope or substitute data", () => {
  assert.deepEqual(profitOptions({ ...fixture(), status: "unavailable" }), []);
  const rows = [{ end: "2023-08-31", metrics: [fact("net_income", "10")] }];
  assert.deepEqual(profitOptions({ status: "available", annual: rows }), []);
  assert.equal(consistentProfitRows(rows, undefined), rows);
  assert.equal(
    metric(consistentProfitRows(rows, "net_parent")[0], "net_income").value,
    null,
  );
});

test("invalid values and other currencies do not increase coverage or become chart points", () => {
  for (const value of [true, NaN, Infinity, "", null, "10000000000000000"]) {
    const story = fixture();
    metric(story.annual[0], "net_parent").value = value;
    assert.equal(
      metric(consistentProfitRows(story.annual, "net_parent")[0], "net_income")
        .value,
      null,
    );
  }
  const story = fixture();
  metric(story.annual[0], "net_parent").unit = "EUR";
  assert.equal(
    metric(consistentProfitRows(story.annual, "net_parent")[0], "net_income")
      .value,
    null,
  );
});
