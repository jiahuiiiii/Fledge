import test from "node:test";
import assert from "node:assert/strict";
import { orderStarters } from "./profile.js";

const items = [{ id: "business" }, { id: "growth" }, { id: "risks" }, { id: "outlook" }];

test("starter questions follow the user's goal", () => {
  assert.deepEqual(
    orderStarters(items, ["risks", "outlook", "growth", "business"]).map((i) => i.id),
    ["risks", "outlook", "growth", "business"],
  );
});

test("without answers the original order is kept", () => {
  assert.deepEqual(orderStarters(items, undefined), items);
  assert.deepEqual(orderStarters(items, ["risks"]).map((i) => i.id), ["risks", "business", "growth", "outlook"]);
});
