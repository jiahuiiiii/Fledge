const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
const assert = require("node:assert/strict");
const fs = require("node:fs");
let browser;
(async () => {
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_PATH,
  });
  const page = await browser.newPage({
      viewport: { width: 1440, height: 1100 },
    }),
    errors = [],
    external = [],
    writes = [];
  const folder =
    process.env.THESIS_SECTOR_SCREENSHOTS ||
    "/private/tmp/thesis-sector-screenshots";
  fs.mkdirSync(folder, { recursive: true });
  page.on("pageerror", (e) => errors.push(e.message));
  await page.route("**/*", (route) => {
    const r = route.request(),
      url = r.url();
    if (url.startsWith(process.env.THESIS_TEST_URL)) {
      if (url.endsWith("/loading"))
        return route.fulfill({ json: { result: null } });
      if (r.method() !== "GET") {
        writes.push(url);
        if (r.method() === "PUT" && url.endsWith("/fmp/peers"))
          return route.continue();
        return route.fulfill({
          status: 403,
          json: { error: "Authored test blocks unexpected mutation" },
        });
      }
      return route.continue();
    }
    if (url.startsWith("https://financialmodelingprep.com/image-stock/"))
      return route.fulfill({ status: 404, body: "Authored missing logo" });
    external.push(url);
    return route.abort();
  });
  await page.goto(process.env.THESIS_TEST_URL);
  await page
    .getByRole("button", { name: /MSFT · Microsoft/ })
    .first()
    .click();
  await page.getByRole("tab", { name: "Compare & value", exact: true }).click();
  const panel = page.getByRole("region", {
    name: "Competitor position",
    exact: true,
  });
  await panel
    .getByRole("heading", {
      name: "Where MSFT stands among competitors",
      exact: true,
    })
    .waitFor();
  await panel.locator(".position-group > summary").click();
  const peer = panel.getByLabel("Sector competitor 1");
  await peer.focus();
  await page.keyboard.press("n");
  await page.keyboard.press("Enter");
  assert.equal(await peer.inputValue(), "NVDA");
  await panel
    .getByLabel("Why compare NVDA")
    .fill("Authored comparison of growth and margins; products differ.");
  await panel
    .getByRole("button", { name: "Apply comparison group", exact: true })
    .click();
  await panel
    .locator(".position-reading")
    .getByText("MSFT is below NVDA.", { exact: true })
    .waitFor();
  assert.equal(writes.length, 0);
  const rows = panel.locator(".position-comparison-row");
  assert.equal(await rows.count(), 2);
  assert.match(await rows.first().innerText(), /23.1%/);
  const evidence = rows.first();
  await evidence.focus();
  await page.keyboard.press("Enter");
  const dialog = page.getByRole("dialog");
  assert.equal(
    await dialog.locator(".position-evidence-list > details").count(),
    2,
  );
  assert.match(await dialog.innerText(), /23.08%/);
  assert.doesNotMatch(await dialog.innerText(), /RevenueFromContract|source snapshot|accession/i);
  await page.keyboard.press("Escape");
  assert.equal(
    await evidence.evaluate((e) => document.activeElement === e),
    true,
  );
  await panel.getByLabel("Competitor measure").focus();
  await page.keyboard.press("o");
  await page.keyboard.press("Enter");
  await panel
    .locator(".position-reading")
    .getByText("MSFT is above NVDA.", { exact: true })
    .waitFor();
  for (const width of [1440, 980, 390, 320]) {
    await page.setViewportSize({ width, height: 1100 });
    await panel.locator(".position-map-wrap").scrollIntoViewIfNeeded();
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    );
    await page.screenshot({
      path: `${folder}/reported-map-${width}.png`,
      animations: "disabled",
    });
    await panel.locator(".position-reading").scrollIntoViewIfNeeded();
    await page.screenshot({
      path: `${folder}/reported-bars-${width}.png`,
      animations: "disabled",
    });
  }
  await page.setViewportSize({ width: 1440, height: 1100 });
  await panel
    .getByRole("button", { name: "Save peers for this company", exact: true })
    .click();
  await panel
    .getByText("Using your saved comparison companies.", { exact: false })
    .waitFor();
  assert.equal(writes.length, 1);
  await page.getByRole("tab", { name: "Financials", exact: true }).click();
  await page.locator(".financial-peer-context").waitFor();
  assert.equal(
    await page.locator(".financials-story .sector-position").count(),
    0,
  );
  await page.getByRole("tab", { name: "Compare & value", exact: true }).click();
  await panel.locator(".position-group > summary").click();
  if (!(await panel.locator(".position-group").evaluate((e) => e.open)))
    await panel.locator(".position-group > summary").click();
  await panel.getByRole("button", { name: "Add peer", exact: true }).click();
  assert.equal(await panel.getByLabel("Sector competitor 2").inputValue(), "");
  await page.getByRole("tab", { name: "Financials", exact: true }).click();
  await page.getByRole("tab", { name: "Compare & value", exact: true }).click();
  await panel.getByLabel("Sector competitor 2").waitFor();
  assert.equal(await panel.getByLabel("Sector competitor 2").inputValue(), "");
  await panel.getByLabel("Competitor measure").focus();
  await page.keyboard.press("Home");
  await page.keyboard.press("Enter");
  await rows.first().getByText("29.4×", { exact: true }).waitFor();
  assert.match(
    await panel.locator(".position-average-flag").innerText(),
    /45.1×/,
  );
  assert.equal(await panel.locator(".position-map-wrap").count(), 0);
  await rows.first().click();
  assert.match(await dialog.innerText(), /29.38×/);
  assert.match(await dialog.innerText(), /Finnhub vendor TTM definition/);
  assert.match(
    await dialog.locator(".position-average-evidence").innerText(),
    /Included: NVDA/,
  );
  await page.keyboard.press("Escape");
  for (const width of [1440, 390, 320]) {
    await page.setViewportSize({ width, height: width < 600 ? 844 : 1050 });
    await panel.locator(".position-comparison").scrollIntoViewIfNeeded();
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    );
    await page.screenshot({ path: `${folder}/pe-${width}.png` });
  }
  await page.setViewportSize({ width: 1440, height: 1100 });
  // Comparable positive, negative and zero figures share a baseline; gaps stay readable separately.
  let scenario = "mixed";
  await page.route("**/sector-position*", async (route) => {
    const response = await route.fetch(),
      body = await response.json(),
      base = body.result.members;
    const zero = structuredClone(base[1]),
      missing = structuredClone(base[1]);
    zero.symbol = "ZERO";
    zero.name = "Authored zero";
    missing.symbol = "GAP";
    missing.name = "Authored missing";
    missing.performance.status = "unavailable";
    body.result.members = [...base, zero, missing];
    body.result.peers = [...body.result.peers, "ZERO", "GAP"];
    for (const [index, m] of body.result.members.entries()) {
      const row = m.performance.reports.annual.metrics.find(
        (r) => r.key === "revenue_growth",
      );
      if (index === 0 || index === 2 || scenario === "zero") {
        row.value = scenario === "zero" || index === 2 ? "0" : "-25";
        row.inputs[0].value = String(
          Number(row.inputs[1].value) * (1 + Number(row.value) / 100),
        );
      }
      if (scenario === "missing") m.performance.status = "unavailable";
    }
    return route.fulfill({ response, json: body });
  });
  async function reloadComparison() {
    await page.getByRole("tab", { name: "Financials", exact: true }).click();
    await page
      .getByRole("tab", { name: "Compare & value", exact: true })
      .click();
  }
  await reloadComparison();
  await panel.getByLabel("Competitor measure").focus();
  await page.keyboard.press("Home");
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Enter");
  await rows.first().getByText("-25.0%", { exact: true }).waitFor();
  assert.equal(await rows.count(), 3);
  assert.equal(await panel.locator(".position-excluded-row").count(), 1);
  assert.match(await panel.locator(".position-excluded-row").innerText(), /GAP.*Authored missing/s);
  const geometry = await rows.evaluateAll((nodes) =>
    nodes.map((n) => {
      const f = n.querySelector(".position-row-fill");
      return f
        ? {
            left: parseFloat(f.style.left),
            width: parseFloat(f.style.width),
            zero: f.classList.contains("is-zero"),
          }
        : null;
    }),
  );
  assert.ok(
    Math.abs(geometry[0].left + geometry[0].width - geometry[1].left) < 0.001,
    "positive and negative bars meet at the same zero",
  );
  assert.equal(geometry[2].width, 0);
  assert.equal(geometry[2].zero, true);
  await panel
    .getByRole("button", { name: "Evidence & periods", exact: true })
    .click();
  assert.equal(
    await dialog.locator(".position-evidence-list > details").count(),
    4,
  );
  await dialog.locator(".position-evidence-list > details > summary").last().click();
  assert.match(await dialog.innerText(), /unavailable/i);
  await page.keyboard.press("Escape");
  await page.screenshot({
    path: `${folder}/mixed-values.png`,
    animations: "disabled",
  });
  scenario = "zero";
  await reloadComparison();
  await page.waitForFunction(
    () => document.querySelectorAll(".position-row-fill.is-zero").length === 3,
  );
  scenario = "missing";
  await reloadComparison();
  await page.waitForFunction(
    () =>
      document.querySelectorAll(".position-row-label .is-missing").length === 1 &&
      document.querySelectorAll(".position-excluded-row").length === 3,
  );
  assert.equal(await panel.locator(".position-row-fill").count(), 0);
  assert.equal(await panel.locator(".position-scale > span").count(), 0);
  await page.unroute("**/sector-position*");
  // Future figures are authored controlled responses, separate from original filings.
  await page.route("**/sector-position*", async (route) => {
    const response = await route.fetch(),
      body = await response.json();
    for (const m of body.result.members) {
      m.consensus = {
        status: "saved",
        snapshot_id: "authored-" + m.symbol,
        first_observed_at: "2026-10-09T00:00:00Z",
        data: {
          method: "fmp-research-1",
          forecasts: [
            {
              period_type: "annual",
              period_end: "2026-12-31",
              currency: "USD",
              metrics: [{ key: "revenue", average: "100" }],
            },
            {
              period_type: "annual",
              period_end: "2027-12-31",
              currency: "USD",
              metrics: [
                {
                  key: "revenue",
                  average: m.symbol === "MSFT" ? "120" : "130",
                },
              ],
            },
          ],
        },
      };
    }
    return route.fulfill({ response, json: body });
  });
  await page.getByRole("tab", { name: "Financials", exact: true }).click();
  await page.getByRole("tab", { name: "Compare & value", exact: true }).click();
  await panel
    .getByRole("button", { name: "Expected growth", exact: true })
    .click();
  await panel.getByLabel("Competitor forecast year").focus();
  await page.keyboard.press("End");
  await page.keyboard.press("Enter");
  await panel
    .locator(".position-reading")
    .getByText("MSFT is below NVDA.", { exact: true })
    .waitFor();
  assert.match(await panel.innerText(), /forecast-to-forecast/);
  assert.match(
    await panel.locator(".position-comparison-row").first().innerText(),
    /20.0%/,
  );
  await rows.first().click();
  assert.match(await dialog.innerText(), /120/);
  assert.match(await dialog.innerText(), /100/);
  assert.match(await dialog.innerText(), /two annual forecasts from the same FMP response/);
  assert.match(await dialog.innerText(), /underlying forecast date is unknown/);
  await page.keyboard.press("Escape");
  await panel.locator(".position-forward-details > summary").click();
  assert.match(
    await panel.locator(".position-forward-details").innerText(),
    /non-gaap/,
  );
  for (const width of [1440, 320]) {
    await page.setViewportSize({ width, height: 1100 });
    await panel.locator(".position-reading").scrollIntoViewIfNeeded();
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    );
    await page.screenshot({
      path: `${folder}/expected-${width}.png`,
      animations: "disabled",
    });
  }
  await page.emulateMedia({ reducedMotion: "reduce" });
  assert.deepEqual(errors, []);
  assert.deepEqual(external, []);
  assert.equal(writes.length, 1);
  console.log(
    JSON.stringify({
      journey: "competitor position",
      authored: true,
      viewports: [1440, 980, 390, 320],
      peerWrites: 1,
      sourceRequests: 0,
      aiRequests: 0,
      errors,
    }),
  );
  await browser.close();
})().catch(async (e) => {
  console.error(e);
  if (browser) await browser.close();
  process.exit(1);
});
