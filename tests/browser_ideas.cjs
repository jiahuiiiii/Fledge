const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");
let browser;
(async () => {
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_PATH,
  });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1050 },
    reducedMotion: "reduce",
  });
  const base = process.env.THESIS_TEST_URL,
    errors = [],
    writes = [],
    external = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.route("**/*", (route) => {
    const request = route.request(),
      url = new URL(request.url());
    if (
      url.hostname === "financialmodelingprep.com" &&
      url.pathname.startsWith("/image-stock/")
    )
      return route.fulfill({ status: 404, body: "Authored missing logo" });
    if (!url.href.startsWith(base)) {
      external.push(url.href);
      return route.abort();
    }
    if (url.pathname.endsWith("/loading"))
      return route.fulfill({ json: { result: { active: false, steps: [] } } });
    if (request.method() !== "GET") {
      writes.push(url.pathname);
      return route.abort();
    }
    return route.continue();
  });
  await page.route("**/api/v1/workspace*", async (route) => {
    const response = await route.fetch(),
      body = await response.json();
    body.result.catalogue = body.result.catalogue.map((c) =>
      c.symbol === "NSTR"
        ? {
            ...c,
            name: "Northstar Data and Enterprise Infrastructure Holdings Incorporated",
          }
        : c,
    );
    await route.fulfill({ response, json: body });
  });
  await page.goto(base + "/?view=ideas");
  const ideas = page.getByRole("region", { name: "Saved ideas", exact: true });
  await ideas.locator(".idea-summary").first().waitFor();
  await page.evaluate(() => document.fonts.ready);
  const data = (
    await (await page.request.get(base + "/api/v1/workspace")).json()
  ).result;
  const saved = data.catalogue
    .filter((c) => c.status)
    .sort((a, b) => b.unread - a.unread);
  assert.ok(saved.length >= 2);
  assert.deepEqual(
    await ideas.locator(".saved-idea-company > span").allTextContents(),
    saved.map((c) => c.symbol),
  );
  assert.deepEqual(
    await ideas.locator(".saved-idea-status").allTextContents(),
    saved.map((c) => c.status),
  );
  for (const c of saved) {
    const card = ideas.locator(".idea-summary").filter({ hasText: c.symbol });
    assert.equal(await card.locator("h3").innerText(), c.question);
    assert.equal(
      await card.locator(".saved-idea-reasoning").textContent(),
      c.reasoning || "Draft with no reasoning yet.",
    );
    assert.match(
      await card.locator(".saved-idea-meta").innerText(),
      new RegExp(`Revision ${c.revision}`),
    );
    assert.equal(
      await card.locator(".saved-idea-updates").innerText(),
      c.unread
        ? `${c.unread} update${c.unread === 1 ? "" : "s"} awaiting review`
        : "No unreviewed updates",
    );
  }
  const screenshot = async (name) => {
    if (process.env.THESIS_IDEAS_SCREENSHOTS)
      await page.screenshot({
        path: `${process.env.THESIS_IDEAS_SCREENSHOTS}/${name}.png`,
        animations: "disabled",
      });
  };
  for (const width of [1440, 980, 390, 320]) {
    await page.setViewportSize({ width, height: 1050 });
    await ideas.scrollIntoViewIfNeeded();
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      `saved ideas overflow ${width}`,
    );
    assert.equal(
      await ideas
        .locator(".saved-idea-company strong")
        .first()
        .evaluate((el) => getComputedStyle(el).textOverflow),
      "ellipsis",
    );
    assert.equal(
      await ideas
        .locator(".idea-summary")
        .first()
        .evaluate((el) => getComputedStyle(el).transitionDuration),
      "0s",
    );
    assert.equal(await page.locator(".periodic-review-entry").count(), 0);
    await screenshot(`saved-${width}`);
  }
  // The original focus page/editor remains the saved-card destination.
  await page.setViewportSize({ width: 1440, height: 1050 });
  const card = ideas.locator(".idea-summary").filter({ hasText: "MSFT" });
  await card.focus();
  await page.keyboard.press("Enter");
  await page
    .getByRole("button", { name: "Edit my idea", exact: true })
    .waitFor();
  assert.equal(new URL(page.url()).searchParams.get("view"), "idea");
  await page.getByRole("button", { name: "Edit my idea", exact: true }).click();
  const edit = page.getByRole("dialog", {
    name: "Edit your idea",
    exact: true,
  });
  await edit.waitFor();
  assert.equal(
    await edit
      .getByRole("textbox", { name: "Research question", exact: true })
      .inputValue(),
    saved.find((c) => c.symbol === "MSFT").question,
  );
  await page.keyboard.press("Escape");
  await edit.waitFor({ state: "hidden" });
  const nav = page.getByRole("navigation", {
    name: "Workspace navigation",
    exact: true,
  });
  await nav.getByRole("button", { name: "My ideas", exact: true }).click();
  assert.equal(await ideas.locator(".idea-summary").count(), 1);
  const empty = data.catalogue.find((c) => c.symbol === "AURQ");
  assert.ok(empty && !empty.status);
  await page.goto(base + `/?company=${empty.id}&view=ideas`);
  await ideas
    .getByRole("heading", { name: "Save your view on AURQ", exact: true })
    .waitFor();
  assert.equal(await ideas.locator(".idea-summary").count(), 0);
  assert.match(
    await ideas.locator(".ideas-scope").innerText(),
    /0 saved ideas/,
  );
  for (const width of [1440, 980, 390, 320]) {
    await page.setViewportSize({ width, height: 1050 });
    await page.evaluate(() => {
      document.querySelector(".main-workspace").scrollTop = 0;
      window.scrollTo(0, 0);
    });
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      `empty ideas overflow ${width}`,
    );
    assert.ok(
      await ideas
        .getByRole("button", { name: "Save my reasoning", exact: true })
        .evaluate((el) => el.getBoundingClientRect().height >= 44),
    );
    assert.equal(await page.locator(".periodic-review-entry").count(), 0);
    await screenshot(`empty-${width}`);
  }
  await ideas
    .getByRole("button", { name: "Save my reasoning", exact: true })
    .focus();
  await page.keyboard.press("Enter");
  const create = page.getByRole("dialog", {
    name: "Save your reasoning",
    exact: true,
  });
  await create.waitFor();
  await create
    .getByRole("textbox", { name: "My reasoning", exact: true })
    .fill("An unsaved test thought.");
  await page.keyboard.press("Escape");
  await create.waitFor({ state: "hidden" });
  assert.equal(
    await ideas
      .getByRole("button", { name: "Save my reasoning", exact: true })
      .evaluate((el) => el === document.activeElement),
    true,
  );
  assert.equal(
    (
      await (
        await page.request.get(
          base + `/api/v1/workspace?instrument_id=${empty.id}`,
        )
      ).json()
    ).result.versions.length,
    0,
  );
  await ideas
    .getByRole("button", { name: "Read company research", exact: true })
    .click();
  assert.equal(new URL(page.url()).searchParams.get("view"), "workspace");
  assert.equal(new URL(page.url()).searchParams.get("company"), empty.id);
  // Authored all-company empty state must lead to the existing company browser.
  await page.route("**/api/v1/workspace*", async (route) => {
    const response = await route.fetch(),
      body = await response.json();
    body.result.catalogue = body.result.catalogue.map((c) => ({
      ...c,
      status: null,
      unread: 0,
    }));
    await route.fulfill({ response, json: body });
  });
  await page.goto(base + "/?view=ideas");
  await ideas
    .getByRole("heading", {
      name: "What do you think about the companies you follow?",
      exact: true,
    })
    .waitFor();
  await screenshot("all-empty-320");
  await ideas
    .getByRole("button", { name: "Choose a company", exact: true })
    .click();
  await page
    .getByRole("region", { name: "All company workspaces", exact: true })
    .waitFor();
  await page.locator('.company-overview-grid[aria-busy="false"]').waitFor();
  assert.equal(new URL(page.url()).searchParams.get("view"), "workspace");
  assert.ok(!new URL(page.url()).searchParams.get("company"));
  assert.deepEqual(writes, []);
  assert.deepEqual(errors, []);
  assert.deepEqual(external, []);
  const report = {
    viewports: [1440, 980, 390, 320],
    savedIdeaCount: saved.length,
    emptyCompany: "AURQ",
    cardKeyboardNavigation: true,
    originalEditors: true,
    cancelWithoutSave: true,
    focusRestored: true,
    noDuplicateWeeklyBanner: true,
    allCompanyBrowser: true,
    writes,
    errors,
    external,
  };
  if (process.env.THESIS_IDEAS_SCREENSHOTS)
    fs.writeFileSync(
      `${process.env.THESIS_IDEAS_SCREENSHOTS}/browser.json`,
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
