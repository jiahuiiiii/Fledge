import test from "node:test";
import assert from "node:assert/strict";
import { comparisonMeaning } from "./conditionRoles.js";

test("risk and requirement previews retain operator, threshold and equality", () => {
  for (const role of ["risk", "required"])
    for (const operator of ["<=", ">="]) {
      const text = comparisonMeaning({ role, operator, threshold: "15" });
      assert.match(
        text,
        role === "risk" ? /^Flags a risk/ : /^The reported figure must/,
      );
      assert.ok(
        text.includes(operator === "<=" ? "at most 15%" : "at least 15%"),
      );
      assert.match(text, /including equality/);
    }
  assert.match(
    comparisonMeaning({ role: "risk", operator: "<=", threshold: null }),
    /chosen threshold/,
  );
  assert.doesNotMatch(
    comparisonMeaning({ role: "risk", operator: "<=", threshold: null }),
    /null%/,
  );
  assert.match(
    comparisonMeaning({ operator: ">=", threshold: "0" }),
    /^The reported figure must be at least 0%/,
  );
});
