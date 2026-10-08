const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const assert = require("node:assert/strict"),
  fs = require("node:fs");
(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_PATH,
  });
  try {
    const page = await browser.newPage({
        viewport: { width: 1440, height: 1100 },
      }),
      errors = [],
      forbidden = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.route("**/*", (r) => {
      const u = new URL(r.request().url());
      if (u.hostname !== "127.0.0.1" || r.request().method() !== "GET") {
        forbidden.push(u.pathname);
        return r.abort();
      }
      return r.continue();
    });
    const base = process.env.THESIS_TEST_URL;
    await page.goto(
      base + "/?company=c767e09f-35ea-5eaf-a626-ff5d3aa4709b&view=history",
    );
    const checks = page.getByRole("region", {
      name: "Evidence linked to saved reasoning",
      exact: true,
    });
    const pair = checks.locator(".answer-evidence").first();
    await pair.waitFor();
    assert.match(
      await pair.innerText(),
      /Question addressed: What operating margin did Microsoft report for Q3/,
    );
    assert.match(
      await pair.innerText(),
      /Microsoft reports an operating margin of 38% for Q3/,
    );
    assert.match(await pair.innerText(), /AI assessment: answers part/);
    for (const width of [320, 390, 1440]) {
      await page.setViewportSize({ width, height: 1100 });
      assert.ok(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      );
      await pair
        .locator("..")
        .screenshot({
          path: `/private/tmp/thesis-answer-evidence-${width}.png`,
        });
    }
    const event = page.waitForEvent("download");
    await checks
      .getByRole("link", { name: "Download this check", exact: true })
      .first()
      .click();
    const download = await event,
      html = fs.readFileSync(await download.path(), "utf8");
    assert.match(html, /Question addressed: What operating margin/);
    assert.match(html, /Answer evidence · original wording/);
    assert.doesNotMatch(html, /<script/);
    await page.reload();
    await pair.waitFor();
    assert.match(await pair.innerText(), /38%/);
    assert.deepEqual(errors, []);
    assert.deepEqual(forbidden, []);
    console.log(
      "Answer evidence browser passed: exact question/source pair, private download, reopening, 320/390/1440 layouts, no writes or external requests.",
    );
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
