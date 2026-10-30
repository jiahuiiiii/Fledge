import test from "node:test";
import assert from "node:assert/strict";
import { statusLine, watchItems } from "./ideaWatch.js";

const event = {
  condition_id: "e1",
  role: "required",
  description: "Arm loses its licence case",
};
const number = {
  condition_id: "c1",
  role: "risk",
  metric: "operating_margin",
  operator: "<=",
  threshold: "20",
};

test("a draft says plainly that nothing is watched", () => {
  assert.equal(statusLine(null), "No idea saved yet.");
  assert.equal(
    statusLine({ status: "draft", events: [], conditions: [] }),
    "Not watching yet. Add something to watch in Edit, then approve it.",
  );
  const draft = { status: "draft", events: [event], conditions: [number] };
  assert.equal(
    statusLine(draft),
    "Not watching yet. The 2 things under “What I’m watching” are saved but not approved. Approve them to start alerts.",
  );
  assert.deepEqual(
    watchItems(draft).map((i) => [i.type, i.label, i.state]),
    [
      ["Event", "Arm loses its licence case", "Not watching"],
      ["Risk", "Operating margin at most 20%", "Not watching"],
    ],
  );
});

test("a watched idea shows each item's latest state", () => {
  const version = {
    status: "monitoring",
    events: [event],
    conditions: [number],
  };
  assert.equal(
    statusLine(version),
    "Watching 2 things. Waiting for the first check.",
  );
  const evaluation = {
    created_at: "2026-10-20T06:02:00Z",
    event_results: [{ condition_id: "e1", state: "confirmed" }],
    results: [{ condition_id: "c1", outcome: "not_met" }],
  };
  assert.equal(
    statusLine(version, evaluation),
    "Watching 2 things. Last checked 20 Oct, 14:02 SGT.",
  );
  assert.deepEqual(
    watchItems(version, evaluation).map((i) => i.state),
    ["Happened", "Risk threshold reached"],
  );
  assert.equal(watchItems(version)[0].state, "Not checked yet");
});
