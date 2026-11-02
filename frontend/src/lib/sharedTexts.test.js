import { test } from "node:test";
import assert from "node:assert/strict";
import { expandSharedTexts } from "./sharedTexts.js";

test("puts shared texts back in every source list", () => {
  const result = {
    documents: [
      { id: "a", body_ref: "r1" },
      { id: "b", body: "own text" },
    ],
    sentiment: { sources: [{ id: "a", body_ref: "r1" }] },
    sentiment_inputs: {
      sources: [
        { id: "a", body_ref: "r1" },
        { id: "p", body_ref: "r2" },
      ],
    },
    source_texts: { r1: "Long article text", r2: "Long post text" },
  };
  const out = expandSharedTexts(result);
  assert.equal(out.documents[0].body, "Long article text");
  assert.equal(out.documents[1].body, "own text");
  assert.equal(out.sentiment.sources[0].body, "Long article text");
  assert.equal(out.sentiment_inputs.sources[1].body, "Long post text");
  assert.equal("source_texts" in out, false);
  assert.equal("body_ref" in out.documents[0], false);
});

test("leaves answers without shared texts untouched", () => {
  const result = { documents: [{ id: "a", body: "x" }], unchanged: false };
  assert.equal(expandSharedTexts(result), result);
  assert.deepEqual(result, {
    documents: [{ id: "a", body: "x" }],
    unchanged: false,
  });
  assert.equal(expandSharedTexts(null), null);
  assert.deepEqual(expandSharedTexts({ unchanged: true, revision: "r" }), {
    unchanged: true,
    revision: "r",
  });
});

test("a missing text never invents one", () => {
  const out = expandSharedTexts({
    sentiment: { sources: [{ id: "a", body_ref: "gone" }], withheld: false },
    source_texts: {},
  });
  assert.equal(out.sentiment.sources[0].body, undefined);
  assert.equal("body_ref" in out.sentiment.sources[0], false);
});
