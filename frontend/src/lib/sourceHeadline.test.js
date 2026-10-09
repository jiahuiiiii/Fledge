import test from "node:test";
import assert from "node:assert/strict";
import { sourceHeadline } from "./sourceHeadline.js";

test("social type placeholders do not become story headlines", () => {
  for (const title of [
    "Hacker News comment",
    "Reddit comment",
    "Reddit post",
    "X post",
    "  HACKER NEWS COMMENT ",
  ])
    assert.equal(sourceHeadline({ kind: "social", title }), null);
});
test("real titles remain exact and news titles are not inferred to be placeholders", () => {
  for (const [kind, title] of [
    ["social", " Is demand growing? "],
    ["news", "Hacker News comment"],
  ])
    assert.equal(sourceHeadline({ kind, title }), title);
});
test("missing or empty source titles remain missing", () => {
  for (const source of [null, {}, { title: "  " }, { title: 12 }])
    assert.equal(sourceHeadline(source), null);
});
