// Authored cards exercise existing read-only account/source-scoped endpoints.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const assert = require("node:assert/strict"),
  fs = require("node:fs");
let browser;
(async () => {
  const { companyName } = await import(
    "../frontend/src/lib/companyIdentity.js"
  );
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
    external = [],
    reads = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.route("**/*", (route) => {
    const r = route.request(),
      u = new URL(r.url());
    if (
      u.hostname === "financialmodelingprep.com" &&
      r.resourceType() === "image"
    )
      return route.fulfill({ status: 404, body: "Authored missing logo" });
    if (!u.href.startsWith(base)) {
      external.push(u.href);
      return route.abort();
    }
    if (u.pathname.endsWith("/loading"))
      return route.fulfill({ json: { result: { active: false, steps: [] } } });
    if (r.method() !== "GET") {
      writes.push(u.pathname);
      return route.abort();
    }
    return route.continue();
  });
  await page.goto(base + "/?view=workspace");
  await page
    .getByRole("region", { name: "All company workspaces", exact: true })
    .waitFor();
  const original = (
    await (
      await page.request.get(
        base +
          "/api/v1/workspace?instrument_id=c767e09f-35ea-5eaf-a626-ff5d3aa4709b",
      )
    ).json()
  ).result;
  const catalogue = [
    ["AMD", "ADVANCED MICRO DEVICES INC"],
    ["AVGO", "Broadcom Inc."],
    ["MRVL", "Marvell Technology, Inc."],
    ["MU", "MICRON TECHNOLOGY INC"],
    ["NVDA", "NVIDIA"],
    ["QCOM", "QUALCOMM INC/DE"],
    [
      "LONG",
      "A very long authored company name that should remain readable through its full accessible label",
    ],
  ].map(([symbol, name], n) => ({
    id: "authored-" + symbol,
    symbol,
    name,
    mode: "sec",
    unread: n === 1 ? 2 : 0,
    status: null,
    question: null,
  }));
  const workspace = (c) => ({
    ...original,
    catalogue,
    instrument: { ...original.instrument, ...c },
    market: {
      ...original.market,
      quote: {
        quote: {
          price: "80",
          change: "80",
          change_percent: "100",
          quoted_at: "2026-10-07T15:00:00Z",
        },
      },
    },
    financial_depth:
      c.symbol === "LONG"
        ? null
        : {
            ...original.financial_depth,
            trailing: [
              {
                key: "revenue",
                value: "64000000000",
                start: "2024-10-01",
                end: "2025-09-30",
              },
              {
                key: "operating_margin",
                value: c.symbol === "MU" ? "-12" : "25",
                start: "2024-10-01",
                end: "2025-09-30",
              },
            ],
          },
  });
  const history = (c) => ({
    available: true,
    configured: false,
    symbol: c.symbol,
    snapshot: {
      series: {
        omitted_sessions: 0,
        latest_quote: {
          price: c.symbol === "MU" ? "95" : "105",
          quoted_at: "2026-10-08T15:01:00Z",
          session: "regular session",
        },
        bars: [
          { date: "2026-10-07", close: "100", provisional: false },
          { date: "2026-10-08", close: "104", provisional: true },
        ],
      },
    },
  });
  let fail = false,
    hold = false,
    release;
  await page.route("**/api/v1/workspace*", async (route) => {
    const id = new URL(route.request().url()).searchParams.get("instrument_id");
    const c = catalogue.find((c) => c.id === id) || catalogue[0];
    reads.push({ kind: "workspace", id: c.id });
    if (hold && c.symbol === "QCOM")
      await new Promise((resolve) => (release = resolve));
    if (fail && c.symbol === "LONG")
      return route.fulfill({
        status: 503,
        json: {
          result: { errors: [{ error_message: "Authored read unavailable" }] },
        },
      });
    return route.fulfill({ json: { result: workspace(c) } });
  });
  await page.route("**/api/v1/companies/*/price-history", (route) => {
    const c = catalogue.find((c) => route.request().url().includes(c.id));
    reads.push({ kind: "price", id: c?.id });
    return route.fulfill({
      json: {
        result:
          c?.symbol === "LONG"
            ? { available: false, symbol: c.symbol }
            : history(c),
      },
    });
  });
  await page.goto(base + "/?view=workspace");
  const all = page.getByRole("region", {
    name: "All company workspaces",
    exact: true,
  });
  await page.waitForFunction(
    () =>
      document
        .querySelector(".company-overview-grid")
        ?.getAttribute("aria-busy") === "false",
  );
  assert.equal(await all.locator(".company-overview-card").count(), 7);
  assert.doesNotMatch(
    await all.innerText(),
    /Start with a research question|NaN|Invalid Date/,
  );
  for (const c of catalogue.slice(0, 6)) {
    const card = all.locator(`[data-company="${c.id}"]`);
    assert.equal(
      await card.locator(".company-overview-identity strong").innerText(),
      companyName(c),
    );
    assert.equal(
      await card
        .locator(".company-overview-identity strong")
        .getAttribute("title"),
      c.name,
    );
    assert.match(await card.innerText(), /US\$64bn/);
    assert.match(await card.innerText(), /SEC · to 30 Sept 2025/);
    assert.match(
      await card.locator(".price-change").innerText(),
      c.symbol === "MU" ? /−5.00 \(−5.00%\)/ : /\+5.00 \(\+5.00%\)/,
    );
  }
  const mrvl = all.locator('[data-company="authored-MRVL"]');
  await mrvl.locator(".company-avatar.has-logo").waitFor();
  assert.equal(
    await mrvl
      .locator(".company-avatar img")
      .evaluate((img) => img.naturalWidth),
    128,
  );
  assert.equal(
    await mrvl
      .locator(".company-avatar")
      .evaluate((el) => getComputedStyle(el).backgroundColor),
    "rgb(38, 48, 67)",
  );
  assert.match(
    await all.locator('[data-company="authored-LONG"]').innerText(),
    /Unavailable/,
  );
  await all.getByRole("searchbox", { name: "Find a company" }).fill("INC/DE");
  assert.equal(await all.locator(".company-overview-card").count(), 1);
  assert.match(await all.innerText(), /Qualcomm/);
  await all
    .getByRole("searchbox", { name: "Find a company" })
    .fill("no matching company");
  assert.match(await all.innerText(), /No companies match/);
  await all.getByRole("searchbox", { name: "Find a company" }).fill("");
  const save = async (name) => {
    if (process.env.THESIS_COMPANIES_EVIDENCE)
      await page.screenshot({
        path: `${process.env.THESIS_COMPANIES_EVIDENCE}/${name}.png`,
        animations: "disabled",
      });
  };
  for (const width of [1440, 980, 390, 320]) {
    await page.setViewportSize({ width, height: 1050 });
    await page.evaluate(() => scrollTo(0, 0));
    await page.evaluate(() => document.fonts.ready);
    await page.evaluate(
      () =>
        new Promise((r) =>
          requestAnimationFrame(() => requestAnimationFrame(r)),
        ),
    );
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      `overflow ${width}`,
    );
    assert.equal(
      await all
        .locator(".company-overview-card")
        .first()
        .evaluate((el) => el.getBoundingClientRect().height >= 44),
      true,
    );
    await save(`authored-companies-${width}`);
  }
  await page.setViewportSize({ width: 1440, height: 1050 });
  await mrvl.focus();
  await page.keyboard.press("Enter");
  await page
    .locator(".company-header h1")
    .filter({ hasText: "Marvell Technology" })
    .waitFor();
  const quote = page.getByRole("region", { name: "Market quote", exact: true });
  await quote.locator(".price-change").waitFor();
  assert.match(
    await quote.innerText(),
    /105.00[\s\S]*\+5.00 \(\+5.00%\)[\s\S]*vs 7 Oct close/,
  );
  assert.doesNotMatch(await quote.innerText(), /\+80/);
  await save("authored-mrvl-header");
  // In-flight reads from All cannot replace a subsequently selected company.
  await page
    .getByRole("button", { name: "All companies", exact: true })
    .click();
  await all.waitFor();
  await page.waitForFunction(
    () =>
      document
        .querySelector(".company-overview-grid")
        ?.getAttribute("aria-busy") === "false",
  );
  fail = true;
  await all
    .getByRole("button", { name: "Reload saved data", exact: true })
    .click();
  await all
    .getByText("Saved data unavailable. Reload to try again.", { exact: true })
    .waitFor();
  fail = false;
  hold = true;
  await all
    .getByRole("button", { name: "Reload saved data", exact: true })
    .click();
  await all
    .locator('[data-company="authored-MRVL"] .company-overview-quote')
    .waitFor();
  await all
    .getByRole("button", {
      name: "Open MRVL · Marvell Technology",
      exact: true,
    })
    .click();
  release?.();
  hold = false;
  await page
    .locator(".company-header h1")
    .filter({ hasText: "Marvell Technology" })
    .waitFor();
  assert.equal(await page.locator(".company-overview").count(), 0);
  assert.deepEqual(errors, []);
  assert.deepEqual(writes, []);
  assert.deepEqual(external, []);
  const report = {
    authoredData: true,
    companies: 7,
    widths: [1440, 980, 390, 320],
    savedPricesFinancialsDates: true,
    canonicalNamesRetained: true,
    aliasAndLegalSearch: true,
    marvellWhiteMarkOnDark: true,
    headerChangeSameSource: true,
    negativeAndMissing: true,
    keyboardNavigation: true,
    readFailureAndLateResult: true,
    errors,
    writes,
    external,
    reads,
  };
  if (process.env.THESIS_COMPANIES_EVIDENCE)
    fs.writeFileSync(
      process.env.THESIS_COMPANIES_EVIDENCE + "/browser.json",
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
