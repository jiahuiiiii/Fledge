const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const assert = require("node:assert/strict");
let browser;
(async () => {
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_PATH,
  });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
    reducedMotion: "reduce",
  });
  const errors = [],
    writes = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route("**/*", (r) => {
    const u = new URL(r.request().url());
    if (
      !["127.0.0.1", "localhost"].includes(u.hostname) ||
      r.request().method() !== "GET"
    ) {
      writes.push(u.pathname);
      return r.abort();
    }
    return r.continue();
  });
  const base = process.env.THESIS_TEST_URL || "http://127.0.0.1:8841";
  const apple = "4780d271-7c4a-5c18-80f8-74e164c21675",
    google = "528be36b-8e44-57e9-a9fa-fbd2ee8bbdd1",
    microsoft = "c767e09f-35ea-5eaF-a626-ff5d3aa4709b".toLowerCase();
  const nav = page.getByRole("navigation", { name: "Workspace navigation" }),
    main = page.locator(".main-workspace");
  const pick = (symbol) =>
    page
      .locator(".company-row .watch-item")
      .filter({ hasText: symbol })
      .click();
  const ready = () =>
    page.waitForFunction(
      () =>
        document.querySelector(".main-workspace")?.getAttribute("aria-busy") ===
        "false",
    );
  const sameShell = async () =>
    assert.ok(
      await page.evaluate(
        () =>
          window.shell.header === document.querySelector(".topbar") &&
          window.shell.side === document.querySelector(".watchlist") &&
          window.shell.grid === document.querySelector(".workspace-grid"),
      ),
      "shell was remounted",
    );
  await page.goto(base + "/?company=" + apple + "&view=workspace");
  await ready();
  await page.locator(".historical-prices .price-panel").waitFor();
  await page.evaluate(
    () =>
      (window.shell = {
        header: document.querySelector(".topbar"),
        side: document.querySelector(".watchlist"),
        grid: document.querySelector(".workspace-grid"),
      }),
  );
  let release;
  const held = new Promise((resolve) => (release = resolve));
  const route = "**/api/v1/workspace?instrument_id=" + google;
  await page.route(route, async (r) => {
    await held;
    await r.continue();
  });
  await pick("GOOGL");
  await main.locator(":scope > .skeleton-workspace").waitFor();
  await sameShell();
  assert.equal(await page.locator(".watchlist .loading-skeleton").count(), 0);
  assert.equal(await page.locator(".idea-panel .skeleton-idea").count(), 1);
  assert.equal(
    await page.locator(".market-quote").count(),
    0,
    "old quote remains under new company",
  );
  assert.equal(
    await page.locator(".idea-panel button").count(),
    0,
    "old idea remains actionable",
  );
  assert.equal(await page.locator(".quick-save").isEnabled(), false);
  assert.equal(await main.getAttribute("aria-busy"), "true");
  await page.screenshot({
    path: "/private/tmp/thesis-stock-switch-skeleton.png",
  });
  // A late GOOGL response must not replace AAPL after another click.
  await pick("AAPL");
  await ready();
  release();
  await page.unroute(route);
  await page.waitForTimeout(250);
  assert.equal(
    await main.locator(".company-header .ticker").innerText(),
    "AAPL",
  );
  await sameShell();
  // The company and its chart are revealed together, with no second skeleton.
  let releaseChart;
  const chartHeld = new Promise((resolve) => (releaseChart = resolve));
  const chartRoute = "**/api/v1/companies/" + google + "/price-history";
  await page.route(chartRoute, async (r) => {
    await chartHeld;
    await r.continue();
  });
  await pick("GOOGL");
  await main.locator(":scope > .skeleton-workspace").waitFor();
  await page.waitForTimeout(350);
  assert.equal(await main.getAttribute("aria-busy"), "true");
  assert.ok((await main.locator(".skeleton-plot").boundingBox()).height >= 190);
  await sameShell();
  await page.screenshot({ path: "/private/tmp/thesis-chart-skeleton.png" });
  releaseChart();
  await page.unroute(chartRoute);
  await ready();
  const chart = page.locator(".historical-prices");
  await chart.locator(".price-panel").waitFor();
  assert.equal(await chart.locator(".skeleton-chart").count(), 0);
  // Returning to Workspace retains the actual chart and its user-selected range.
  await chart.getByRole("button", { name: "6M", exact: true }).click();
  await page.evaluate(
    () =>
      (window.retainedChart = document.querySelector(
        ".historical-prices .price-chart",
      )),
  );
  const geometry = () =>
    page.evaluate(() => {
      const selectors = [
        ".topbar",
        ".demo-bar",
        ".watchlist",
        ".main-workspace",
        ".idea-panel",
      ];
      return selectors.map((selector) => {
        const r = document.querySelector(selector).getBoundingClientRect();
        return [r.x, r.y, r.width, r.height];
      });
    });
  const frame = await geometry();
  for (const name of ["My ideas", "Updates", "History", "Workspace"]) {
    await nav.getByRole("button", { name, exact: true }).click();
    assert.deepEqual(
      await geometry(),
      frame,
      `shell geometry changed in ${name}`,
    );
    if (name === "Updates") {
      await main
        .locator(".update-inbox .loading-skeleton")
        .waitFor({ state: "hidden" });
      await page.evaluate(
        () => (window.retainedInbox = document.querySelector(".update-inbox")),
      );
    }
  }
  assert.ok(
    await page.evaluate(
      () =>
        window.retainedChart ===
        document.querySelector(".historical-prices .price-chart"),
    ),
  );
  assert.equal(
    await chart
      .getByRole("button", { name: "6M", exact: true })
      .getAttribute("aria-pressed"),
    "true",
  );
  assert.equal(await main.locator(".loading-skeleton:visible").count(), 0);
  await nav.getByRole("button", { name: "Updates", exact: true }).click();
  assert.ok(
    await page.evaluate(
      () => window.retainedInbox === document.querySelector(".update-inbox"),
    ),
  );
  assert.equal(await main.locator(".loading-skeleton:visible").count(), 0);
  await nav.getByRole("button", { name: "Workspace", exact: true }).click();
  // Delayed research subsection changes have their own loading surface.
  for (const [tabName, endpoint, regionName] of [
    ["Expectations", "expectations", "Company expectations"],
    ["Valuation", "valuation", "Valuation scenarios"],
  ]) {
    let releasePanel;
    const panelHeld = new Promise((resolve) => (releasePanel = resolve));
    const panelRoute = "**/api/v1/companies/" + google + "/" + endpoint;
    await page.route(panelRoute, async (r) => {
      await panelHeld;
      await r.continue();
    });
    await page.getByRole("tab", { name: tabName, exact: true }).click();
    const panel = page.getByRole("region", { name: regionName, exact: true });
    await panel.locator(".skeleton-panel").waitFor();
    await sameShell();
    releasePanel();
    await page.unroute(panelRoute);
    await panel.locator(".loading-skeleton").waitFor({ state: "hidden" });
  }
  // A failed selected-company load has a retry state, never another company's data.
  const failureRoute = "**/api/v1/workspace?instrument_id=" + microsoft;
  await page.route(failureRoute, (r) =>
    r.fulfill({
      status: 503,
      json: {
        result: {
          errors: [{ error_message: "Authored company loading outage" }],
        },
      },
    }),
  );
  await pick("MSFT");
  await main
    .getByRole("heading", { name: "Research could not be loaded", exact: true })
    .waitFor();
  await sameShell();
  assert.equal(await page.locator(".market-quote").count(), 0);
  assert.equal(await main.getAttribute("aria-busy"), "false");
  await page.unroute(failureRoute);
  await main.getByRole("button", { name: "Try again", exact: true }).click();
  await ready();
  await page.locator(".market-quote").waitFor();
  assert.equal(
    await main.locator(".company-header .ticker").innerText(),
    "MSFT",
  );
  for (const name of ["My ideas", "Updates", "History", "Workspace"]) {
    await nav.getByRole("button", { name, exact: true }).click();
    await sameShell();
  }
  // A locally intercepted save may finish after changing stocks. It must not
  // close the new company's editor, show its notice or overwrite its draft.
  // This response is authored in the browser; no write reaches the server.
  let releaseSave, saveStarted;
  const saveHeld = new Promise((resolve) => (releaseSave = resolve));
  const saveSeen = new Promise((resolve) => (saveStarted = resolve));
  // Company buttons are intentionally disabled while saving. Browser Back can
  // still change scope, so create a same-document history entry for that path.
  await page.evaluate(
    ({ apple, microsoft }) => {
      history.replaceState(null, "", `?company=${apple}&view=workspace`);
      history.pushState(null, "", `?company=${microsoft}&view=workspace`);
    },
    { apple, microsoft },
  );
  await page.route("**/api/v1/idea", async (r) => {
    assert.equal(r.request().postDataJSON().instrument_id, microsoft);
    saveStarted();
    await saveHeld;
    await r.fulfill({ status: 200, json: { result: {} } });
  });
  await page.locator(".idea-panel button.full").click();
  await page
    .getByLabel("My reasoning", { exact: true })
    .fill("Authored delayed save control.");
  await page.getByRole("button", { name: "Save draft", exact: true }).click();
  await saveSeen;
  await page.keyboard.press("Escape");
  await page.goBack();
  await ready();
  await page.locator(".idea-panel button.full").click();
  const draft = page.getByLabel("My reasoning", { exact: true });
  await draft.fill("Separate unsaved Apple reasoning.");
  const saveFinished = page.waitForResponse((r) =>
    r.url().endsWith("/api/v1/idea"),
  );
  releaseSave();
  await saveFinished;
  await page.waitForTimeout(250);
  assert.equal(await draft.inputValue(), "Separate unsaved Apple reasoning.");
  assert.equal(await page.getByRole("dialog").isVisible(), true);
  assert.equal(
    await page
      .locator(".global-message")
      .filter({ hasText: "Draft saved" })
      .count(),
    0,
  );
  await sameShell();
  await page.keyboard.press("Escape");
  await page.unroute("**/api/v1/idea");
  // The same selective loading behavior holds on phones.
  await page.setViewportSize({ width: 390, height: 900 });
  let releasePhone;
  const phoneHeld = new Promise((resolve) => (releasePhone = resolve));
  await page.route(route, async (r) => {
    await phoneHeld;
    await r.continue();
  });
  await page.getByLabel("Company", { exact: true }).selectOption(google);
  await main.locator(":scope > .skeleton-workspace").waitFor();
  await sameShell();
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );
  await page.screenshot({ path: "/private/tmp/thesis-stock-switch-phone.png" });
  releasePhone();
  await page.unroute(route);
  await ready();
  // A chart read error does not hold the entire workspace in a skeleton.
  const brokenChart = "**/api/v1/companies/" + microsoft + "/price-history";
  await page.route(brokenChart, (r) =>
    r.fulfill({
      status: 503,
      json: {
        result: { errors: [{ error_message: "Authored chart read outage" }] },
      },
    }),
  );
  await page.getByLabel("Company", { exact: true }).selectOption(microsoft);
  await ready();
  await page
    .locator(".historical-prices")
    .getByText("Authored chart read outage", { exact: true })
    .waitFor();
  assert.equal(await main.locator(".loading-skeleton:visible").count(), 0);
  assert.equal(
    await main.locator(".historical-prices .price-chart").count(),
    0,
  );
  await page.unroute(brokenChart);
  assert.deepEqual(errors, []);
  assert.deepEqual(writes, []);
  console.log(
    "Stable transitions passed: one stock-loading phase, retained chart/range and inbox, unchanged shell geometry across all tabs, local research skeletons, late workspace/save isolation, failed workspace/chart handling, phone layout and no server writes (one locally simulated save).",
  );
})()
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  })
  .finally(async () => {
    await browser?.close();
  });
