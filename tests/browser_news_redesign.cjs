// Standalone authored UI checks; builds a fixture and serves static files only.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs/promises"),
  path = require("node:path"),
  os = require("node:os"),
  http = require("node:http");
let browser, server, temp;
(async () => {
  const root = path.resolve(__dirname, ".."),
    frontend = path.join(root, "frontend");
  const { build } = await import(
    path.join(frontend, "node_modules/vite/dist/node/index.js")
  );
  const { default: react } = await import(
    path.join(frontend, "node_modules/@vitejs/plugin-react/dist/index.js")
  );
  temp = await fs.mkdtemp(path.join(os.tmpdir(), "fledge-news-ui-"));
  await fs.writeFile(
    path.join(temp, "index.html"),
    `<html lang="en"><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body><div id="root"></div><script type="module" src="${path.join(root, "tests/ui/news-redesign.jsx")}"></script></body></html>`,
  );
  await build({
    root: temp,
    configFile: false,
    plugins: [react()],
    resolve: {
      alias: {
        react: path.join(frontend, "node_modules/react"),
        "react-dom": path.join(frontend, "node_modules/react-dom"),
      },
    },
    build: { outDir: path.join(temp, "dist"), chunkSizeWarningLimit: 1000 },
    logLevel: "error",
  });
  server = http.createServer(async (req, res) => {
    try {
      const filename = path.join(
        temp,
        "dist",
        new URL(req.url, "http://localhost").pathname,
      );
      const file = filename.endsWith(path.sep)
        ? path.join(filename, "index.html")
        : filename;
      res.setHeader(
        "Content-Type",
        file.endsWith(".css")
          ? "text/css"
          : file.endsWith(".js")
            ? "text/javascript"
            : "text/html",
      );
      res.end(await fs.readFile(file));
    } catch {
      res.writeHead(404);
      res.end();
    }
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_PATH,
  });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1100 },
    reducedMotion: "reduce",
  });
  const errors = [],
    requests = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.route("**/*", (route) => {
    if (
      !route.request().url().startsWith(base) ||
      route.request().url().includes("/api/")
    ) {
      requests.push(route.request().url());
      return route.abort();
    }
    return route.continue();
  });
  await page.goto(base);
  await page.addStyleTag({
    content: "html { scroll-behavior: auto !important; }",
  });
  await page
    .getByRole("heading", { name: "What’s the tone?", exact: true })
    .waitFor();
  const tabs = page.getByRole("tablist", { name: "Research views" });
  const selected = () => tabs.locator('[aria-selected="true"]');
  const checkSelected = async (name) => {
    assert.equal(await selected().count(), 1);
    assert.equal(await selected().textContent(), name);
    assert.equal(
      await page.getByRole("tabpanel").getAttribute("aria-labelledby"),
      await selected().getAttribute("id"),
    );
  };
  for (const width of [1440, 1024, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 1100 });
    await tabs.getByRole("tab", { name: "Overview", exact: true }).click();
    await checkSelected("Overview");
    await page.keyboard.press("ArrowRight");
    await checkSelected("Financials");
    await page.keyboard.press("End");
    await checkSelected("Compare & value");
    await page.keyboard.press("ArrowRight");
    await checkSelected("Summary");
    await page.keyboard.press("Home");
    await checkSelected("Summary");
    await tabs
      .getByRole("tab", { name: "News & discussion", exact: true })
      .click();
    await checkSelected("News & discussion");
    await page.keyboard.press("Tab");
    assert.equal(
      await page.evaluate(() => document.activeElement.id),
      "research-panel",
    );
    assert.equal(
      await tabs.evaluate((el) => getComputedStyle(el).flexDirection),
      "row",
    );
    assert.equal(
      await selected().evaluate((el) => getComputedStyle(el).backgroundColor),
      "rgba(0, 0, 0, 0)",
    );
    assert.equal(
      await selected().evaluate((el) => getComputedStyle(el, "::after").height),
      "2px",
    );
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      true,
      `No page overflow at ${width}`,
    );
    assert.equal(
      await tabs.evaluate((el) => {
        const b = el
            .querySelector('[aria-selected="true"]')
            .getBoundingClientRect(),
          l = el.getBoundingClientRect();
        return b.left >= l.left - 1 && b.right <= l.right + 1;
      }),
      true,
    );
  }
  await page.setViewportSize({ width: 1440, height: 1100 });
  const panel = page.getByRole("region", {
    name: "News and social sentiment",
    exact: true,
  });
  await panel
    .getByRole("button", { name: "Company news", exact: true })
    .click();
  await panel.locator(".sentiment-source-list > summary").click();
  assert.equal(await panel.locator(".source-story").count(), 6);
  await panel
    .getByRole("button", { name: "Next sources", exact: true })
    .click();
  assert.equal(await panel.locator(".source-story").count(), 4);
  const sourceText = await panel
    .locator(".story-source-text")
    .first()
    .textContent();
  await panel
    .getByRole("button", { name: "Inspect evidence", exact: true })
    .first()
    .click();
  const dialog = page.getByRole("dialog", {
    name: "Story evidence",
    exact: true,
  });
  await dialog.waitFor();
  assert.equal(
    await dialog.locator(".story-full-text p").textContent(),
    sourceText,
  );
  await page.keyboard.press("Escape");
  assert.equal(await page.getByRole("dialog").count(), 0);
  assert.match(
    await page.evaluate(() => document.activeElement.textContent),
    /Inspect evidence/,
  );
  await tabs.getByRole("tab", { name: "Overview", exact: true }).click();
  await tabs
    .getByRole("tab", { name: "News & discussion", exact: true })
    .click();
  assert.match(
    await panel.locator(".sentiment-pagination").textContent(),
    /Page 2 of 2/,
  );
  assert.equal(
    await panel
      .getByRole("button", { name: "Company news", exact: true })
      .getAttribute("aria-pressed"),
    "true",
  );
  assert.equal(
    await panel.locator(".sentiment-source-list").getAttribute("open"),
    "",
  );
  await panel.getByRole("button", { name: /^Negative/ }).click();
  assert.equal(await panel.locator(".source-story").count(), 4);
  // Save screenshots with the default All sources view.
  await panel.getByRole("button", { name: "All tones", exact: true }).click();
  await panel.getByRole("button", { name: "All sources", exact: true }).click();
  await panel.locator(".sentiment-source-list > summary").click();
  const screenshots = path.join(
    root,
    "docs/reviews/2026-10-25/news-screenshots",
  );
  await fs.mkdir(screenshots, { recursive: true });
  for (const width of [1440, 390, 320]) {
    await page.setViewportSize({ width, height: 1100 });
    await page.waitForFunction(() => {
      const list = document.querySelector('[aria-label="Research views"]');
      const item = list
        .querySelector('[aria-selected="true"]')
        .getBoundingClientRect();
      const box = list.getBoundingClientRect();
      return item.left >= box.left - 1 && item.right <= box.right + 1;
    });
    await page.evaluate(async () => {
      document.querySelectorAll("*").forEach((el) => {
        if (el.scrollTop) el.scrollTop = 0;
      });
      scrollTo({ top: 0, behavior: "instant" });
      await new Promise((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(resolve)),
      );
    });
    await page.screenshot({
      path: path.join(screenshots, `news-${width}.png`),
      fullPage: false,
    });
  }
  for (const state of ["empty", "withheld", "stale"]) {
    await page.getByLabel("Fixture state").selectOption(state);
    if (state === "empty") {
      assert.match(await panel.textContent(), /Tone analysis is not available/);
      assert.equal(await page.locator(".development-card").count(), 0);
    }
    if (state === "withheld") {
      assert.match(
        await panel.textContent(),
        /withheld because source access changed/,
      );
      assert.equal(await panel.locator(".source-story").count(), 0);
    }
    if (state === "stale") {
      assert.match(await panel.textContent(), /over 24 hours ago/);
      assert.match(await panel.textContent(), /some news sources unavailable/);
    }
    assert.equal(
      await panel
        .getByRole("button", { name: "Refresh & analyse", exact: true })
        .isDisabled(),
      true,
    );
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      true,
      `${state} state overflow`,
    );
  }
  assert.deepEqual(errors, []);
  assert.deepEqual(requests, []);
  console.log(
    "PASS: line tabs at 5 widths, keyboard/focus, selected visibility, retained filters/paging, original evidence, empty/withheld/stale states; zero API/external requests or browser errors.",
  );
})()
  .catch((e) => {
    console.error(e);
    process.exitCode = 1;
  })
  .finally(async () => {
    if (browser) await browser.close();
    if (server) await new Promise((resolve) => server.close(resolve));
    if (temp) await fs.rm(temp, { recursive: true, force: true });
  });
