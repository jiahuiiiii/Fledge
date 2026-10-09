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

test("company updates lead with their retained headline and own source excerpt", () => {
  const record = {
    kind: "company",
    title: "New adverse or mixed company reporting",
    detail: {
      payload: {
        items: [
          {
            source_id: "alert-source",
            explanation: "AI reading: a generic classification",
            citations: [
              { source_id: "alert-source", quote: "A production delay" },
              {
                source_id: "alert-source",
                quote: "The opening moved to September.",
              },
            ],
          },
        ],
      },
      sources: [
        { id: "unrelated", title: "Wrong headline", body: "Wrong body" },
        {
          id: "alert-source",
          title: "A production delay",
          body: "The opening moved to September. The plan is being revised.",
          kind: "news",
          source: "Saved publisher",
          published_at: "2026-05-01",
        },
      ],
    },
  };
  const summary = inboxSummary(record);
  assert.equal(summary.title, "A production delay");
  assert.equal(summary.text, "The opening moved to September.");
  assert.equal(summary.source, "Saved publisher");
  assert.equal(summary.alert, record.title);
  assert.doesNotMatch(JSON.stringify(summary), /Wrong|generic classification/);
});

test("company previews never borrow a parent or comparison-only source", () => {
  for (const comparison_only of [false, true]) {
    const record = {
      kind: "company",
      title: "A changed discussion",
      detail: {
        payload: {
          items: [
            {
              source_id: "comment",
              citations: [{ source_id: "parent", quote: "A parent claim" }],
            },
          ],
        },
        sources: [
          { id: "parent", title: "Parent headline", body: "A parent claim" },
          {
            id: "comment",
            kind: "social",
            title: "Hacker News comment",
            body: "The comment's own wording.",
            comparison_only,
          },
        ],
      },
    };
    const summary = inboxSummary(record);
    assert.doesNotMatch(
      JSON.stringify(summary),
      /Parent headline|A parent claim|Hacker News comment/,
    );
    if (!comparison_only)
      assert.equal(summary.text, "The comment's own wording.");
    else assert.doesNotMatch(summary.text, /own wording/);
  }
});
