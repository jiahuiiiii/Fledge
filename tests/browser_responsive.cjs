// Every main Pro view at phone, tablet and desktop widths: no sideways scroll,
// and the company header keeps its buttons on the price row on desktop.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const assert = require("node:assert/strict");
let browser;
(async () => {
  browser = await chromium.launch({ headless: true, ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}) });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, reducedMotion: "reduce" });
  const errors = [], external = [], problems = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.route("**/*", (route) => {
    const request = route.request(), url = request.url();
    if (url.startsWith(process.env.THESIS_TEST_URL)) {
      if (url.endsWith("/loading")) return route.fulfill({ json: { result: null } });
      if (request.method() !== "GET") return route.fulfill({ status: 403, json: { result: { error: "blocked" } } });
      return route.continue();
    }
    if (url.startsWith("https://financialmodelingprep.com/image-stock/")) return route.fulfill({ status: 404, body: "" });
    external.push(url);
    return route.abort();
  });
  const shot = (name) => process.env.THESIS_SHOTS && page.screenshot({ path: `${process.env.THESIS_SHOTS}/${name}.png`, animations: "disabled" });
  await page.goto(process.env.THESIS_TEST_URL);
  const skip = page.getByRole("button", { name: /Skip, show me the app/ });
  if (await skip.waitFor({ timeout: 3000 }).then(() => true, () => false)) await skip.click();
  await page.locator(".watch-item").filter({ hasText: "MSFT" }).click();
  const pro = page.getByRole("button", { name: "Turn on Pro tools" });
  if (await pro.waitFor({ timeout: 8000 }).then(() => true, () => false)) await pro.click();
  await page.getByRole("tab", { name: "Overview", exact: true }).waitFor();

  const views = [
    ["overview", () => page.getByRole("tab", { name: "Overview", exact: true }).click()],
    ["news", () => page.getByRole("tab", { name: "News & discussion", exact: true }).click()],
    ["financials", () => page.getByRole("tab", { name: "Financials", exact: true }).click()],
    ["compare", () => page.getByRole("tab", { name: "Compare & value", exact: true }).click()],
  ];
  for (const [name, go] of views) {
    await go();
    await page.waitForTimeout(1200);
    for (const width of [320, 390, 768, 1024, 1440]) {
      await page.setViewportSize({ width, height: 1000 });
      await page.waitForTimeout(250);
      const overflow = await page.evaluate(() => {
        const limit = innerWidth;
        const wide = [...document.querySelectorAll("body *")]
          .filter((el) => { const r = el.getBoundingClientRect(); return r.width > 0 && r.right > limit + 1 && !el.closest("[hidden],dialog:not([open]),.sr-only,[aria-hidden=true]") && !el.closest("svg,table,pre,.position-bars,.revenue-chart,[tabindex='0']"); })
          .slice(0, 3).map((el) => `${el.tagName.toLowerCase()}.${String(el.className).slice(0, 50)}`);
        return { scroll: document.documentElement.scrollWidth - limit, wide };
      });
      if (overflow.scroll > 0 || overflow.wide.length) problems.push(`${name}@${width}: scroll +${overflow.scroll} ${overflow.wide.join(" | ")}`);
      if (width >= 1024) {
        const header = await page.evaluate(() => {
          const q = document.querySelector(".company-header .market-quote"), a = document.querySelector(".company-header .company-actions");
          if (!a) return null;
          const ar = a.getBoundingClientRect(), qr = q?.getBoundingClientRect();
          return { sameRow: !qr || ar.top < qr.bottom - 4, beside: !qr || ar.left >= qr.right - 4 };
        });
        if (header && !(header.sameRow && header.beside)) problems.push(`header buttons not beside the price at ${width} on ${name}`);
      }
      if (width === 390 || width === 1440) await shot(`${name}-${width}`);
    }
  }
  // Account page: Account is a header tab (underlined), Telegram lives here, no sideways scroll.
  await page.goto(`${process.env.THESIS_TEST_URL}/?view=account`);
  await page.getByRole("heading", { name: "Account", exact: true }).waitFor();
  assert.equal(await page.locator(".topbar-tab[aria-current='page']").count(), 1);
  assert.equal(await page.locator(".topbar-tools").getByRole("button", { name: "Telegram alerts" }).count(), 0);
  for (const width of [320, 390, 768, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.waitForTimeout(250);
    const scroll = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
    if (scroll > 0) problems.push(`account@${width}: scroll +${scroll}`);
    if (width === 390 || width === 1440) await shot(`account-${width}`);
  }
  console.log(JSON.stringify({ problems }, null, 1));
  assert.deepEqual(problems, []);
  assert.deepEqual(errors, []);
  assert.deepEqual(external, []);
  await browser.close();
})().catch(async (e) => { console.error(e); await browser?.close(); process.exit(1); });
