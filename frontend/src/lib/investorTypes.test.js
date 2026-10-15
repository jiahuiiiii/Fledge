import test from "node:test";
import assert from "node:assert/strict";
import { INVESTOR_TYPES, typeName } from "./investorTypes.js";
import { TERMS_VERSION } from "./terms.js";

test("every server investor type has plain-language copy", () => {
  for (const key of ["starting_out", "long_term", "steady_builder", "swing_trader", "active_trader"]) {
    const info = INVESTOR_TYPES[key];
    for (const field of ["name", "short", "about", "watch", "fledge"])
      assert.ok(info[field], `${key}.${field}`);
    assert.doesNotMatch(Object.values(info).join(" "), /\byou should (buy|sell)\b/i);
  }
  assert.equal(typeName("swing_trader"), "Swing trader");
  assert.equal(typeName("unknown"), "");
});

test("terms version matches the server format", () => {
  assert.match(TERMS_VERSION, /^\d{4}-\d{2}-\d{2}$/);
});
