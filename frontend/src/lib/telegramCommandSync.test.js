import test from "node:test";
import assert from "node:assert/strict";
import { syncStep } from "./telegramCommandSync.js";

test("commands off stops polling", () => {
  assert.deepEqual(syncStep(undefined, { enabled: false, latest: null }), {
    stop: true,
    changed: false,
    last: undefined,
  });
  assert.equal(syncStep(undefined, null).stop, true);
});

test("the first answer is a baseline; a newer command signals a re-read", () => {
  const first = syncStep(undefined, { enabled: true, latest: { id: "a" } });
  assert.deepEqual(first, { stop: false, changed: false, last: "a" });
  assert.equal(
    syncStep("a", { enabled: true, latest: { id: "a" } }).changed,
    false,
  );
  assert.equal(
    syncStep("a", { enabled: true, latest: { id: "b" } }).changed,
    true,
  );
  assert.equal(
    syncStep(null, { enabled: true, latest: { id: "b" } }).changed,
    true,
  );
  assert.equal(syncStep(null, { enabled: true, latest: null }).changed, false);
});
