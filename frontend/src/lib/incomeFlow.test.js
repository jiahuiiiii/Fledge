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
