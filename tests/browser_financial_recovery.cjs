// Authored recovery previews and AI responses; no provider or live-workspace writes.
const assert = require("node:assert/strict");
const path = require("node:path");

module.exports = async function checkFinancialRecovery(page, folder) {
  const docs = [
    {
      id: "report-a",
      form: "10-K",
      end: "2024-11-03",
      gaps: ["Borrowing (short- and long-term debt)", "Interest expense"],
    },
    {
      id: "report-b",
      form: "10-Q",
      end: "2025-02-02",
      gaps: ["Borrowing (short- and long-term debt)"],
    },
    {
      id: "report-c",
      form: "10-Q",
      end: "2025-05-04",
      gaps: ["Borrowing (short- and long-term debt)"],
    },
    {
      id: "report-d",
      form: "10-Q",
      end: "2025-08-03",
      gaps: ["Borrowing (short- and long-term debt)"],
    },
  ];
  let active = docs,
    saved = new Map(),
    calls = [],
    failId = null,
    previewFailure = false,
    release = null;
  let pauseNext = false,
    blockedId = "report-d";
  function preview(doc) {
    return {
      document: doc,
      documents: active.map((d) => ({ ...d, saved: saved.has(d.id) })),
      plan_id: `plan-${doc.id}`,
      has_gaps: true,
      missing: doc.gaps.map((label, i) => ({
        key: i ? "interest" : "debt",
        label,
      })),
      candidate_cells: 112,
      omitted_cells: 142,
      maximum_cost_usd:
        (docs.findIndex((item) => item.id === doc.id) + 1) / 100,
      can_run: !saved.has(doc.id) && doc.id !== blockedId,
      reading: saved.get(doc.id) || null,
      message:
        "No suitable dated statement cells were found for an AI reading.",
    };
  }
  function reading(doc) {
    return {
      id: `reading-${doc.id}`,
      document: { ...doc, url: "https://www.sec.gov/Archives/authored.htm" },
      accepted: [],
      review_id: null,
      result: {
        items: [
          {
            id: "debt",
            label: "Borrowing",
            value: "1000000000",
            start: null,
            end: doc.end,
            operation: "reported",
            explanation: "Authored reported borrowing.",
            inputs: [
              {
                id: "debt-row",
                label: "Total borrowing",
                value: "1000000000",
                text: "Total borrowing | 1,000",
              },
            ],
          },
        ],
        rejected: [],
        unresolved: [],
      },
    };
  }
  await page.route(
    "**/api/v1/companies/*/financial-recovery**",
    async (route) => {
      const req = route.request(),
        url = new URL(req.url());
      if (req.method() === "GET") {
        const id = url.searchParams.get("document_id");
        if (previewFailure && id)
          return route.fulfill({
            status: 503,
            json: {
              result: {
                errors: [{ error_message: "Authored preview unavailable." }],
              },
            },
          });
        return route.fulfill({
          json: {
            result: preview(active.find((d) => d.id === id) || active[0]),
          },
        });
      }
      const body = req.postDataJSON();
      if (url.pathname.endsWith("/review")) {
        const doc = active.find((d) =>
          url.pathname.includes(`reading-${d.id}`),
        );
        saved.set(doc.id, {
          ...saved.get(doc.id),
          accepted: body.accepted,
          review_id: "review-1",
        });
        return route.fulfill({ json: { result: saved.get(doc.id) } });
      }
      calls.push(body);
      if (pauseNext) {
        pauseNext = false;
        await new Promise((resolve) => {
          release = resolve;
        });
      }
      if (body.document_id === failId)
        return route.fulfill({
          status: 422,
          json: {
            result: {
              errors: [{ error_message: "Authored interrupted reading." }],
            },
          },
        });
      const doc = active.find((d) => d.id === body.document_id),
        result = reading(doc);
      saved.set(doc.id, result);
      return route.fulfill({ json: { result } });
    },
  );
  async function reload() {
    await page.reload();
    await page.getByRole("tab", { name: "Financials", exact: true }).click();
    await panel.getByRole("button", { name: /Fill missing figures/ }).waitFor();
  }
  const panel = page.getByRole("region", {
    name: "Missing financial figures",
    exact: true,
  });
  const toggle = panel.getByRole("button", { name: /Fill missing figures/ });
  const boxes = panel.locator(".recovery-checklist input");
  const fetch = panel.getByRole("button", { name: /Find figures with AI/ });
  const waitReady = () =>
    page.waitForFunction(() =>
      document.querySelector(".recovery-checklist input:not(:disabled)"),
    );
  await reload();
  assert.equal(await toggle.getAttribute("aria-expanded"), "false");
  await toggle.focus();
  await page.keyboard.press("Enter");
  await waitReady();
  assert.equal(await boxes.count(), 4);
  assert.equal(await boxes.nth(3).isDisabled(), true);
  assert.equal(await fetch.isDisabled(), true);
  assert.deepEqual(calls, []);
  assert.equal(
    await panel.locator(".recovery-checklist").getByText(/US\$/).count(),
    0,
  );
  assert.equal(
    await panel
      .getByText("Select a report to see the total cost.", { exact: true })
      .count(),
    0,
  );
  assert.equal(
    await toggle.evaluate((el) => getComputedStyle(el).justifyContent),
    "flex-start",
  );
  assert.equal(
    await toggle.evaluate((el) => getComputedStyle(el).textAlign),
    "left",
  );
  await boxes.nth(0).focus();
  await page.keyboard.press("Space");
  await boxes.nth(2).check();
  assert.match(await panel.innerText(), /At most US\$0.0400 in total/);
  await toggle.click();
  await toggle.click();
  await waitReady();
  assert.equal(await boxes.nth(0).isChecked(), true);
  assert.equal(await boxes.nth(2).isChecked(), true);
  await panel.getByRole("button", { name: "Select all", exact: true }).click();
  assert.equal(
    await panel.locator(".recovery-checklist input:checked").count(),
    3,
  );
  await panel
    .getByRole("button", { name: "Clear selection", exact: true })
    .click();
  assert.equal(await fetch.isDisabled(), true);
  await boxes.nth(0).check();
  await boxes.nth(2).check();
  for (const width of [1440, 390, 320]) {
    await page.setViewportSize({ width, height: 1000 });
    await panel.scrollIntoViewIfNeeded();
    assert.ok(
      await panel.evaluate((el) => el.scrollWidth <= el.clientWidth),
      `recovery overflow at ${width}`,
    );
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      `page overflow at ${width}`,
    );
    await panel.screenshot({
      path: path.join(folder, `recovery-checklist-${width}.png`),
    });
  }
  await page.setViewportSize({ width: 1440, height: 1100 });
  pauseNext = true;
  await fetch.click();
  await page.waitForFunction(() =>
    document
      .querySelector('.financial-recovery [role="status"]')
      ?.textContent.includes("Reading report 1 of 2"),
  );
  assert.equal(calls.length, 1);
  assert.equal(await boxes.nth(0).isDisabled(), true);
  assert.equal(
    await panel
      .getByRole("button", { name: "Select all", exact: true })
      .isDisabled(),
    true,
  );
  release();
  await panel
    .getByRole("heading", { name: "Suggested figures", exact: true })
    .waitFor();
  assert.deepEqual(calls, [
    { document_id: "report-a", plan_id: "plan-report-a" },
    { document_id: "report-c", plan_id: "plan-report-c" },
  ]);
  assert.equal(await panel.getByLabel("Use in my charts").isChecked(), false);
  await panel.getByLabel("Use in my charts").check();
  await panel
    .getByRole("button", { name: "Save my choices", exact: true })
    .click();
  await panel
    .getByRole("button", { name: "Choices saved", exact: true })
    .waitFor();
  assert.deepEqual(saved.get("report-a").accepted, ["debt"]);
  assert.equal(calls.length, 2);
  // Batch stops at the first failure; successful suggestions survive. No retry.
  saved = new Map();
  calls = [];
  failId = "report-b";
  blockedId = null;
  await reload();
  await toggle.click();
  await waitReady();
  await panel.getByRole("button", { name: "Select all", exact: true }).click();
  await fetch.click();
  await panel
    .getByRole("alert")
    .filter({ hasText: "1 of 4 reports were read" })
    .waitFor();
  assert.deepEqual(
    calls.map((c) => c.document_id),
    ["report-a", "report-b"],
  );
  await panel
    .getByRole("heading", { name: "Suggested figures", exact: true })
    .waitFor();
  // Preview failure can only reload free previews.
  saved = new Map();
  calls = [];
  failId = null;
  previewFailure = true;
  await reload();
  await toggle.click();
  await panel
    .getByRole("alert")
    .filter({ hasText: "Authored preview unavailable." })
    .waitFor();
  assert.equal(await fetch.isDisabled(), true);
  assert.deepEqual(calls, []);
  previewFailure = false;
  await panel
    .getByRole("button", { name: "Reload reports", exact: true })
    .click();
  await waitReady();
  // The same selection path also works with exactly one missing report.
  active = [docs[0]];
  await reload();
  await toggle.click();
  await waitReady();
  assert.equal(await boxes.count(), 1);
  await panel.getByRole("button", { name: "Select all", exact: true }).click();
  await fetch.click();
  await panel
    .getByRole("heading", { name: "Suggested figures", exact: true })
    .waitFor();
  assert.equal(calls.length, 1);
  assert.equal(await panel.locator(".recovery-checklist").count(), 0);
  // Identical gaps are stated once instead of repeated in every report row.
  saved = new Map();
  calls = [];
  active = docs.map((doc) => ({ ...doc, gaps: docs[0].gaps }));
  await reload();
  await toggle.click();
  await waitReady();
  assert.equal(
    await panel.locator(".recovery-common-gaps").textContent(),
    "Borrowing, Interest expense",
  );
  assert.equal(
    await panel.locator(".recovery-checklist-copy > span").count(),
    0,
  );
  assert.equal(
    await panel.locator(".recovery-checklist-copy > small").count(),
    0,
  );
  await panel.getByRole("button", { name: "Select all", exact: true }).click();
  assert.equal((await panel.innerText()).match(/US\$/g).length, 1);
  for (const width of [1440, 390, 320]) {
    await page.setViewportSize({ width, height: 1000 });
    assert.ok(await panel.evaluate((el) => el.scrollWidth <= el.clientWidth));
    await panel.screenshot({
      path: path.join(folder, `recovery-compact-${width}.png`),
    });
  }
  console.log(
    "Recovery checklist passed: keyboard collapse/selection, select all/clear, selected-only sequential calls/costs, blocked reports, saved review, failure stops, free preview reload, single report and 1440/390/320px; authored responses only.",
  );
};

