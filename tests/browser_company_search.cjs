const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
const assert = require("node:assert/strict");
(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_PATH,
  });
  try {
    const page = await browser.newPage({
      viewport: { width: 1440, height: 1000 },
    });
    let errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.route("**/*", (r) => {
      let u = new URL(r.request().url());
      if (!["127.0.0.1", "localhost"].includes(u.hostname)) return r.abort();
      return r.continue();
    });
    await page.goto(
      (process.env.THESIS_TEST_URL || "http://127.0.0.1:8844") + "/",
    );
    await page
      .getByRole("button", { name: "+ Add company", exact: true })
      .click();
    let dialog = page.getByRole("dialog");
    await dialog.getByLabel("Find a company").fill("Advanced Micro");
    const amd = dialog.getByRole("button", { name: /(?:Add|Open) AMD/ });
    await amd.waitFor();
    await page.screenshot({ path: "/private/tmp/thesis-company-search73.png" });
    await amd.click();
    await page.locator(".company-header").filter({ hasText: "AMD" }).waitFor();
    await page
      .getByRole("region", { name: "Question-focused research", exact: true })
      .waitFor();
    let check = page.getByRole("checkbox", {
      name: "Include social discussion",
    });
    await check.uncheck();
    await check.focus();
    await page.keyboard.press("Space");
    assert(await check.isChecked());
    assert.equal(
      await check.evaluate((e) => getComputedStyle(e).appearance),
      "none",
    );
    await page.screenshot({ path: "/private/tmp/thesis-question73.png" });
    for (const w of [320, 390, 1440, 1920]) {
      await page.setViewportSize({ width: w, height: 1000 });
      await page
        .getByRole("button", {
          name: w < 900 ? "Add company" : "+ Add company",
          exact: true,
        })
        .click();
      dialog = page.getByRole("dialog");
      await dialog.getByLabel("Find a company").fill("TSLA");
      await dialog.getByRole("button", { name: /Add TSLA/ }).waitFor();
      assert(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
        `page overflow ${w}`,
      );
      assert(
        await dialog.evaluate((e) => e.scrollWidth <= e.clientWidth),
        `dialog overflow ${w}`,
      );
      await page.screenshot({ path: `/private/tmp/thesis-search73-${w}.png` });
      await page.keyboard.press("Escape");
    }
    assert.deepEqual(errors, []);
    console.log(
      "Search by company name, add non-preset AMD, checkbox keyboard/appearance, dialog and question layouts 320–1920 passed.",
    );
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
