import test from "node:test";
import assert from "node:assert/strict";
import { inboxSummary, recordKey } from "./inbox.js";

test("withdrawn evidence cannot enter an inbox preview through old generated fields", () => {
  for (const kind of ["idea", "company", "condition"]) {
    const record = {
      kind,
      title: "Retained sensitive interpretation",
      detail: {
        withheld: true,
        question: "Question",
        payload: { reason: "Retained sensitive interpretation" },
        items: [
          {
            relation: "risk",
            explanation: "Retained sensitive interpretation",
          },
        ],
      },
    };
    assert.doesNotMatch(
      JSON.stringify(inboxSummary(record)),
      /Retained sensitive/,
    );
  }
});
test("a question answer is not presented as support for an investment stance", () => {
  const record = {
    kind: "idea",
    detail: {
      question: "When will the product launch?",
      items: [
        { relation: "context", explanation: "Background only" },
        {
          relation: "answers",
          explanation: "The report gives a planned date.",
        },
      ],
    },
  };
  assert.equal(inboxSummary(record).title, "Evidence toward your question");
  assert.equal(inboxSummary(record).text, "The report gives a planned date.");
});
test("records from different streams keep separate identity and review state", () => {
  assert.notEqual(
    recordKey({ kind: "idea", id: "same-id" }),
    recordKey({ kind: "company", id: "same-id" }),
  );
});