if (require.main === module) {
  const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
  const fs = require("node:fs");
  let browser;
  (async () => {
    const folder =
      process.env.THESIS_FINANCIALS_SCREENSHOTS ||
      "/private/tmp/thesis-financial-recovery-screenshots";
    fs.mkdirSync(folder, { recursive: true });
    browser = await chromium.launch({
      headless: true,
      executablePath: process.env.CHROMIUM_PATH,
    });
    const page = await browser.newPage({
        viewport: { width: 1440, height: 1100 },
      }),
      errors = [],
      external = [],
      writes = [];
    page.on("pageerror", (e) => errors.push(e.message));
    const base = process.env.THESIS_TEST_URL;
    await page.route("**/*", (route) => {
      const request = route.request(),
        url = request.url();
      if (!url.startsWith(base)) {
        external.push(url);
        return route.abort();
      }
      if (url.endsWith("/loading"))
        return route.fulfill({ json: { result: null } });
      if (request.method() !== "GET") {
        writes.push(url);
        return route.abort();
      }
      return route.continue();
    });
    await page.route("**/api/v1/home", async (route) => {
      const response = await route.fetch(),
        payload = await response.json();
      payload.result.profile = { ...payload.result.profile, completed: true };
      payload.result.detail_mode = "data";
      return route.fulfill({ response, json: payload });
    });
    await page.goto(base + "/?view=workspace");
    await page.locator(".watch-item").filter({ hasText: "MSFT" }).click();
    await page.getByRole("tab", { name: "Financials", exact: true }).click();
    try {
      await module.exports(page, folder);
    } catch (error) {
      await page.screenshot({ path: path.join(folder, "failure.png") });
      throw error;
    }
    assert.deepEqual(errors, []);
    assert.deepEqual(writes, []);
    assert.ok(
      external.every((url) =>
        url.startsWith("https://financialmodelingprep.com/image-stock/"),
      ),
    );
    await browser.close();
  })().catch(async (error) => {
    console.error(error);
    if (browser) await browser.close();
    process.exit(1);
  });
}
