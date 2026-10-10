import test from "node:test";
import assert from "node:assert/strict";
import { flowLayout, matchingMix } from "./incomeFlow.js";

const period = {
  kind: "annual",
  start: "2024-01-01",
  end: "2024-12-31",
  chartable: true,
  metrics: [
    {
      key: "revenue",
      value: "100",
      inputs: [
        { filing_url: "https://www.sec.gov/a.htm", concept: "Revenues" },
      ],
    },
  ],
  nodes: [
    { key: "revenue", value: "100", column: 0 },
    { key: "gross", value: "60", column: 1 },
    { key: "cost", value: "40", column: 1 },
  ],
  links: [
    { source: "revenue", target: "gross", value: "60" },
    { source: "revenue", target: "cost", value: "40" },
  ],
};
const group = {
  chartable: true,
  start: period.start,
  end: period.end,
  url: "https://www.sec.gov/a.htm",
  concept: "us-gaap:Revenues",
  total: "100",
  members: [
    { label: "A", value: "70" },
    { label: "B", value: "30" },
  ],
};

test("segment join requires exact period, filing, definition and total", () => {
  assert.equal(matchingMix(period, [group]).length, 1);
  for (const change of [
    { start: "2024-02-01" },
    { end: "2024-12-30" },
    { url: "https://www.sec.gov/b.htm" },
    { concept: "us-gaap:OtherRevenue" },
    { total: "99" },
    { chartable: false },
  ])
    assert.deepEqual(matchingMix(period, [{ ...group, ...change }]), []);
  assert.deepEqual(matchingMix({ ...period, kind: "trailing" }, [group]), []);
});

test("all bands share one scale; merging categories preserve exact total thickness", () => {
  const graph = flowLayout(period, group);
  const revenue = graph.nodes.find((row) => row.key === "revenue");
  const a = graph.nodes.find((row) => row.key === "source-0");
  const b = graph.nodes.find((row) => row.key === "source-1");
  assert.equal(a.height + b.height, revenue.height);
  assert.equal(
    graph.nodes.find((row) => row.key === "gross").height / revenue.height,
    0.6,
  );
  assert.ok(graph.links.every((row) => !row.path.includes("NaN")));
});

test("negative, missing and unsupported magnitudes are not scaled as positive flows", () => {
  for (const value of [null, "", "-1", "Infinity", "100000000000000000000"])
    assert.equal(
      flowLayout({
        ...period,
        nodes: [{ ...period.nodes[0], value }, ...period.nodes.slice(1)],
      }),
      null,
    );
  assert.equal(flowLayout({ ...period, chartable: false }), null);
  const graph = flowLayout({
    ...period,
    nodes: [
      period.nodes[0],
      { ...period.nodes[1], value: "0" },
      period.nodes[2],
    ],
  });
  assert.equal(graph.nodes[1].height, 0);
});

test("plot height is bounded and width never magnifies labels", () => {
  for (const available of [320, 980, 1920, 2800]) {
    const graph = flowLayout(period, group, available);
    assert.ok(graph.height <= 480);
    assert.ok(graph.width >= available);
    assert.equal(graph.nodes[1].width, 12);
    const many = {
      ...group,
      members: Array.from({ length: 8 }, (_, i) => ({
        label: String(i),
        value: "12.5",
      })),
    };
    const compact = flowLayout(period, many, available);
    assert.ok(compact.height <= 480);
    assert.equal(compact.nodes.length, period.nodes.length);
  }
});

test("unreconciled geography stays readable but cannot become a flow", async () => {
  const { matchingBreakdowns } = await import("./incomeFlow.js");
  const overlapping = { ...group, chartable: false };
  assert.equal(matchingBreakdowns(period, [overlapping]).length, 1);
  assert.equal(matchingMix(period, [overlapping]).length, 0);
});

test("trailing categories are invalidated when any original revenue input changes", async () => {
  const { matchingBreakdowns } = await import("./incomeFlow.js");
  const p = { ...period, kind: "trailing", id: "trailing:test" };
  const g = {
    ...group,
    period_id: p.id,
    calculated: true,
    revenue_inputs: structuredClone(p.metrics[0].inputs),
  };
  assert.equal(matchingBreakdowns(p, [g]).length, 1);
  p.metrics = structuredClone(p.metrics);
  p.metrics[0].inputs[0].filing_url = "changed";
  assert.equal(matchingBreakdowns(p, [g]).length, 0);
});

test("five countries connect to revenue at one scale with bounded, nonoverlapping labels", () => {
  const five = {
    ...group,
    members: [30, 26, 18, 16, 10].map((value, i) => ({
      label: `Country ${i}`,
      value: String(value),
    })),
  };
  for (const values of [
    five.members,
    [99.5, 0.1, 0.1, 0.1, 0.1, 0.1].map((value, i) => ({
      label: `Country ${i}`,
      value: String(value),
    })),
  ]) {
    const graph = flowLayout(period, { ...five, members: values }, 1440);
    const sources = graph.nodes.filter((n) => n.group),
      total = graph.nodes.find((n) => n.key === "revenue");
    assert.equal(sources.length, values.length);
    assert.equal(
      graph.links.filter((l) => l.target === "revenue").length,
      values.length,
    );
    assert.ok(
      Math.abs(sources.reduce((sum, n) => sum + n.height, 0) - total.height) <
        1e-8,
    );
    assert.ok(graph.height <= 480);
    for (let i = 1; i < sources.length; i++)
      assert.ok(
        sources[i].hitY >= sources[i - 1].hitY + sources[i - 1].hitHeight,
      );
  }
  assert.equal(
    flowLayout(period, { ...five, chartable: false }).nodes.length,
    period.nodes.length,
  );
});
