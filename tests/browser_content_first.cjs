// Header geometry, on-demand operations and explicit fiscal comparison labels.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright"),
  assert = require("node:assert/strict"),
  fs = require("node:fs");
let browser;
(async () => {
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_PATH,
  });
  const page = await browser.newPage({
    viewport: { width: 375, height: 812 },
    reducedMotion: "reduce",
  });
  const base = process.env.THESIS_TEST_URL,
    iid = "c767e09f-35ea-5eaf-a626-ff5d3aa4709b",
    errors = [],
    writes = [],
    external = [],
    positions = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.route("**/*", (route) => {
    const r = route.request(),
      u = new URL(r.url());
    if (
      u.hostname === "financialmodelingprep.com" &&
      r.resourceType() === "image"
    )
      return route.fulfill({ status: 404, body: "Authored unavailable logo" });
    if (!r.url().startsWith(base)) {
      external.push(r.url());
      return route.abort();
    }
    if (u.pathname.endsWith("/loading"))
      return route.fulfill({
        json: {
          result: {
            active: false,
            steps: [
              {
                key: "sources",
                label: "Saved sources",
                status: "ready",
                message: "Authored saved sources checked.",
              },
            ],
          },
        },
      });
    if (r.method() !== "GET") {
      writes.push(u.pathname);
      return route.abort();
    }
    return route.continue();
  });
  await page.route("**/api/v1/model-status", (route) =>
    route.fulfill({
      json: {
        result: {
          enabled: true,
          briefing_enabled: true,
          comparison_enabled: true,
          budget: {
            remaining_usd: 4,
            running: 0,
            unresolved: 1,
            needs_attention: 1,
          },
        },
      },
    }),
  );
  await page.addInitScript(() =>
    localStorage.setItem(
      "thesis.layout",
      JSON.stringify({
        companiesHidden: true,
        ideaHidden: true,
        progressHidden: true,
      }),
    ),
  );
  await page.goto(base + `/?company=${iid}&view=workspace`);
  const overview = page.getByRole("heading", { name: "Overview", exact: true });
  await overview.waitFor();
  const nav = page.getByRole("navigation", { name: "Workspace navigation" });
  const source = await (
    await page.request.get(base + `/api/v1/companies/${iid}/financial-story`)
  ).json();
  const period = (id, start, end, revenue) => ({
    ...structuredClone(source.result.annual.at(-1)),
    id,
    start,
    end,
    metrics: source.result.annual.at(-1).metrics.map((row) => ({
      ...row,
      start,
      end,
      value: row.key === "revenue" ? revenue : row.value,
    })),
  });
  const authored = {
    ...source.result,
    annual: [
      period("annual-before", "2023-10-01", "2024-09-30", "52000000000"),
      period("annual-now", "2024-10-01", "2025-09-30", "64000000000"),
    ],
    trailing: [
      period("trailing-before", "2024-07-01", "2025-06-30", "50000000000"),
      period("trailing-now", "2025-07-01", "2026-06-30", "80000000000"),
    ],
  };
  await page.route("**/api/v1/companies/*/financial-story", (route) =>
    route.fulfill({ json: { result: authored } }),
  );
  for (const [width, height] of [
    [375, 812],
    [320, 740],
    [390, 844],
    [980, 1000],
    [1440, 1050],
  ]) {
    await page.setViewportSize({ width, height });
    await page.evaluate(() => scrollTo(0, 0));
    await page.evaluate(() => document.fonts.ready);
    await page.evaluate(
      () =>
        new Promise((r) =>
          requestAnimationFrame(() => requestAnimationFrame(r)),
        ),
    );
    const y = (await overview.boundingBox()).y;
    positions.push({ width, height, overviewTop: y });
    if (width < 600)
      assert.ok(y < 390, `Overview starts too low: ${width} ${y}`);
    assert.equal(await page.locator(".demo-bar,.ai-activity").count(), 0);
    assert.equal(
      await page
        .getByRole("region", { name: "Research loading progress", exact: true })
        .count(),
      0,
    );
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      `overflow ${width}`,
    );
    for (const name of ["Notebook", "Data & sources", "Research updates"])
      assert.ok(
        await page
          .getByRole("button", { name, exact: true })
          .evaluate((el) => el.getBoundingClientRect().height >= 44),
        name,
      );
    if (process.env.THESIS_CONTENT_FIRST_EVIDENCE)
      await page.screenshot({
        path: `${process.env.THESIS_CONTENT_FIRST_EVIDENCE}/overview-${width}.png`,
        animations: "disabled",
      });
  }
  await page.setViewportSize({ width: 375, height: 812 });
  const tools = page.getByRole("button", {
    name: "Research updates",
    exact: true,
  });
  await tools.focus();
  await page.keyboard.press("Enter");
  const dialog = page.getByRole("dialog", {
    name: "Research updates",
    exact: true,
  });
  await dialog.waitFor();
  assert.match(await dialog.innerText(), /10-K|filed/);
  assert.equal(
    await dialog
      .getByRole("button", { name: "Refresh research", exact: true })
      .isEnabled(),
    true,
  );
  console.log(
    "Research dialog buttons",
    await dialog.locator("button").allTextContents(),
  );
  await dialog.locator(".progress-restore").click();
  await dialog
    .getByRole("region", { name: "Research loading progress", exact: true })
    .waitFor();
  await dialog
    .getByRole("button", { name: "View progress", exact: true })
    .click();
  assert.match(await dialog.innerText(), /Authored saved sources checked/);
  await dialog.getByText("AI request details", { exact: true }).click();
  assert.match(await dialog.innerText(), /without a confirmed charge/);
  await page.keyboard.press("Escape");
  assert.equal(
    await tools.evaluate((el) => el === document.activeElement),
    true,
  );
  assert.doesNotMatch(
    await page.locator("body").innerText(),
    /without a confirmed charge/,
  );
  await page
    .getByRole("tab", { name: "News & discussion", exact: true })
    .click();
  const news = page.getByRole("region", {
    name: "News and social sentiment",
    exact: true,
  });
  await news.waitFor();
  assert.equal(
    await news
      .getByRole("button", { name: "Refresh & analyse", exact: true })
      .isDisabled(),
    true,
  );
  assert.match(await news.innerText(), /New AI analysis is paused/);
  assert.doesNotMatch(
    await news.innerText(),
    /confirmed charge|no automatic confirmation/,
  );
  await page.getByRole("tab", { name: "Overview", exact: true }).click();
  const growth = page.locator(".glance-growth");
  assert.match(await growth.innerText(), /23.1% · last fiscal year/);
  assert.match(
    await growth.innerText(),
    /Year ended 30 Sept? 2025 vs year ended 30 Sept? 2024/,
  );
  await page.getByRole("tab", { name: "Financials", exact: true }).click();
  const history = page.getByRole("region", {
    name: "Earnings and cash-flow history",
    exact: true,
  });
  const sales = history
    .locator(".financial-insight")
    .filter({ hasText: "Sales grew" });
  await sales.waitFor();
  assert.match(
    await sales.innerText(),
    /Trailing 12 months[\s\S]*60.0% higher[\s\S]*1 Jul 2025 – 30 Jun 2026 vs 1 Jul 2024 – 30 Jun 2025/,
  );
  await history
    .getByRole("button", { name: "Annual reports", exact: true })
    .click();
  assert.match(
    await sales.innerText(),
    /Fiscal year[\s\S]*23.1% higher[\s\S]*1 Oct 2024 – 30 Sept? 2025 vs 1 Oct 2023 – 30 Sept? 2024/,
  );
  await history
    .getByRole("button", { name: "Figures & calculations", exact: true })
    .click();
  await page
    .getByRole("dialog", {
      name: "Performance · figures & calculations",
      exact: true,
    })
    .waitFor();
  assert.match(
    await page
      .getByRole("dialog", {
        name: "Performance · figures & calculations",
        exact: true,
      })
      .innerText(),
    /64000000000 USD/,
  );
  await page.keyboard.press("Escape");
  for (const name of ["My ideas", "Updates", "History"]) {
    await nav.getByRole("button", { name, exact: true }).click();
    assert.equal(await page.locator(".demo-bar,.ai-activity").count(), 0);
    assert.doesNotMatch(
      await page.locator("body").innerText(),
      /confirmed charge/,
    );
  }
  assert.deepEqual(errors, []);
  assert.deepEqual(writes, []);
  assert.deepEqual(external, []);
  const report = {
    authoredData: true,
    positions,
    noPersistentStatusStrips: true,
    onDemandRefreshProgressAndBillingDetail: true,
    chargeBlockStillEnforced: true,
    keyboardFocus: true,
    annualTrailingPeriodDates: true,
    unchangedEvidence: true,
    allViewsNoBillingBanner: true,
    errors,
    writes,
    external,
  };
  if (process.env.THESIS_CONTENT_FIRST_EVIDENCE)
    fs.writeFileSync(
      process.env.THESIS_CONTENT_FIRST_EVIDENCE + "/browser.json",
      JSON.stringify(report, null, 2),
    );
  console.log(JSON.stringify(report));
})()
  .catch((e) => {
    console.error(e);
    process.exitCode = 1;
  })
  .finally(async () => {
    await browser?.close();
  });
