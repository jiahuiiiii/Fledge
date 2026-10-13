import test from "node:test";
import assert from "node:assert/strict";
import { needsListingUpdate } from "./companyDirectory.js";

const now = Date.parse("2026-10-12T08:00:00Z");

test("listings refresh when missing or older than a day", () => {
  assert.equal(needsListingUpdate(null, now), false);
  assert.equal(needsListingUpdate({ retrieved_at: null }, now), true);
  assert.equal(
    needsListingUpdate({ retrieved_at: "2026-10-05T02:20:40Z" }, now),
    true,
  );
  assert.equal(
    needsListingUpdate({ retrieved_at: "2026-10-11T07:59:00Z" }, now),
    true,
  );
  assert.equal(
    needsListingUpdate({ retrieved_at: "2026-10-11T08:01:00+00:00" }, now),
    false,
  );
  assert.equal(needsListingUpdate({ retrieved_at: "not a date" }, now), true);
});
