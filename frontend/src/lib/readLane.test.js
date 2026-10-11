import test from "node:test";
import assert from "node:assert/strict";
import { createReadLane } from "./readLane.js";

test("overlapping polls share one read, then a later poll reads again", async () => {
  const lane = createReadLane();
  let finish,
    calls = 0;
  const read = () => {
    calls++;
    return new Promise((resolve) => {
      finish = resolve;
    });
  };
  const first = lane.read("A", read),
    duplicate = lane.read("A", read);
  await Promise.resolve();
  assert.equal(first, duplicate);
  assert.equal(calls, 1);
  finish("saved A");
  assert.equal(await duplicate, "saved A");
  assert.equal(await lane.read("A", () => "new A"), "new A");
});

test("switching cancels old work without clearing the new company read", async () => {
  const lane = createReadLane();
  let firstSignal, finishFirst, finishNext;
  const first = lane.read("A", (signal) => {
    firstSignal = signal;
    return new Promise((resolve) => {
      finishFirst = resolve;
    });
  });
  await Promise.resolve();
  const next = lane.read(
    "B",
    () =>
      new Promise((resolve) => {
        finishNext = resolve;
      }),
  );
  await Promise.resolve();
  assert.equal(firstSignal.aborted, true);
  finishFirst("late A");
  await first;
  assert.equal(
    lane.read("B", () => assert.fail("duplicate B")),
    next,
  );
  finishNext("B");
  assert.equal(await next, "B");
});

test("unmount and mutation invalidation cancel pending work; failures can retry", async () => {
  const lane = createReadLane();
  const abandoned = lane.read("A", () =>
    assert.fail("unmounted request started"),
  );
  lane.cancel();
  await assert.rejects(abandoned, { name: "AbortError" });
  await assert.rejects(
    lane.read("B", () => {
      throw new Error("unavailable");
    }),
    /unavailable/,
  );
  assert.equal(await lane.read("B", () => "recovered"), "recovered");
});
