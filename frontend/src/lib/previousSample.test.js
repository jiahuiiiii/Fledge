import test from "node:test";
import assert from "node:assert/strict";
import { loadPreviousSample, savedPreviousSample } from "./previousSample.js";

test("an alert that already carries its earlier sample needs no request", () => {
  const items = [{ source_id: "s1" }];
  assert.deepEqual(savedPreviousSample({ previous_items: items, previous_sources: [{ id: "s1" }] }), {
    withheld: false,
    items,
    sources: [{ id: "s1" }],
  });
  assert.equal(savedPreviousSample({ previous_items: null }), null);
  assert.equal(savedPreviousSample({}), null);
});

test("the earlier sample loads for one alert and keeps withheld evidence hidden", async () => {
  const calls = [];
  const client = {
    alertPreviousSample: async (id) => {
      calls.push(id);
      return id === "hidden"
        ? { withheld: true, previous_items: [], previous_sources: [] }
        : { withheld: false, previous_items: [{ source_id: "s1" }], previous_sources: [{ id: "s1" }] };
    },
  };
  assert.deepEqual(await loadPreviousSample(client, "a1"), {
    withheld: false,
    items: [{ source_id: "s1" }],
    sources: [{ id: "s1" }],
  });
  assert.deepEqual(await loadPreviousSample(client, "hidden"), { withheld: true, items: [], sources: [] });
  assert.deepEqual(calls, ["a1", "hidden"]);
});
