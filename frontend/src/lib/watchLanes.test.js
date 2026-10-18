import test from "node:test";
import assert from "node:assert/strict";
import {
  watchLaneLabel,
  watchFrequencyLabel,
  separateWatchSteps,
} from "./watchLanes.js";

test("watch history names news and discussion checks while preserving legacy labels", () => {
  assert.equal(watchLaneLabel("fast"), "News check");
  assert.equal(watchLaneLabel("slow"), "Discussion check");
  assert.equal(watchLaneLabel("combined"), "");
  assert.equal(watchLaneLabel(undefined), "");
  assert.equal(watchLaneLabel("<script>"), "");
  assert.equal(watchLaneLabel("__proto__"), "");
  assert.equal(
    watchFrequencyLabel({ lanes_enabled: true }),
    "Discussion checks every",
  );
  assert.equal(watchFrequencyLabel({ interval_minutes: 60 }), "Check every");
  assert.match(separateWatchSteps.separate_fast_lane, /news checks/);
  assert.match(separateWatchSteps.separate_slow_lane, /discussion checks/);
});
