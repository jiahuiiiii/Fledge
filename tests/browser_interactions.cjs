// Read-only installed-app interaction checks; sidebar preferences are isolated to this browser context.
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
    writes = [],
    external = [];
  let workspaceReads = 0;
  page.on("pageerror", (e) => errors.push(e.message));
  await page.route("**/*", (r) => {
    const u = new URL(r.request().url());
    if (!["127.0.0.1", "localhost"].includes(u.hostname)) {
      external.push(u.href);
      return r.abort();
    }
    if (r.request().method() !== "GET") {
      writes.push(u.pathname);
      return r.abort();
    }
    if (u.pathname === "/api/v1/workspace") workspaceReads++;
    return r.continue();
  });
  const base = process.env.THESIS_TEST_URL || "http://127.0.0.1:8841",
    iid = "528be36b-8e44-57e9-a9fa-fbd2ee8bbdd1";
  await page.goto(base + "/?company=" + iid + "&view=workspace");
  await page.locator(".company-header").waitFor();
  await page.evaluate(() => {
    window.savedHeader = document.querySelector(".topbar");
    window.savedGrid = document.querySelector(".workspace-grid");
  });
  const initialReads = workspaceReads;
  const nav = page.getByRole("navigation", { name: "Workspace navigation" });
  let release;
  const held = new Promise((resolve) => (release = resolve));
  await page.route("**/api/v1/research-review?**", async (r) => {
    await held;
    await r.continue();
  });
  await nav.getByRole("button", { name: "Updates", exact: true }).click();
  await page.locator(".update-inbox .loading-skeleton").waitFor();
  assert.ok(
    await page.evaluate(
      () =>
        window.savedHeader === document.querySelector(".topbar") &&
        window.savedGrid === document.querySelector(".workspace-grid"),
    ),
  );
  await page.screenshot({ path: "/private/tmp/thesis-tab-skeleton.png" });
  await nav.getByRole("button", { name: "History", exact: true }).click();
  release();
  await page.unroute("**/api/v1/research-review?**");
  await page
    .getByRole("heading", { name: "Research history", exact: true })
    .waitFor();
  const filter = page.getByLabel("Show", { exact: true });
  await filter.click();
  const menu = page.getByRole("listbox");
  await menu.waitFor();
  assert.equal(await filter.getAttribute("aria-expanded"), "true");
  assert.equal(
    await filter.evaluate((e) => getComputedStyle(e).outlineStyle),
    "none",
  );
  await page.screenshot({ path: "/private/tmp/thesis-custom-dropdown.png" });
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Enter");
  assert.equal(await filter.inputValue(), "unreviewed");
  await menu.waitFor({ state: "hidden" });
  await filter.click();
  await page.keyboard.press("End");
  await page.keyboard.press("Escape");
  assert.equal(await filter.inputValue(), "unreviewed");
  await filter.focus();
  await page.keyboard.type("All");
  await page.keyboard.press("Enter");
  assert.equal(await filter.inputValue(), "all");
  await filter.click();
  await page.mouse.click(400, 180);
  await menu.waitFor({ state: "hidden" });
  for (const name of [
    "My ideas",
    "Workspace",
    "History",
    "Updates",
    "Workspace",
  ]) {
    await nav.getByRole("button", { name, exact: true }).click();
    assert.ok(
      await page.evaluate(
        () =>
          window.savedHeader === document.querySelector(".topbar") &&
          window.savedGrid === document.querySelector(".workspace-grid"),
      ),
      `shell remounted for ${name}`,
    );
  }
  assert.equal(
    workspaceReads,
    initialReads,
    "tab navigation refetches the whole workspace",
  );
  // Removal is reversible sidebar visibility; no API write or research deletion.
  const company = () => page.locator(".watch-item").filter({ hasText: "MSFT" });
  await page
    .getByRole("button", { name: "Remove MSFT from sidebar", exact: true })
    .click();
  assert.equal(await company().count(), 0);
  await page.getByRole("button", { name: "Undo", exact: true }).click();
  assert.equal(await company().count(), 1);
  await page
    .getByRole("button", { name: "Remove MSFT from sidebar", exact: true })
    .click();
  await page.reload();
  await page.locator(".company-header").waitFor();
  assert.equal(await company().count(), 0);
  await page
    .getByRole("button", { name: "+ Add company", exact: true })
    .click();
  const dialog = page.getByRole("dialog");
  await dialog.waitFor();
  await dialog.locator("summary").filter({hasText:"Manage sidebar"}).click();
  await dialog
    .getByRole("button", { name: "Restore MSFT", exact: true })
    .click();
  assert.equal(await company().count(), 1);
  const search = dialog.getByLabel("Find a company", { exact: true });
  await search.fill("NVDA");
  await dialog.getByRole("button", {name: /(?:Open|Add) NVDA/}).waitFor();
  assert.equal(await dialog.isVisible(), true);
  await page.keyboard.press("Escape");
  await dialog.waitFor({ state: "hidden" });
  // Empty sidebars can be restored, including through the phone management dialog.
  const removals = page.getByRole("button", {
    name: /^Remove .+ from sidebar$/,
  });
  while (await removals.count()) await removals.first().click();
  await page
    .getByText("Your sidebar is empty. Add or restore a company below.", {
      exact: true,
    })
    .waitFor();
  await page.setViewportSize({ width: 390, height: 900 });
  await page.getByRole("button", { name: "Add company", exact: true }).click();
  await dialog.waitFor();
  await dialog.locator("summary").filter({hasText:"Manage sidebar"}).click();
  await dialog
    .getByRole("button", { name: "Restore GOOGL", exact: true })
    .click();
  await page.keyboard.press("Escape");
  assert.equal(
    await page.getByLabel("Company", { exact: true }).inputValue(),
    iid,
  );
  await page.getByRole("button", { name: "History", exact: true }).click();
  await filter.click();
  await menu.waitFor();
  const box = await menu.boundingBox();
  assert.ok(
    box.x >= 0 &&
      box.x + box.width <= 390 &&
      box.y >= 0 &&
      box.y + box.height <= 900,
  );
  await page.screenshot({
    path: "/private/tmp/thesis-custom-dropdown-phone.png",
  });
  await page.keyboard.press("Tab");
  await menu.waitFor({ state: "hidden" });
  assert.deepEqual(errors, []);
  assert.deepEqual(writes, []);
  assert.deepEqual(external, []);
  console.log(
    "Interactions passed: custom mouse/keyboard/typeahead/Escape/Tab menus, modal popup, subtle focus, stable tab DOM, delayed inbox skeleton, no navigation workspace refetch, remove/undo/reload/restore/empty sidebar, phone menu bounds; no API writes.",
  );
})()
  .catch((e) => {
    console.error(e);
    process.exitCode = 1;
  })
  .finally(async () => {
    await browser?.close();
  });
