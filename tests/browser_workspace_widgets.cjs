// Arrangeable home page: reading mode is static; Arrange allows keyboard
// moves, dragging, width changes, hiding and reset; the arrangement survives a
// reload; phones get a single stacked column. Disposable fictional database.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const assert = require("node:assert/strict");
let browser;
(async () => {
  browser = await chromium.launch({ headless: true, ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}) });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, reducedMotion: "reduce" });
  const errors = [], external = [], saves = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.route("**/*", (route) => {
    const request = route.request(), url = request.url();
    if (url.startsWith(process.env.THESIS_TEST_URL)) {
      if (url.endsWith("/loading")) return route.fulfill({ json: { result: null } });
      // Only layout saves may write; everything else stays read-only.
      if (request.method() !== "GET" && !new URL(url).pathname.startsWith("/api/v1/layouts/"))
        return route.fulfill({ status: 403, json: { result: { error: "blocked" } } });
      if (request.method() !== "GET") saves.push(request.method());
      return route.continue();
    }
    if (url.startsWith("https://financialmodelingprep.com/image-stock/")) return route.fulfill({ status: 404, body: "" });
    external.push(url);
    return route.abort();
  });
  const board = page.locator('.ws-board[data-page="home"]');
  const order = () => board.evaluate((el) =>
    [...el.querySelectorAll("[data-widget]")]
      .map((w) => [w.dataset.widget, w.getBoundingClientRect()])
      .sort((a, b) => a[1].top - b[1].top || a[1].left - b[1].left)
      .map(([id]) => id));
  const settle = () => page.waitForTimeout(800);
  const open = async () => {
    await page.goto(process.env.THESIS_TEST_URL);
    const skip = page.getByRole("button", { name: /Skip, show me the app/ });
    if (await skip.waitFor({ timeout: 3000 }).then(() => true, () => false)) await skip.click();
    await board.waitFor();
    await board.locator(".ws-grid").waitFor();
  };

  await open();
  assert.deepEqual(await order(), ["welcome", "portfolio", "companies"]);
  // Reading mode: no bars, nothing draggable.
  assert.equal(await board.locator(".ws-bar").count(), 0);
  assert.equal(await board.locator(".react-draggable").count(), 0);

  await board.getByRole("button", { name: "Arrange" }).click();
  assert.equal(await board.locator(".ws-bar").count(), 3);
  // Optional widgets start in the add list, not on the page.
  const add = board.getByRole("group", { name: "Sections you can add" });
  for (const name of ["Today’s alerts", "Updates to review", "World headlines"])
    await add.getByRole("button", { name }).waitFor();
  // Keyboard: move the welcome block later and keep focus on the control.
  const later = board.getByRole("button", { name: "Move later: Welcome" });
  await later.focus();
  await page.keyboard.press("Enter");
  await settle();
  assert.deepEqual(await order(), ["portfolio", "welcome", "companies"]);
  assert.equal(await page.evaluate(() => document.activeElement?.dataset.action), "later");

  // Width: the keyboard narrows; dragging the right edge widens again.
  const companies = board.locator('[data-widget="companies"]');
  const full = (await companies.boundingBox()).width;
  await board.getByRole("button", { name: "Make narrower: Your companies" }).click();
  await settle();
  assert.ok((await companies.boundingBox()).width < full - 20);
  const handle = board.locator(".ws-item").filter({ has: companies }).locator(".react-resizable-handle-e");
  const edge = await handle.boundingBox();
  await page.mouse.move(edge.x + edge.width / 2, edge.y + edge.height / 2);
  await page.mouse.down();
  await page.mouse.move(edge.x + 400, edge.y + edge.height / 2, { steps: 10 });
  await page.mouse.up();
  await settle();
  assert.ok((await companies.boundingBox()).width > full - 20);

  // Drag the companies block to the top by its bar.
  const bar = await companies.locator(".ws-bar").boundingBox();
  const top = await board.locator(".ws-grid").boundingBox();
  await page.mouse.move(bar.x + 60, bar.y + bar.height / 2);
  await page.mouse.down();
  await page.mouse.move(bar.x + 60, top.y + 4, { steps: 20 });
  await page.mouse.up();
  await settle();
  assert.equal((await order())[0], "companies");

  // Hide and add back.
  await board.getByRole("button", { name: "Hide Your list today" }).click();
  assert.equal(await board.locator('[data-widget="portfolio"]').count(), 0);
  await board.getByRole("group", { name: "Sections you can add" }).getByRole("button", { name: "Your list today" }).click();
  assert.equal(await board.locator('[data-widget="portfolio"]').count(), 1);
  await board.getByRole("button", { name: "Done" }).click();
  await settle();
  const arranged = await order();
  assert.ok(saves.includes("PUT"), "the arrangement was saved");

  // Survives a reload.
  await open();
  assert.deepEqual(await order(), arranged);

  // Reset restores the defaults, saved too.
  await board.getByRole("button", { name: "Arrange" }).click();
  await board.getByRole("button", { name: "Reset to default" }).click();
  await settle();
  assert.deepEqual(await order(), ["welcome", "portfolio", "companies"]);
  assert.ok(saves.includes("DELETE"));
  await board.getByRole("button", { name: "Done" }).click();

  // Phones: one stacked column, no grid, no sideways scroll.
  await page.setViewportSize({ width: 320, height: 800 });
  await board.locator(".ws-stack").waitFor();
  assert.equal(await board.locator(".ws-grid").count(), 0);
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= 320));

  assert.deepEqual(errors, []);
  assert.deepEqual(external, []);
  console.log("Workspace widgets journey passed.");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
}).finally(() => browser?.close());
