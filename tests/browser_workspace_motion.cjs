// Read-only local app check. Loading responses and one long company label are
// authored UI fixtures; no provider calls or application writes reach the server.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const evidence =
  process.env.THESIS_MOTION_EVIDENCE || "/private/tmp/thesis-motion";
const base = process.env.THESIS_TEST_URL || "http://127.0.0.1:8841";
const longName =
  "Example International Semiconductor and Computing Systems Corporation";
const run = {
  active: false,
  steps: ["News", "Filings", "Discussions"].map((label) => ({
    key: label.toLowerCase(),
    label,
    status: "ready",
    message: "Authored completed UI step",
  })),
};
let browser;
(async () => {
  fs.mkdirSync(evidence, { recursive: true });
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_PATH,
  });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
    reducedMotion: "no-preference",
  });
  const errors = [],
    external = [],
    blockedWrites = [],
    mockedLoading = [],
    transitions = [],
    layouts = [];
  let stressCatalogue = false,
    emptyWorkspace = false;
  page.on("pageerror", (e) => errors.push(e.message));
  await page.route("**/*", async (route) => {
    const request = route.request(),
      url = new URL(request.url());
    if (!["127.0.0.1", "localhost"].includes(url.hostname)) {
      external.push(url.hostname);
      return route.abort();
    }
    if (/\/companies\/[^/]+\/loading$/.test(url.pathname)) {
      mockedLoading.push(request.method());
      return route.fulfill({ json: { result: run } });
    }
    if (url.pathname === "/api/v1/company-directory")
      return route.fulfill({ json: { result: { companies: [] } } });
    if (request.method() !== "GET") {
      blockedWrites.push(url.pathname);
      return route.abort();
    }
    if (url.pathname === "/api/v1/workspace") {
      const response = await route.fetch();
      const packet = await response.json();
      if (packet.result?.catalogue?.length > 1)
        packet.result.catalogue[1].name = longName;
      if (stressCatalogue)
        for (let i = 0; i < 30; i++)
          packet.result.catalogue.push({
            ...packet.result.catalogue[0],
            id: `bbbbbbbb-bbbb-4bbb-8bbb-${String(i).padStart(12, "0")}`,
            symbol: `FIX${i}`,
            name: `Authored long-list company ${i}`,
            mode: "recorded",
            unread: 0,
          });
      if (emptyWorkspace) packet.result = { empty: true };
      return route.fulfill({ response, json: packet });
    }
    return route.continue();
  });
  await page.goto(base + "/?view=workspace");
  await page.locator(".company-row").first().waitFor();
  await page.locator(".company-row .watch-item").first().click();
  await page.locator('.main-workspace[aria-busy="false"]').waitFor();
  await page.evaluate(() => document.fonts.ready);
  await page
    .getByRole("button", { name: "Hide research progress", exact: true })
    .waitFor();
  await page.waitForTimeout(400);
  assert.equal(await page.locator("footer").count(), 0);
  assert.equal(await page.locator(".topbar .panel-toggle-left").count(), 0);
  const bottomControl = () =>
    page.locator(".panel-toggle-left").evaluate((button) => {
      const panel = button.closest(".watchlist");
      return {
        gap:
          panel.getBoundingClientRect().bottom -
          button.getBoundingClientRect().bottom,
        viewportGap: innerHeight - button.getBoundingClientRect().bottom,
      };
    });
  assert.ok((await bottomControl()).gap <= 16);
  assert.equal(
    (await page.locator(".watchlist .add-company").textContent()).trim(),
    "",
  );
  const row = page.locator(".company-row.selected");
  const rowStyle = () =>
    row.evaluate((e) => ({
      background: getComputedStyle(e).backgroundColor,
      children: [...e.querySelectorAll("button")].map(
        (b) => getComputedStyle(b).backgroundColor,
      ),
      rightSpace:
        e.getBoundingClientRect().right -
        e.querySelector(".remove-company").getBoundingClientRect().right,
    }));
  await row.locator(".watch-item").hover();
  await page.waitForTimeout(170);
  const leftHover = await rowStyle();
  assert.equal(leftHover.background, "rgb(27, 39, 33)");
  assert.deepEqual(leftHover.children, [
    "rgba(0, 0, 0, 0)",
    "rgba(0, 0, 0, 0)",
  ]);
  assert.ok(leftHover.rightSpace >= 8);
  await page
    .locator(".watchlist")
    .screenshot({ path: path.join(evidence, "company-hover.png") });
  await row.locator(".remove-company").hover();
  await page.waitForTimeout(170);
  assert.deepEqual(await rowStyle(), leftHover);
  await page
    .locator(".watchlist")
    .screenshot({ path: path.join(evidence, "cross-hover.png") });
  const label = page
    .locator(".company-row-label small")
    .filter({ hasText: longName });
  const truncation = await label.evaluate((e) => ({
    overflow: getComputedStyle(e).overflow,
    ellipsis: getComputedStyle(e).textOverflow,
    client: e.clientWidth,
    scroll: e.scrollWidth,
    title: e.title,
  }));
  assert.equal(truncation.ellipsis, "ellipsis");
  assert.equal(truncation.overflow, "hidden");
  assert.ok(truncation.scroll > truncation.client);
  assert.equal(truncation.title, longName);
  await page.evaluate(() => {
    window.motionNodes = [
      ".watchlist",
      ".idea-panel",
      ".research-loading",
      ".company-search input",
    ].map((s) => document.querySelector(s));
  });
  const sample = () =>
    page.evaluate(async () => {
      const values = [],
        start = performance.now();
      do {
        await new Promise(requestAnimationFrame);
        const main = document
          .querySelector(".main-workspace")
          .getBoundingClientRect();
        values.push({
          x: main.x,
          right: main.right,
          progress: document
            .querySelector(".research-loading-collapse")
            .getBoundingClientRect().height,
        });
      } while (performance.now() - start < 350);
      return values;
    });
  await page.getByPlaceholder("Name or symbol").fill("AV");
  for (const [side, labelText, coordinate] of [
    ["companies", "company", "x"],
    ["idea", "idea", "right"],
  ]) {
    const before = await sample();
    await page
      .getByRole("button", {
        name: `${side === "companies" ? "Collapse" : "Hide"} ${labelText} sidebar`,
        exact: true,
      })
      .click();
    const closing = await sample();
    const start = before.at(-1)[coordinate],
      end = closing.at(-1)[coordinate];
    assert.ok(
      closing.some(
        (v) =>
          v[coordinate] > Math.min(start, end) + 1 &&
          v[coordinate] < Math.max(start, end) - 1,
      ),
      `${side} closing interpolates`,
    );
    const panel = page.locator(
      side === "companies" ? ".watchlist" : ".idea-panel",
    );
    assert.equal(
      await panel.getAttribute("inert"),
      side === "companies" ? null : "",
    );
    assert.equal(
      await panel.evaluate((e) => getComputedStyle(e).visibility),
      side === "companies" ? "visible" : "hidden",
    );
    if (side === "companies") {
      assert.equal(end, 64);
      assert.equal(await page.locator(".company-row").count(), 3);
      assert.equal(
        await page.locator(".company-sidebar-browse").getAttribute("inert"),
        "",
      );
      assert.ok(
        await page.locator(".company-row .company-avatar").first().isVisible(),
      );
      assert.equal(
        await page.locator(".company-row-label").first().isVisible(),
        false,
      );
      assert.equal(
        await page.locator(".remove-company").first().isVisible(),
        false,
      );
      const second = page.locator(".company-row .watch-item").nth(1);
      await second.focus();
      await second.press("Enter");
      await page.locator('.main-workspace[aria-busy="false"]').waitFor();
      assert.equal(await second.getAttribute("aria-pressed"), "true");
      await page.locator(".company-row .watch-item").first().click();
      await page.locator('.main-workspace[aria-busy="false"]').waitFor();
      assert.equal(
        await page.evaluate(() =>
          window.motionNodes
            .filter((_, index) => index !== 2)
            .every((element) => element.isConnected),
        ),
        true,
      );
      // Progress is scoped to the selected company and remounts during navigation.
      // Pin the new scope before checking its subsequent collapse/restore behavior.
      await page.evaluate(() => {
        window.motionNodes[2] = document.querySelector(".research-loading");
      });
      await page.locator(".watchlist .add-company").click();
      await page
        .getByRole("dialog", { name: "Add a company", exact: true })
        .waitFor();
      await page.locator("#company-lookup").press("Escape");
      assert.equal(await page.getByRole("dialog").count(), 0);
      assert.ok((await bottomControl()).gap <= 16);
      await page.screenshot({ path: path.join(evidence, "compact-1440.png") });
    }
    await page
      .getByRole("button", {
        name: `${side === "companies" ? "Expand" : "Show"} ${labelText} sidebar`,
        exact: true,
      })
      .click();
    const opening = await sample();
    assert.ok(
      opening.some(
        (v) =>
          v[coordinate] > Math.min(start, end) + 1 &&
          v[coordinate] < Math.max(start, end) - 1,
      ),
      `${side} opening interpolates`,
    );
    assert.ok(Math.abs(opening.at(-1)[coordinate] - start) <= 1);
    transitions.push({ side, closing, opening });
  }
  assert.equal(
    await page.getByPlaceholder("Name or symbol").inputValue(),
    "AV",
  );
  await page.getByPlaceholder("Name or symbol").fill("");
  await page
    .getByRole("button", { name: "View progress", exact: true })
    .click();
  await page.waitForTimeout(350);
  const beforeProgress = (await sample()).at(-1).progress;
  await page
    .getByRole("button", { name: "Hide research progress", exact: true })
    .press("Enter");
  assert.equal(
    await page
      .locator(".progress-restore")
      .evaluate((e) => e === document.activeElement),
    true,
  );
  const closingProgress = await sample();
  assert.ok(
    closingProgress.some(
      (v) => v.progress > 1 && v.progress < beforeProgress - 1,
    ),
  );
  assert.equal(closingProgress.at(-1).progress, 0);
  assert.equal(
    await page.locator(".research-loading-collapse").getAttribute("inert"),
    "",
  );
  await page.locator(".progress-restore").press("Enter");
  assert.equal(
    await page
      .locator(".collapse-progress")
      .evaluate((e) => e === document.activeElement),
    true,
  );
  const openingProgress = await sample();
  assert.ok(
    openingProgress.some(
      (v) => v.progress > 1 && v.progress < beforeProgress - 1,
    ),
  );
  assert.equal(
    await page
      .getByRole("button", { name: "Hide details", exact: true })
      .getAttribute("aria-expanded"),
    "true",
  );
  transitions.push({
    side: "progress",
    closing: closingProgress,
    opening: openingProgress,
  });
  assert.equal(
    await page.evaluate(() => window.motionNodes.every((e) => e.isConnected)),
    true,
  );
  // Reverse a transition before it finishes; no delayed hide may win afterwards.
  await page.locator(".panel-toggle-left").click();
  await page.locator(".panel-toggle-left").click();
  await page.waitForTimeout(350);
  assert.equal(
    await page.locator(".watchlist").getAttribute("aria-hidden"),
    null,
  );
  assert.equal(
    await page
      .locator(".watchlist")
      .evaluate((e) => getComputedStyle(e).visibility),
    "visible",
  );
  await page.emulateMedia({ reducedMotion: "reduce" });
  assert.equal(
    await page
      .locator(".workspace-grid")
      .evaluate((e) => getComputedStyle(e).transitionDuration),
    "0s",
  );
  await page
    .getByRole("button", { name: "Collapse company sidebar", exact: true })
    .click();
  assert.equal(
    await page
      .locator(".main-workspace")
      .evaluate((e) => e.getBoundingClientRect().x),
    64,
  );
  await page
    .getByRole("button", { name: "Expand company sidebar", exact: true })
    .click();
  for (const width of [2048, 1920, 1440, 1024, 980, 768, 740, 600, 390, 320]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const hidden of [true, false]) {
      await page.locator(".panel-toggle-right").click();
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
        };
      });
      assert.equal(geometry.ideaHidden, hidden);
      assert.ok(geometry.documentWidth <= width, `document overflow ${width}`);
      assert.ok(
        geometry.mainWidth <= geometry.mainClient + 1,
        `main overflow ${width}`,
      );
      if (width > 980 && !hidden) {
        const panelWidths = await page.evaluate(() =>
          [".watchlist", ".idea-panel"].map((selector) => {
            const panel = document.querySelector(selector);
            return {
              panel: panel.clientWidth,
              body: panel.querySelector(".sidebar-body").getBoundingClientRect()
                .width,
            };
          }),
        );
        assert.ok(
          panelWidths.every((w) => Math.abs(w.panel - w.body) <= 1),
          `sidebar body follows responsive rail ${width}`,
        );
      }
      if (width <= 740 && hidden)
        assert.ok(geometry.ideaHeight <= 1, `phone idea collapse ${width}`);
      layouts.push(geometry);
    }
    if (width === 1440 || width === 390)
      await page.screenshot({
        path: path.join(evidence, `workspace-${width}.png`),
      });
    if (width === 1024)
      await page.locator(".watchlist").screenshot({
        path: path.join(evidence, "sidebar-1024.png"),
      });
    if (width > 980) {
      await page
        .getByRole("button", { name: "Collapse company sidebar", exact: true })
        .click();
      const compactGeometry = await page.evaluate(() => ({
        width: innerWidth,
        documentWidth: document.documentElement.scrollWidth,
        mainX: document.querySelector(".main-workspace").getBoundingClientRect()
          .x,
      }));
      assert.equal(compactGeometry.mainX, 64);
      assert.ok(compactGeometry.documentWidth <= width);
      assert.ok((await bottomControl()).gap <= 16);
      layouts.push({ compact: true, ...compactGeometry });
      if (width === 1024 || width === 1920)
        await page.screenshot({
          path: path.join(evidence, `compact-${width}.png`),
        });
      await page
        .getByRole("button", { name: "Expand company sidebar", exact: true })
        .click();
    }
  }
  // Mobile uses height animation for the idea panel.
  await page.emulateMedia({ reducedMotion: "no-preference" });
  const phoneBefore = await page
    .locator(".idea-panel")
    .evaluate((e) => e.getBoundingClientRect().height);
  await page.locator(".panel-toggle-right").click();
  const phoneHeights = await page.evaluate(async () => {
    const values = [],
      start = performance.now();
    do {
      await new Promise(requestAnimationFrame);
      values.push(
        document.querySelector(".idea-panel").getBoundingClientRect().height,
      );
    } while (performance.now() - start < 350);
    return values;
  });
  assert.ok(phoneHeights.some((h) => h > 2 && h < phoneBefore - 1));
  assert.ok(phoneHeights.at(-1) <= 1);
  await page.locator(".panel-toggle-right").click();
  await page.waitForTimeout(350);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  // Both panels can collapse together while the company logo rail stays available.
  await page
    .getByRole("button", { name: "Collapse company sidebar", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Hide idea sidebar", exact: true })
    .click();
  assert.deepEqual(
    await page.locator(".main-workspace").evaluate((e) => ({
      x: e.getBoundingClientRect().x,
      width: e.getBoundingClientRect().width,
    })),
    { x: 64, width: 1376 },
  );
  await page
    .getByRole("button", { name: "Expand company sidebar", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Show idea sidebar", exact: true })
    .click();
  await page
    .getByRole("button", { name: "All companies", exact: true })
    .click();
  await page.locator('.main-workspace[aria-busy="false"]').waitFor();
  assert.equal(
    await page
      .locator(".idea-panel")
      .evaluate((e) => getComputedStyle(e).display),
    "none",
  );
  assert.equal(
    await page
      .locator(".main-workspace")
      .evaluate((e) => e.getBoundingClientRect().right),
    1440,
  );
  await page.locator(".company-row .watch-item").first().click();
  await page.locator('.main-workspace[aria-busy="false"]').waitFor();
  await page
    .getByRole("button", { name: "Hide research progress", exact: true })
    .waitFor();
  await page
    .getByRole("button", { name: "Collapse company sidebar", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Hide research progress", exact: true })
    .click();
  await page.reload();
  await page.locator('.main-workspace[aria-busy="false"]').waitFor();
  assert.equal(await page.locator(".watchlist").getAttribute("inert"), null);
  assert.equal(
    await page.locator(".watchlist").getAttribute("data-collapsed"),
    "true",
  );
  assert.equal(
    await page.locator(".research-loading-collapse").getAttribute("inert"),
    "",
  );
  assert.equal(await page.locator(".idea-panel").getAttribute("inert"), null);
  stressCatalogue = true;
  await page.reload();
  await page.locator('.main-workspace[aria-busy="false"]').waitFor();
  await page
    .getByRole("button", { name: "Expand company sidebar", exact: true })
    .click();
  const stressBefore = await bottomControl();
  const listScroll = await page
    .locator(".company-sidebar-content")
    .evaluate((element) => {
      element.scrollTop = element.scrollHeight;
      return {
        height: element.clientHeight,
        scroll: element.scrollHeight,
        top: element.scrollTop,
      };
    });
  assert.ok(listScroll.scroll > listScroll.height && listScroll.top > 0);
  assert.deepEqual(await bottomControl(), stressBefore);
  assert.ok(stressBefore.gap <= 16 && stressBefore.viewportGap <= 16);
  await page.locator(".watchlist .add-company").click();
  await page
    .getByRole("dialog", { name: "Add a company", exact: true })
    .waitFor();
  await page.locator("#company-lookup").press("Escape");
  await page.screenshot({
    path: path.join(evidence, "long-list-controls.png"),
  });
  emptyWorkspace = true;
  await page.reload();
  await page.locator(".empty-workspace").waitFor();
  assert.equal(await page.locator("footer").count(), 0);
  assert.deepEqual(errors, []);
  assert.deepEqual(external, []);
  assert.deepEqual(blockedWrites, []);
  fs.writeFileSync(
    path.join(evidence, "verification.json"),
    JSON.stringify(
      {
        leftHover,
        truncation,
        transitions,
        phoneHeights,
        layouts,
        errors,
        external,
        blockedWrites,
        mockedLoading,
        stressBefore,
        listScroll,
      },
      null,
      2,
    ),
  );
  console.log(
    "Company logo rail navigation, bottom controls with long-list scrolling, plus-only Add dialog, footer removal including the empty workspace, shared hover/ellipsis, reversible panel/progress motion, retained controls, keyboard focus, reduced motion, persistence and ten viewport widths passed. Loading, directory and catalogue fixtures are authored; no app writes or external requests.",
  );
})()
  .catch((e) => {
    console.error(e);
    process.exitCode = 1;
  })
  .finally(async () => {
    await browser?.close();
  });
