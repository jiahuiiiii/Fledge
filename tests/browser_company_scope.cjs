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
  await page.route("**/*", (route) => {
    const request = route.request(),
      url = new URL(request.url());
    if (
      !["127.0.0.1", "localhost"].includes(url.hostname) ||
      request.method() !== "GET"
    ) {
      writes.push(url.pathname);
      return route.abort();
    }
    return route.continue();
  });
  const base = process.env.THESIS_TEST_URL || "http://127.0.0.1:8841";
  const apple = "4780d271-7c4a-5c18-80f8-74e164c21675",
    google = "528be36b-8e44-57e9-a9fa-fbd2ee8bbdd1";
  const nav = page.getByRole("navigation", { name: "Workspace navigation" });
  const side = page.getByRole("complementary", {
    name: "Companies",
    exact: true,
  });
  const pick = (symbol) =>
    side
      .locator(".company-row .watch-item")
      .filter({ hasText: symbol })
      .click();
  const tab = (name) => nav.getByRole("button", { name, exact: true }).click();
  const scope = async (id, view) => {
    await page.waitForFunction(
      ({ id, view }) => {
        const p = new URLSearchParams(location.search);
        return (p.get("company") || "") === id && p.get("view") === view;
      },
      { id, view },
    );
    if (id)
      await page
        .locator(".company-header .ticker")
        .filter({ hasText: id === apple ? "AAPL" : "GOOGL" })
        .waitFor({ state: "attached" });
    else
      await page
        .locator(".all-companies-view .company-row")
        .first()
        .waitFor({ state: "attached" });
    await page.waitForFunction(
      () =>
        document.querySelector(".main-workspace")?.getAttribute("aria-busy") ===
        "false",
    );
  };
  await page.goto(base + "/?view=workspace");
  await page
    .getByRole("region", { name: "All company workspaces", exact: true })
    .waitFor();
  assert.equal(
    await side
      .getByRole("button", { name: "All companies", exact: true })
      .getAttribute("aria-pressed"),
    "true",
  );
  await tab("My ideas");
  await scope("", "ideas");
  assert.ok((await page.locator(".idea-summary").count()) > 1);
  await pick("AAPL");
  await scope(apple, "ideas");
  assert.equal(await page.locator(".idea-summary").count(), 1);
  assert.match(await page.locator(".idea-summary").innerText(), /Apple/);
  await tab("History");
  await scope(apple, "history");
  await page
    .getByRole("heading", { name: "Research history", exact: true })
    .waitFor();
  await pick("GOOGL");
  await scope(google, "history");
  await page
    .getByRole("heading", { name: "Research history", exact: true })
    .waitFor();
  assert.equal(await page.locator(".all-history").count(), 0);
  await tab("Updates");
  await scope(google, "updates");
  assert.equal(
    await page.getByLabel("Inbox company", { exact: true }).inputValue(),
    google,
  );
  await page.getByLabel("Show updates").selectOption("all");
  await page.getByLabel("Inbox company", { exact: true }).click();
  await page.getByRole("listbox").locator(`[data-value="${apple}"]`).click();
  await scope(apple, "updates");
  assert.equal(await page.getByLabel("Show updates").inputValue(), "all");
  await tab("Workspace");
  await scope(apple, "workspace");
  await page.locator(".company-header").waitFor();
  await tab("My ideas");
  await scope(apple, "ideas");
  assert.equal(await page.locator(".idea-summary").count(), 1);
  await side
    .getByRole("button", { name: "All companies", exact: true })
    .click();
  await scope("", "ideas");
  assert.ok((await page.locator(".idea-summary").count()) > 1);
  await tab("History");
  await scope("", "history");
  const history = page.getByRole("region", {
    name: "All company history",
    exact: true,
  });
  await history.locator(".idea-summary").first().waitFor();
  assert.ok(
    (await history
      .locator(".idea-summary")
      .evaluateAll(
        (nodes) => new Set(nodes.map((n) => n.dataset.company)).size,
      )) > 1,
  );
  await history
    .locator('.idea-summary[data-company="' + google + '"]')
    .first()
    .click();
  await scope(google, "history");
  assert.ok(new URL(page.url()).searchParams.get("evaluation"));
  await page.getByLabel("Record", { exact: true }).waitFor();
  await side
    .getByRole("button", { name: "All companies", exact: true })
    .click();
  await tab("Updates");
  await scope("", "updates");
  assert.equal(
    await page.getByLabel("Inbox company", { exact: true }).inputValue(),
    "",
  );
  await page.reload();
  await page.getByLabel("Inbox company", { exact: true }).waitFor();
  assert.equal(
    await page.getByLabel("Inbox company", { exact: true }).inputValue(),
    "",
  );
  await tab("History");
  await history.locator(".idea-summary").first().waitFor();
  await page.setViewportSize({ width: 390, height: 900 });
  const company = page.getByLabel("Company", { exact: true });
  await company.click();
  await page.getByRole("listbox").locator(`[data-value="${apple}"]`).click();
  await scope(apple, "history");
  assert.equal(await company.inputValue(), apple);
  await tab("My ideas");
  await scope(apple, "ideas");
  assert.equal(await page.locator(".idea-summary").count(), 1);
  await company.click();
  await page.getByRole("listbox").locator('[data-value=""]').click();
  await scope("", "ideas");
  assert.ok((await page.locator(".idea-summary").count()) > 1);
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );
  await page.screenshot({
    path: "/private/tmp/thesis-company-scope-phone.png",
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await tab("History");
  await history.locator(".idea-summary").first().waitFor();
  await page.screenshot({
    path: "/private/tmp/thesis-company-history-all.png",
  });
  // Partial history failures stay explicit while other company records remain usable.
  const historyRoute =
    "**/api/v1/workspace?instrument_id=c767e09f-35ea-5eaf-a626-ff5d3aa4709b";
  await page.route(historyRoute, (route) =>
    route.fulfill({
      status: 503,
      json: {
        result: { errors: [{ error_message: "Authored history outage" }] },
      },
    }),
  );
  await history
    .getByRole("button", { name: "Refresh history", exact: true })
    .click();
  await history.getByRole("alert").filter({ hasText: "MSFT" }).waitFor();
  assert.ok(
    await history
      .locator('.idea-summary[data-company="' + google + '"]')
      .count(),
  );
  await page.unroute(historyRoute);
  await history
    .getByRole("button", { name: "Refresh history", exact: true })
    .click();
  await history
    .locator(
      '.idea-summary[data-company="c767e09f-35ea-5eaf-a626-ff5d3aa4709b"]',
    )
    .first()
    .waitFor();
  assert.equal(await history.getByRole("alert").count(), 0);
  assert.deepEqual(errors, []);
  assert.deepEqual(writes, []);
  console.log(
    "Shared company scope passed: same-tab sidebar selection, AAPL/GOOGL across four tabs, dropdown/URL synchronization, review-status preservation, all/empty selection, all-history exact links, reload and phone switching; read-only.",
  );
})()
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  })
  .finally(async () => {
    await browser?.close();
  });
