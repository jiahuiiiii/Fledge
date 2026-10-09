// Presentation checks over the owner's saved research. All writes, loading and external requests are blocked.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const base = process.env.THESIS_TEST_URL || "http://127.0.0.1:8841";
const evidence =
  process.env.THESIS_DESIGN_EVIDENCE || "/private/tmp/thesis-design";
const before = process.env.THESIS_DESIGN_STAGE === "before";
let browser;
(async () => {
  fs.mkdirSync(evidence, { recursive: true });
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
    external = [],
    layouts = [];
  page.on("pageerror", (e) => {
    errors.push(e.message);
    console.error(e.message);
  });
  await page.route("**/*", async (route) => {
    const request = route.request(),
      url = new URL(request.url());
    if (
      url.hostname === "financialmodelingprep.com" &&
      request.resourceType() === "image"
    )
      return route.fulfill({ status: 404, body: "" });
    if (!["127.0.0.1", "localhost"].includes(url.hostname)) {
      external.push(url.hostname);
      return route.abort();
    }
    if (/\/companies\/[^/]+\/loading$/.test(url.pathname))
      return route.fulfill({ json: { result: { active: false, steps: [] } } });
    if (request.method() !== "GET") {
      writes.push(url.pathname);
      return route.abort();
    }
    return route.continue();
  });
  await page.goto(base + "/?view=workspace");
  await page
    .locator(".company-row .watch-item")
    .filter({
      has: page.locator(
        `strong[title="${process.env.THESIS_DESIGN_SYMBOL || "AVGO"}"]`,
      ),
    })
    .click();
  await page.locator('.main-workspace[aria-busy="false"]').waitFor();
  const main = page.locator(".main-workspace"),
    tabs = page.getByRole("tablist", { name: "Research views" });
  await tabs.waitFor();
  const labels = await tabs.getByRole("tab").allTextContents();
  const savedTitle = await page.locator(".company-header h1").textContent();
  const collapseProgress = page.getByRole("button", {
    name: "Hide research progress",
    exact: true,
  });
  if (await collapseProgress.count()) await collapseProgress.click();
  await page.screenshot({
    path: path.join(
      evidence,
      `${before ? "before" : "after"}-workspace-1440.png`,
    ),
  });
  await tabs.scrollIntoViewIfNeeded();
  await page.screenshot({
    path: path.join(
      evidence,
      `${before ? "before" : "after"}-research-1440.png`,
    ),
  });
  if (before) {
    await browser.close();
    browser = null;
    return;
  }
  assert.deepEqual(labels, [
    "Overview",
    "Financials",
    "News & discussion",
    "Outlook",
    "Compare & value",
  ]);
  assert.equal(
    await tabs
      .getByRole("tab", { name: "Overview", exact: true })
      .getAttribute("aria-selected"),
    "true",
  );
  assert.equal(
    await page.locator(".company-chart-disclosure").getAttribute("open"),
    null,
  );
  for (const width of [1920, 1600, 1440, 1024, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 1000 });
    await tabs.scrollIntoViewIfNeeded();
    const orientation = width >= 1100 ? "vertical" : "horizontal";
    await page.waitForFunction(
      (o) =>
        document
          .querySelector('[aria-label="Research views"]')
          .getAttribute("aria-orientation") === o,
      orientation,
    );
    for (const label of labels) {
      const button = tabs.getByRole("tab", { name: label, exact: true });
      await button.click();
      assert.equal(await button.getAttribute("aria-selected"), "true");
      assert.equal(
        await page.getByRole("tabpanel").getAttribute("aria-labelledby"),
        await button.getAttribute("id"),
      );
      assert.equal(
        await page.locator(".research-section-heading h2").textContent(),
        label,
      );
      const size = await button.boundingBox();
      assert.ok(size.height >= 44, `${width}: ${label} target`);
      const geometry = await page.evaluate(() => ({
        document: document.documentElement.scrollWidth,
        viewport: innerWidth,
        main: document.querySelector(".main-workspace").scrollWidth,
        client: document.querySelector(".main-workspace").clientWidth,
      }));
      assert.ok(
        geometry.document <= width + 1 && geometry.main <= geometry.client + 1,
        `${width}: ${label} overflow ${JSON.stringify(geometry)}`,
      );
      layouts.push({ width, label, ...geometry });
    }
    await tabs.getByRole("tab", { name: "Overview", exact: true }).click();
    await tabs.getByRole("tab", { name: "Overview", exact: true }).focus();
    await page.keyboard.press(width >= 1100 ? "ArrowDown" : "ArrowRight");
    assert.equal(
      await tabs
        .getByRole("tab", { name: "Financials", exact: true })
        .getAttribute("aria-selected"),
      "true",
    );
    await page.keyboard.press("Home");
    assert.equal(
      await tabs
        .getByRole("tab", { name: "Overview", exact: true })
        .getAttribute("aria-selected"),
      "true",
    );
    await tabs.scrollIntoViewIfNeeded();
    if (width > 740) {
      await main.evaluate((el) => {
        el.scrollTop +=
          el.querySelector(".research-browser").getBoundingClientRect().top -
          el.getBoundingClientRect().top;
      });
    } else {
      await page.evaluate(() => {
        window.scrollBy(
          0,
          document.querySelector(".research-browser").getBoundingClientRect()
            .top -
            document.querySelector(".topbar").getBoundingClientRect().height -
            16,
        );
      });
    }
    await page.locator(".research-section-heading h2").click();
    if ([1920, 1440, 390, 320].includes(width))
      await page.screenshot({
        path: path.join(evidence, `research-${width}.png`),
      });
  }
  await page.setViewportSize({ width: 1920, height: 1000 });
  await tabs.scrollIntoViewIfNeeded();
  const nav = page.locator(".research-navigation");
  await main.evaluate((el) => {
    const nav = el.querySelector(".research-navigation");
    el.scrollTop +=
      nav.getBoundingClientRect().top - el.getBoundingClientRect().top + 250;
  });
  assert.ok(
    Math.abs((await nav.boundingBox()).y - (await main.boundingBox()).y - 24) <
      2,
    "wide section menu stays visible during reading",
  );
  await tabs
    .getByRole("tab", { name: "News & discussion", exact: true })
    .click();
  await page.getByRole("heading", {name:"Recent company news",exact:true}).click();
  await page.screenshot({
    path: path.join(evidence, "report-reading-1920.png"),
  });
  await page.getByRole("button", { name: "My research", exact: true }).click();
  const question = page.getByRole("region", {
    name: "Question-focused research",
    exact: true,
  });
  await question.scrollIntoViewIfNeeded();
  await question
    .getByRole("button", { name: "Edit question", exact: true })
    .click();
  const original = await question
    .getByRole("textbox", { name: "Your research question" })
    .inputValue();
  await question
    .getByRole("textbox", { name: "Your research question" })
    .fill("Temporary browser-only layout draft");
  await page.keyboard.press("Escape");
  await tabs.getByRole("tab", { name: "Financials", exact: true }).click();
  await tabs.getByRole("tab", { name: "Overview", exact: true }).click();
  await page.getByRole("button", { name: "My research", exact: true }).click();
  assert.equal(
    await question
      .getByRole("textbox", { name: "Your research question" })
      .inputValue(),
    "Temporary browser-only layout draft",
  );
  await question
    .getByRole("button", { name: "Cancel edit", exact: true })
    .click();
  assert.ok(original.length > 0);
  await page.keyboard.press("Escape");
  assert.equal(
    await page
      .getByRole("button", { name: "My research", exact: true })
      .evaluate((el) => document.activeElement === el),
    true,
  );
  assert.equal(
    await page.locator(".company-header h1").textContent(),
    savedTitle,
  );
  const railLayouts = [];
  for (const width of [1440, 1920]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const compact of [false, true]) {
      const hiddenIdea = true;
      const shell = page.locator(".app-shell");
      if (
        ((await shell.getAttribute("data-companies-hidden")) === "true") !==
        compact
      )
        await page
          .getByRole("button", {
            name: compact
              ? "Collapse company sidebar"
              : "Expand company sidebar",
            exact: true,
          })
          .click();
      const geometry = await page.evaluate(() => ({
        document: document.documentElement.scrollWidth,
        main: document.querySelector(".main-workspace").scrollWidth,
        client: document.querySelector(".main-workspace").clientWidth,
      }));
      assert.ok(
        geometry.document <= width + 1 && geometry.main <= geometry.client + 1,
        `rail layout ${width} ${compact} ${hiddenIdea}`,
      );
      railLayouts.push({ width, compact, hiddenIdea, ...geometry });
    }
  }
  assert.deepEqual(errors, []);
  assert.deepEqual(writes, []);
  assert.deepEqual(external, []);
  fs.writeFileSync(
    path.join(evidence, "verification.json"),
    JSON.stringify({ layouts, railLayouts, errors, writes, external }, null, 2),
  );
  await browser.close();
  browser = null;
  console.log(
    "All five research sections, orientation-aware keyboard controls, sticky wide navigation, retained question draft, unchanged company and 35 section/width layouts plus four company-sidebar combinations passed. No app writes or external requests.",
  );
})().catch(async (error) => {
  console.error(error);
  if (browser) {
    const failedPage = browser.contexts()[0]?.pages()[0];
    if (failedPage) {
      console.error(await failedPage.locator("body").innerText());
      await failedPage.screenshot({ path: path.join(evidence, "failure.png") });
    }
    await browser.close();
  }
  process.exitCode = 1;
});
