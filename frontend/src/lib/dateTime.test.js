import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { formatTimestamp, formatReportingAgeExplanation } from "./dateTime.js";
import { day } from "./companySnapshot.js";

test("Singapore timestamps roll over dates and years in 24-hour time", () => {
  assert.equal(
    formatTimestamp("2026-10-11T23:50:00Z"),
    "12 Oct 2026, 07:50 SGT",
  );
  assert.equal(
    formatTimestamp("2026-10-11T16:00:00Z"),
    "12 Oct 2026, 00:00 SGT",
  );
  assert.equal(
    formatTimestamp("2026-12-31T16:00:01Z", { seconds: true }),
    "1 Jan 2027, 00:00:01 SGT",
  );
  assert.equal(
    formatTimestamp("2026-10-12T12:00:00Z"),
    "12 Oct 2026, 20:00 SGT",
  );
  assert.equal(
    formatTimestamp("2026-09-03T04:26:00+08:00"),
    "3 Sept 2026, 04:26 SGT",
  );
});

test("equivalent offsets and Date objects display the same instant without mutation", () => {
  const value = "2026-10-11T23:50:32.123Z";
  const date = new Date(value);
  for (const input of [
    value,
    date,
    "2026-10-12T07:50:32.123+08:00",
    "2026-10-11T19:50:32.123-0400",
  ])
    assert.equal(
      formatTimestamp(input, { seconds: true }),
      "12 Oct 2026, 07:50:32 SGT",
    );
  assert.equal(date.toISOString(), value);
});

test("calendar dates, ambiguous times and missing/invalid inputs never acquire a clock", () => {
  for (const value of [
    null,
    undefined,
    "",
    "2026-10-12",
    "2026-10-12T07:50:00",
    "invalid",
    new Date(NaN),
  ])
    assert.equal(
      formatTimestamp(value, { fallback: "Not supplied" }),
      "Not supplied",
    );
  assert.equal(formatTimestamp(null, { fallback: null }), null);
  assert.equal(day("2026-10-11"), "11 Oct 2026");
});

test("host locale/time zone cannot change Singapore timestamps or reporting dates", () => {
  const url = new URL("./dateTime.js", import.meta.url).href;
  const dayUrl = new URL("./companySnapshot.js", import.meta.url).href;
  const code = `import {formatTimestamp} from ${JSON.stringify(url)}; import {day} from ${JSON.stringify(dayUrl)}; console.log(formatTimestamp('2026-10-11T16:00:00Z')); console.log(day('2026-10-11'));`;
  for (const TZ of ["UTC", "America/New_York", "Asia/Tokyo"])
    assert.equal(
      execFileSync(process.execPath, ["--input-type=module", "-e", code], {
        env: { ...process.env, TZ, LANG: "en_US.UTF-8" },
        encoding: "utf8",
      }),
      "12 Oct 2026, 00:00 SGT\n11 Oct 2026\n",
    );
});

test("saved age-limit wording uses its exact expiry without rewriting unknown text", () => {
  const age = {
    period_end: "2026-10-01",
    max_report_age_days: 10,
    expires_at: "2026-10-12T00:00:00+00:00",
  };
  const text =
    "Too old to assess: the period ended 2026-10-01. Your 10-day limit expired at 2026-10-12T00:00:00+00:00. The last figure and source are retained.";
  assert.equal(
    formatReportingAgeExplanation(text, age),
    text.replace(age.expires_at, "12 Oct 2026, 08:00 SGT"),
  );
  assert.equal(formatReportingAgeExplanation(text, null), text);
  assert.equal(
    formatReportingAgeExplanation("Original quote at " + age.expires_at, age),
    "Original quote at " + age.expires_at,
  );
  assert.equal(age.expires_at, "2026-10-12T00:00:00+00:00");
});
