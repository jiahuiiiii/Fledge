import test from "node:test";
import assert from "node:assert/strict";
import {
  breakpointFor,
  defaultLayout,
  fitHeights,
  moveItem,
  ordered,
  reconcile,
  resizeItem,
  rowsFor,
  saveBody,
  offered,
} from "./workspaceLayout.js";

const place = (x, y, w, h) => ({
  lg: { x, y, w, h },
  md: { x: 0, y, w: 10, h },
  sm: { x: 0, y, w: 6, h },
});
const SPEC = [
  { id: "a", default: place(0, 0, 12, 4) },
  { id: "b", default: place(0, 4, 6, 8) },
  { id: "c", default: place(6, 4, 6, 8) },
];

test("no save gives the registry defaults at every width", () => {
  const { layouts, hidden, savedAt } = reconcile(SPEC, null);
  assert.deepEqual(layouts.lg, defaultLayout(SPEC, "lg"));
  assert.deepEqual(
    layouts.sm.map((i) => i.w),
    [6, 6, 6],
  );
  assert.deepEqual(hidden, []);
  assert.deepEqual(savedAt, []);
});

test("reconcile drops unknown, broken and repeated items and adds new widgets below", () => {
  const saved = {
    lg: [
      { i: "gone", x: 0, y: 0, w: 4, h: 4 },
      { i: "c", x: 0, y: 0, w: 12, h: 6 },
      { i: "c", x: 0, y: 9, w: 12, h: 6 },
      { i: "b", x: 8, y: 0, w: 6, h: 4 },
      null,
    ],
    hidden: ["gone", "a", "a"],
  };
  const { layouts, hidden, savedAt } = reconcile(SPEC, saved);
  assert.deepEqual(savedAt, ["lg"]);
  assert.deepEqual(hidden, ["a"]);
  assert.deepEqual(layouts.lg, [
    { i: "c", x: 0, y: 0, w: 12, h: 6 },
    { i: "a", x: 0, y: 6, w: 12, h: 4 },
    { i: "b", x: 0, y: 10, w: 6, h: 8 },
  ]);
  assert.deepEqual(layouts.md, defaultLayout(SPEC, "md"));
});

test("heights follow content in whole rows", () => {
  assert.equal(rowsFor(0), 1);
  assert.equal(rowsFor(100), 7);
  const fitted = fitHeights(defaultLayout(SPEC, "lg"), { b: 100 });
  assert.deepEqual(
    fitted.map((i) => i.h),
    [4, 7, 8],
  );
  // Measured empty: one row, not the default height left as a blank gap.
  assert.deepEqual(
    fitHeights(defaultLayout(SPEC, "lg"), { a: 0 }).map((i) => i.h),
    [1, 8, 8],
  );
});

test("keyboard moves swap places in reading order and stay on the page", () => {
  const lg = defaultLayout(SPEC, "lg");
  assert.deepEqual(
    ordered(lg).map((i) => i.i),
    ["a", "b", "c"],
  );
  const up = moveItem(lg, "b", -1, 12);
  assert.deepEqual(
    ordered(up).map((i) => i.i),
    ["b", "a", "c"],
  );
  // A full-width widget swapping into a half-width slot keeps inside 12 columns.
  const down = moveItem(lg, "a", 1, 12);
  assert.ok(down.every((i) => i.x + i.w <= 12));
  assert.equal(moveItem(lg, "a", -1, 12), lg);
  // Hidden widgets are skipped when choosing the neighbour.
  assert.deepEqual(
    ordered(moveItem(lg, "c", -1, 12, ["b"])).map((i) => i.i),
    ["c", "a", "b"],
  );
});

test("keyboard resize keeps the minimum and the page edge", () => {
  const lg = defaultLayout(SPEC, "lg");
  assert.deepEqual(
    resizeItem(lg, "c", 3, 12).find((i) => i.i === "c"),
    { i: "c", x: 3, y: 4, w: 9, h: 8 },
  );
  assert.equal(resizeItem(lg, "b", -10, 12, 3).find((i) => i.i === "b").w, 3);
});

test("only arranged widths are saved, with hidden widgets", () => {
  const state = reconcile(SPEC, {
    sm: defaultLayout(SPEC, "sm"),
    hidden: ["b"],
  });
  assert.deepEqual(Object.keys(saveBody(state)).sort(), ["hidden", "sm"]);
  assert.equal(breakpointFor(1200), "lg");
  assert.equal(breakpointFor(900), "md");
  assert.equal(breakpointFor(640), "sm");
  // At exactly a breakpoint the grid still shows the narrower layout.
  assert.equal(breakpointFor(1100), "md");
  assert.equal(breakpointFor(860), "sm");
});

const WITH_OPTIONAL = [
  ...SPEC,
  { id: "d", optional: true, modes: ["data"], default: place(0, 20, 6, 4) },
  {
    id: "e",
    optional: true,
    when: (c) => !c.recorded,
    default: place(6, 20, 6, 4),
  },
];

test("optional widgets start hidden until the user adds them", () => {
  assert.deepEqual(reconcile(WITH_OPTIONAL, null).hidden, ["d", "e"]);
  // A save from before they existed doesn't show them either.
  const old = { lg: defaultLayout(SPEC, "lg"), hidden: ["b"] };
  assert.deepEqual(reconcile(WITH_OPTIONAL, old).hidden, ["b", "d", "e"]);
  // Once added and saved, a widget stays shown; hidden ones stay hidden.
  const added = { lg: defaultLayout(WITH_OPTIONAL, "lg"), hidden: ["e"] };
  assert.deepEqual(reconcile(WITH_OPTIONAL, added).hidden, ["e"]);
});

test("Pro-only and context-dependent widgets are offered only where they apply", () => {
  const ids = (list) => list.map((w) => w.id);
  assert.deepEqual(ids(offered(WITH_OPTIONAL, "explain", {})), [
    "a",
    "b",
    "c",
    "e",
  ]);
  assert.deepEqual(ids(offered(WITH_OPTIONAL, "data", { recorded: true })), [
    "a",
    "b",
    "c",
    "d",
  ]);
});
