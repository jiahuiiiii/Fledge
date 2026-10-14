import test from "node:test";
import assert from "node:assert/strict";
import {
  plainTone,
  toneMood,
  priceLine,
  socialTones,
  worldForCompany,
} from "./beginnerSummary.js";

test("rewords saved tones in plain language", () => {
  assert.equal(plainTone("positive leaning"), "Mostly positive");
  assert.equal(plainTone("thin sample"), "Not enough to tell yet");
  assert.equal(plainTone(null), "Not checked yet");
  assert.equal(toneMood("negative leaning"), "bad");
  assert.equal(toneMood("mixed / balanced"), "mixed");
});

test("describes the price move without explaining it", () => {
  assert.deepEqual(priceLine({ price: 231.5, change_percent: -1.234 }), {
    price: "$231.50",
    move: "down 1.2% in the last session",
    mood: "bad",
  });
  assert.equal(priceLine(null), null);
  assert.equal(priceLine({ price: 10, change_percent: 0.01 }).move, "flat in the last session");
});

test("lists social tone per platform that has a reading", () => {
  const scopes = [
    { scope: "news", analysed: 5, tone: "mixed" },
    { scope: "reddit", analysed: 8, tone: "positive leaning" },
    { scope: "hackernews", analysed: 0, tone: null },
  ];
  assert.deepEqual(socialTones(scopes), [{ platform: "Reddit", tone: "positive leaning" }]);
});

test("picks world headlines linked to the company, else the big picture", () => {
  const page = {
    articles: [
      { id: "1", themes: ["rates"], mentions: [], links: [{ company_id: "aapl", effect: "could_help" }] },
      { id: "2", themes: ["geopolitics"], mentions: [], links: [] },
      { id: "3", themes: [], mentions: ["aapl"], links: [] },
    ],
  };
  const mine = worldForCompany(page, "aapl");
  assert.deepEqual(mine.linked.map((x) => x.article.id), ["1", "3"]);
  assert.equal(mine.bigPicture.length, 0);
  const other = worldForCompany(page, "msft");
  assert.deepEqual(other.linked, []);
  assert.deepEqual(other.bigPicture.map((a) => a.id), ["1", "2"]);
});
