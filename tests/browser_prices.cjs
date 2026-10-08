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
    external = [],
    writes = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.route("**/*", (r) => {
    const u = new URL(r.request().url());
    if (!["127.0.0.1", "localhost"].includes(u.hostname)) {
      external.push(u.href);
      return r.abort();
    }
    if (r.request().method() === "POST") writes.push(u.pathname);
    return r.continue();
  });
  const base = process.env.THESIS_TEST_URL,
    iid = "c767e09f-35ea-5eaf-a626-ff5d3aa4709b";
  await page.goto(base + "/?company=" + iid + "&view=workspace");
  const panel = page.getByRole("region", {
    name: "Daily price history",
    exact: true,
  });
  await panel
    .getByRole("region", { name: "Historical price chart", exact: true })
    .waitFor();
  await panel.getByText("Inspect daily prices and source", { exact: true }).click();
  assert.match(await panel.innerText(), /252 supplied sessions/);
  assert.match(await panel.innerText(), /Current-day bars are excluded/);
  assert.match(await panel.innerText(), /1 sessions have no reported volume/);
  const state = (
    await (
      await page.request.get(base + `/api/v1/companies/${iid}/price-history`)
    ).json()
  ).result;
  const bars = state.snapshot.series.bars;
  assert.match(
    await panel.getByRole("img").getAttribute("aria-label"),
    new RegExp(bars.at(-1).date),
  );
  await panel.getByRole("button", { name: "1Y", exact: true }).click();
  assert.match(
    await panel.getByRole("img").getAttribute("aria-label"),
    new RegExp(bars[0].date),
  );
  await panel.getByRole("button", { name: "Candles", exact: true }).click();
  assert.match(
    await panel.getByRole("img").getAttribute("aria-label"),
    /line chart/,
  );
  await panel.getByText("Inspect a trading session", { exact: true }).click();
  const slider = panel.getByRole("slider", {
    name: "Trading session",
    exact: true,
  });
  await slider.focus();
  await slider.press("Home");
  assert.equal(await slider.getAttribute("aria-valuetext"), bars[0].date);
  assert.match(
    await panel.locator("output").innerText(),
    new RegExp(bars[0].date),
  );
  await slider.press("ArrowRight");
  assert.equal(await slider.getAttribute("aria-valuetext"), bars[1].date);
  if (!(await panel.getByText("Inspect daily prices and source", { exact: true }).evaluate(e => e.parentElement.open)))
    await panel.getByText("Inspect daily prices and source", { exact: true }).click();
  assert.equal(await panel.locator("tbody tr").count(), 252);
  assert.match(await panel.innerText(), /not dividend-adjusted/);
  assert.match(await panel.innerText(), /Unknown/);
  if (!(await panel.getByText("Inspect daily prices and source", { exact: true }).evaluate(e => e.parentElement.open)))
    await panel.getByText("Inspect daily prices and source", { exact: true }).click();
  for (const width of [320, 390, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      `Overflow ${width}`,
    );
    await page.screenshot({
      path: `/private/tmp/thesis-prices-${width}.png`,
      fullPage: false,
    });
  }
  await page.locator(".watch-item").filter({hasText:"AAPL"}).click();
  await panel.getByText(/No daily history has been retrieved/).waitFor();
  assert.equal(await panel.getByRole("img").count(), 0);
  await page.locator(".watch-item").filter({hasText:"MSFT"}).click();
  await panel.getByRole("img").waitFor();
  await panel.getByText("Inspect daily prices and source", { exact: true }).click();
  assert.match(await panel.innerText(), /252 supplied sessions/);
  assert.deepEqual(errors, []);
  assert.deepEqual(external, []);
  assert.deepEqual(writes, []);
  console.log(
    "Daily-price browser passed: cached bars, ranges, line/candles, keyboard dates, source table, missing volume, empty company, 320/390/1440 layouts, no external or paid requests.",
  );
  await browser.close();
})().catch(async (e) => {
  console.error(e);
  if (browser) await browser.close();
  process.exit(1);
});
