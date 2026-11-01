import test from "node:test";
import assert from "node:assert/strict";
import { setupProgress } from "./setupProgress.js";

const step = (key, status) => ({ key, status, label: key });

test("opening until the company and its run are read", () => {
  assert.deepEqual(setupProgress(null, false), {
    stage: "opening",
    stages: [],
  });
  assert.deepEqual(setupProgress({ active: true, steps: [] }, true), {
    stage: "opening",
    stages: [],
  });
});

test("groups sources into three stages, without the optional AI rating", () => {
  const run = {
    active: true,
    steps: [
      step("market", "ready"),
      step("prices", "ready"),
      step("filings", "failed"),
      step("disclosures", "ready"),
      step("reddit", "running"),
      step("hackernews", "queued"),
      step("analysis", "queued"),
    ],
  };
  assert.deepEqual(setupProgress(run, false), {
    stage: "collecting",
    stages: [
      {
        id: "basics",
        label: "Price and company details",
        done: 2,
        total: 2,
        state: "done",
      },
      {
        id: "filings",
        label: "Filings and financials",
        done: 2,
        total: 2,
        state: "done",
      },
      {
        id: "news",
        label: "News and discussions",
        done: 0,
        total: 2,
        state: "working",
      },
    ],
  });
});

test("a stage nobody has started waits; unknown steps count as details", () => {
  const run = {
    active: true,
    steps: [step("market", "running"), step("new_source", "queued"), step("x", "queued")],
  };
  const { stages } = setupProgress(run, false);
  assert.deepEqual(
    stages.map((s) => [s.id, s.state, s.total]),
    [
      ["basics", "working", 2],
      ["news", "waiting", 1],
    ],
  );
});

test("ready when the run ends or every stage has finished", () => {
  const steps = [step("market", "ready"), step("analysis", "running")];
  assert.equal(setupProgress({ active: true, steps }, false).stage, "ready");
  const ended = setupProgress(
    { active: false, steps: [step("market", "queued")] },
    false,
  );
  assert.equal(ended.stage, "ready");
  assert.equal(ended.stages[0].state, "done");
});
