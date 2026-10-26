import test from "node:test";
import assert from "node:assert/strict";
import { uniqueCitations } from "./briefCitations.js";

const docs = [
  { id: "a", url: "https://x.test/1", title: "One" },
  { id: "b", url: "https://x.test/1", title: "One (copy)" },
  { id: "c", url: "https://x.test/2", title: "Two" },
  { id: "d", title: "Same Title" },
  { id: "e", title: "same  title" },
];

test("the same article cited twice, or saved twice, shows once", () => {
  const out = uniqueCitations(
    [{ source_id: "a", quote: "q1" }, { source_id: "a", quote: "q2" }, { source_id: "b", quote: "q3" }, { source_id: "c", quote: "q4" }],
    docs,
  );
  assert.deepEqual(out.map((c) => c.source_id), ["a", "c"]);
});

test("without a link, identical titles are the same article", () => {
  assert.equal(uniqueCitations([{ source_id: "d" }, { source_id: "e" }], docs).length, 1);
});
