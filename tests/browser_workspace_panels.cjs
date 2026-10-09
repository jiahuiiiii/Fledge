// Read-only app UI check. Loading and failure-only logo fixtures are intercepted.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const base = process.env.THESIS_TEST_URL || "http://127.0.0.1:8841";
const evidence =
  process.env.THESIS_PANELS_EVIDENCE || "/private/tmp/thesis-panels";
const run = { active: false, steps: [] };
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
    external = [],
    writes = [],
    checks = [];
  let injectFixtures = false,
    mockedLogoFailures = 0,
    mockedLoading = 0;
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route("**/*", async (route) => {
    const request = route.request(),
      url = new URL(request.url());
    if (
      url.href === "https://financialmodelingprep.com/image-stock/ZZZZZ.png"
    ) {
      mockedLogoFailures++;
      return route.fulfill({
        status: 404,
        body: "Authored missing logo fixture",
      });
    }
    if (!["127.0.0.1", "localhost"].includes(url.hostname)) {
      external.push(url.hostname);
      return route.abort();
    }
    if (/\/companies\/[^/]+\/loading$/.test(url.pathname)) {
      mockedLoading++;
      return route.fulfill({ json: { result: run } });
    }
    if (request.method() !== "GET") {
      writes.push(url.pathname);
      return route.abort();
    }
    if (injectFixtures && url.pathname === "/api/v1/workspace") {
      const response = await route.fetch(),
        packet = await response.json();
      const original = packet.result.catalogue[0];
      packet.result.catalogue.push(
        {
          ...original,
          id: "aaaabbbb-1111-4111-8111-000000000001",
          symbol: "ZZZZZ",
          name: "Unavailable logo fixture",
          mode: "sec",
          unread: 0,
        },
        {
          ...original,
          id: "aaaabbbb-1111-4111-8111-000000000002",
          symbol: "NSTR",
          name: "Northstar fictional fixture",
          mode: "recorded",
          unread: 0,
        },
      );
      return route.fulfill({ response, json: packet });
    }
    return route.continue();
  });
  await page.goto(base + "/?view=workspace");
  await page.locator(".company-row .watch-item").first().waitFor();
  await page.locator(".company-row .watch-item").first().click();
  await page.locator('.main-workspace[aria-busy="false"]').waitFor();
  const nav = page.getByRole("navigation", { name: "Workspace navigation" });
  const pick = (symbol) =>
    page
      .locator(".company-row .watch-item")
      .filter({ has: page.locator(`strong[title="${symbol}"]`) });
  const ready = () =>
    page.locator('.main-workspace[aria-busy="false"]').waitFor();
  for (const symbol of ["AVGO", "FN", "NVDA"]) {
    const avatar = pick(symbol).locator(".company-avatar.has-logo");
    await avatar.waitFor();
    const bundledSrc = await avatar.locator("img").getAttribute("src");
    assert.ok(
      bundledSrc.startsWith(`/assets/${symbol}-`) ||
        bundledSrc.startsWith("data:image/png;base64,"),
    );
    assert.ok(
      await avatar
        .locator("img")
        .evaluate((e) => e.complete && e.naturalWidth > 0),
    );
    assert.equal(
      await avatar
        .locator("img")
        .evaluate((e) => getComputedStyle(e).objectFit),
      "contain",
    );
    await pick(symbol).click();
    await ready();
    await page
      .locator(".company-header .company-avatar.has-logo img")
      .waitFor();
    assert.equal(
      await page
        .locator(".company-header .company-avatar img")
        .getAttribute("src"),
      bundledSrc,
    );
  }
  await pick("AVGO").click();
  await ready();
  await page
    .locator(".watchlist")
    .screenshot({ path: path.join(evidence, "company-logos.png") });
  await page.screenshot({ path: path.join(evidence, "workspace-1440.png") });
  for (const label of ["My ideas", "Updates", "History"]) {
    await nav.getByRole("button", { name: label, exact: true }).click();
    if (label === "Updates")
      await page
        .locator(".update-inbox .market-section-head button:not(:disabled)")
        .waitFor();
    assert.equal(
      await page.locator(".panel-toggle-right").count(),
      0,
      `${label} omits idea toggle`,
    );
    assert.equal(await page.locator(".idea-panel").getAttribute("inert"), "");
    assert.equal(
      await page.locator(".idea-panel").getAttribute("aria-hidden"),
      "true",
    );
    assert.equal(
      await page
        .locator(".main-workspace")
        .evaluate((e) => e.getBoundingClientRect().right),
      1440,
    );
    assert.equal(
      await page.evaluate(
        () => JSON.parse(localStorage.getItem("thesis.layout")).ideaHidden,
      ),
      false,
      "view change preserves open preference",
    );
    await page.screenshot({
      path: path.join(
        evidence,
        `${label.replaceAll(" ", "-").toLowerCase()}-1440.png`,
      ),
    });
    await nav.getByRole("button", { name: "Workspace", exact: true }).click();
    assert.equal(
      await page
        .getByRole("button", { name: "Hide idea sidebar", exact: true })
        .count(),
      1,
    );
    assert.equal(await page.locator(".idea-panel").getAttribute("inert"), null);
  }
  await page
    .getByRole("button", { name: "Hide idea sidebar", exact: true })
    .click();
  await nav.getByRole("button", { name: "My ideas", exact: true }).click();
  await nav.getByRole("button", { name: "Workspace", exact: true }).click();
  assert.equal(
    await page
      .getByRole("button", { name: "Show idea sidebar", exact: true })
      .count(),
    1,
  );
  assert.equal(await page.locator(".idea-panel").getAttribute("inert"), "");
  await page.reload();
  await ready();
  assert.equal(
    await page
      .getByRole("button", { name: "Show idea sidebar", exact: true })
      .count(),
    1,
  );
  await page
    .getByRole("button", { name: "Show idea sidebar", exact: true })
    .click();
  for (const width of [1920, 1440, 1024, 980, 768, 600, 390, 320]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const label of ["Workspace", "My ideas", "Updates", "History"]) {
      await nav.getByRole("button", { name: label, exact: true }).click();
      if (label === "Updates")
        await page
          .locator(".update-inbox .market-section-head button:not(:disabled)")
          .waitFor();
      const geometry = await page.evaluate(() => {
        const main = document.querySelector(".main-workspace"),
          idea = document.querySelector(".idea-panel");
        return {
          width: innerWidth,
          documentWidth: document.documentElement.scrollWidth,
          mainWidth: main.scrollWidth,
          mainClient: main.clientWidth,
          ideaHidden: idea.hasAttribute("inert"),
          ideaHeight: idea.getBoundingClientRect().height,
          footerCount: document.querySelectorAll("footer").length,
        };
      });
      assert.ok(
        geometry.documentWidth <= width,
        `document overflow ${width} ${label}`,
      );
      assert.ok(
        geometry.mainWidth <= geometry.mainClient + 1,
        `main overflow ${width} ${label}`,
      );
      assert.equal(geometry.ideaHidden, label !== "Workspace");
      assert.equal(geometry.footerCount, 0);
      assert.equal(
        await page.locator(".panel-toggle-right").count(),
        label === "Workspace" ? 1 : 0,
      );
      if (width <= 740 && label !== "Workspace")
        assert.ok(
          geometry.ideaHeight <= 1,
          `phone sidebar removes height ${label}`,
        );
      checks.push({ view: label, ...geometry });
      if (width === 390 && label === "My ideas")
        await page.screenshot({
          path: path.join(evidence, "my-ideas-390.png"),
        });
    }
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  await nav.getByRole("button", { name: "Workspace", exact: true }).click();
  await page
    .getByRole("button", { name: "All companies", exact: true })
    .click();
  await ready();
  assert.equal(await page.locator(".panel-toggle-right").count(), 0);
  assert.equal(
    await page
      .locator(".idea-panel")
      .evaluate((e) => getComputedStyle(e).display),
    "none",
  );
  await pick("AVGO").click();
  await ready();
  injectFixtures = true;
  await page.reload();
  await ready();
  await page.waitForFunction(() => {
    const label = document.querySelector('.watch-item strong[title="ZZZZZ"]');
    const avatar = label?.closest("button").querySelector(".company-avatar");
    return avatar && !avatar.querySelector("img");
  });
  const unavailable = pick("ZZZZZ").locator(".company-avatar");
  assert.equal((await unavailable.textContent()).trim(), "U");
  assert.equal(await unavailable.locator("img").count(), 0);
  assert.equal(
    await pick("NSTR").locator("img").count(),
    0,
    "fictional company makes no logo request",
  );
  fs.writeFileSync(
    path.join(evidence, "fallback-observation.json"),
    JSON.stringify(
      {
        mockedLogoFailures,
        external,
        writes,
        avatars: await page.locator(".company-row").evaluateAll((rows) =>
          rows.map((row) => ({
            symbol: row.querySelector("strong").textContent,
            avatar: row.querySelector(".company-avatar").outerHTML,
          })),
        ),
      },
      null,
      2,
    ),
  );
  assert.ok(mockedLogoFailures > 0);
  assert.deepEqual(errors, []);
  assert.deepEqual(external, []);
  assert.deepEqual(writes, []);
  fs.writeFileSync(
    path.join(evidence, "verification.json"),
    JSON.stringify(
      { checks, mockedLoading, mockedLogoFailures, errors, external, writes },
      null,
      2,
    ),
  );
  console.log(
    "Three real bundled logos/header switching, missing-logo fallback, fictional exclusion, Workspace-only idea sidebar, preserved preferences and 32 responsive view checks passed. Loading and missing-logo responses are mocked; no app writes or external requests.",
  );
})()
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  })
  .finally(async () => {
    await browser?.close();
  });
