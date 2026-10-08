const { chromium } = require(process.env.PLAYWRIGHT_MODULE),
  assert = require("node:assert/strict");
(async () => {
  const b = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_PATH,
  });
  try {
    const p = await b.newPage({ viewport: { width: 1440, height: 1000 } });
    let errors = [];
    p.on("pageerror", (e) => errors.push(e.message));
    await p.goto(
      (process.env.THESIS_TEST_URL || "http://127.0.0.1:8844") +
        "/?company=4780d271-7c4a-5c18-80f8-74e164c21675&view=history",
    );
    await p.getByRole("button", { name: /Add your first company/ }).waitFor();
    for (const width of [320, 390, 1440, 1920]) {
      await p.setViewportSize({ width, height: 1000 });
      assert(
        await p.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      );
      await p.screenshot({ path: `/private/tmp/thesis-empty73-${width}.png` });
    }
    await p.setViewportSize({ width: 1440, height: 1000 });
    await p
      .getByRole("navigation")
      .getByRole("button", { name: "Updates", exact: true })
      .click();
    await p.getByRole("heading", { name: "No updates yet" }).waitFor();
    await p.getByRole("button", { name: /Add your first company/ }).click();
    const d = p.getByRole("dialog");
    await d.getByLabel("Find a company").fill("AMD");
    await d.getByRole("button", { name: /Add AMD/ }).click();
    await p.locator(".company-header").filter({ hasText: "AMD" }).waitFor();
    assert.equal(await p.locator(".watch-item").count(), 2); // All companies + AMD
    await p
      .getByRole("navigation")
      .getByRole("button", { name: "History", exact: true })
      .click();
    await p
      .getByRole("heading", { name: "Research history", exact: true })
      .waitFor();
    await p.reload();
    await p
      .getByRole("heading", { name: "Research history", exact: true })
      .waitFor();
    assert.deepEqual(errors, []);
    console.log(
      "Empty workspace, stale URL recovery, four viewport sizes, tabs, first company, and reload all passed.",
    );
  } finally {
    await b.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
