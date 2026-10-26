import test from "node:test";
import assert from "node:assert/strict";
import { alertEvidenceRows } from "./alertEvidence.js";

const source = { id: "s1", title: "Big news", source: "Wire", url: "https://x.test/a", published_at: "2026-10-01T00:00:00Z", body: "Body text" };

test("company update lists its saved sources once, with the cited quote", () => {
  const rows = alertEvidenceRows({
    kind: "company",
    detail: { sources: [source], payload: { items: [{ source_id: "s1", citations: [{ source_id: "s1", quote: "Quoted" }] }, { source_id: "s1" }] } },
  });
  assert.equal(rows.length, 1);
  assert.equal(rows[0].quote, "Quoted");
  assert.equal(rows[0].url, "https://x.test/a");
});

test("withheld updates show no evidence rows", () => {
  assert.deepEqual(alertEvidenceRows({ kind: "company", detail: { withheld: true, sources: [source], payload: { items: [{ source_id: "s1" }] } } }), []);
});

test("a source with no link keeps url null so the caller can fall back", () => {
  const rows = alertEvidenceRows({ kind: "move", detail: { sources: [{ ...source, url: undefined }] } });
  assert.equal(rows[0].url, null);
});
