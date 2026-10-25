// Actual recap UI, authored data, controlled promises and zero HTTP requests.
import assert from "node:assert/strict";
import { mkdtemp, readFile, writeFile, mkdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const frontend = path.join(root, "frontend");
const require = createRequire(path.join(frontend, "package.json"));
const { build } = await import(pathToFileURL(require.resolve("vite")));
const { default: react } = await import(
  pathToFileURL(require.resolve("@vitejs/plugin-react"))
);
const { chromium } = await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE));
const out = await mkdtemp(path.join(tmpdir(), "fledge-reading-pages-"));
const entry = path.join(out, "fixture.jsx");
await writeFile(
  entry,
  (
    await readFile(path.join(root, "tests/ui/reading-pages.jsx"), "utf8")
  ).replaceAll("../../frontend/", frontend + "/"),
);
await build({
  configFile: false,
  root: frontend,
  plugins: [react()],
  logLevel: "error",
  define: { "process.env.NODE_ENV": JSON.stringify("production") },
  resolve: {
    alias: {
      react: path.join(frontend, "node_modules/react"),
      "react-dom": path.join(frontend, "node_modules/react-dom"),
    },
  },
  build: {
    outDir: out,
    emptyOutDir: false,
    lib: {
      entry,
      name: "Fixture",
      formats: ["iife"],
      fileName: () => "fixture.js",
    },
    cssCodeSplit: false,
    minify: false,
  },
});
const js = await readFile(path.join(out, "fixture.js"), "utf8");
const css = await readFile(path.join(out, "fledge.css"), "utf8");
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.CHROMIUM_PATH,
});
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const screenshots = path.join(
  root,
  "docs/reviews/2026-10-25/reading-pages-screenshots",
);
await mkdir(screenshots, { recursive: true });
const errors = [],
  requests = [];
page.on("pageerror", (e) => errors.push(e.message));
await page.route("**/*", (route) => {
  requests.push(route.request().url());
  return route.abort();
});
try {
  await page.setContent(
    '<meta charset="utf-8"><style>' + css + '</style><div id="root"></div>',
  );
  await page.addScriptTag({ content: js });
  const world = page.getByRole("region", { name: "World news", exact: true });
  await world
    .getByRole("heading", { name: "World news", exact: true })
    .waitFor();
  await world.locator(".world-news-item").first().waitFor();
  assert.equal(await world.locator(".world-news-item").count(), 3);
  const filters = world.getByRole("group", { name: "Filter headlines" });
  await filters.getByRole("button", { name: /^About my companies/ }).click();
  assert.equal(await world.locator(".world-news-item").count(), 2);
  await filters.getByRole("button", { name: /^Trade/ }).click();
  assert.equal(await world.locator(".world-news-item").count(), 1);
  await filters.getByRole("button", { name: /^Regulation/ }).click();
  await world
    .getByRole("heading", { name: "No headlines in this view", exact: true })
    .waitFor();
  await world
    .getByRole("button", { name: "Show all headlines", exact: true })
    .click();
  assert.equal(await world.locator(".world-news-item").count(), 3);
  assert.equal(
    await world
      .locator(".world-news-item img, .world-news-item script")
      .count(),
    0,
  );
  assert.match(
    await world.locator(".world-news-summary").first().textContent(),
    /<script>untrusted<\/script>/,
  );
  assert.equal(
    await world
      .getByRole("button", { name: "Check against my watchlist", exact: true })
      .isDisabled(),
    true,
  );
  for (const width of [1440, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 1100 });
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      `World overflow at ${width}`,
    );
    await page.mouse.move(0, 0);
    await page.screenshot({
      path: path.join(screenshots, `world-${width}.png`),
    });
  }
  await page.evaluate(() => window.show("world", { ai: true }));
  await world
    .getByRole("button", { name: "Check against my watchlist", exact: true })
    .click();
  await page.waitForFunction(() =>
    window.actions.some((a) => a.kind === "world-check"),
  );
  assert.equal(
    (await page.evaluate(() => window.actions)).filter(
      (a) => a.kind === "world-check",
    ).length,
    1,
  );
  await page.evaluate(() => window.options({ refreshError: true }));
  await world.getByRole("button", { name: "Refresh", exact: true }).click();
  await world
    .getByRole("alert")
    .filter({ hasText: "Authored refresh failure." })
    .waitFor();
  assert.equal(await world.locator(".world-news-item").count(), 3);
  await page.evaluate(() =>
    window.show("world", { beginner: true, configured: false }),
  );
  await world
    .getByText("Showing saved headlines. New headlines are unavailable.", {
      exact: true,
    })
    .waitFor();
  assert.equal(
    await world
      .getByRole("button", { name: "Check against my watchlist", exact: true })
      .count(),
    0,
  );
  await page.evaluate(() => window.show("world", { empty: true }));
  await world
    .getByRole("heading", { name: "No world headlines yet", exact: true })
    .waitFor();
  await page.evaluate(() => window.show("world", { error: true }));
  await world
    .getByRole("heading", { name: "World news unavailable", exact: true })
    .waitFor();
  await page.evaluate(() => window.options({ error: false }));
  await world.getByRole("button", { name: "Try again", exact: true }).click();
  await world.locator(".world-news-item").first().waitFor();
  await page.evaluate(() => window.show("updates"));
  const inbox = page.getByRole("region", {
    name: "Research update inbox",
    exact: true,
  });
  await inbox.getByText("Page 1 of 2", { exact: true }).waitFor();
  assert.equal(await inbox.locator(".inbox-record").count(), 2);
  assert.equal(
    (await page.evaluate(() => window.actions)).filter(
      (a) =>
        a.kind === "review" || a.kind === "rate" || a.kind === "daily-open",
    ).length,
    0,
  );
  const record = inbox.locator('[data-record-id="r1"]');
  await record.locator(":scope > summary").focus();
  await page.keyboard.press("Enter");
  assert.equal(await record.evaluate((el) => el.open), true);
  await record
    .getByRole("button", { name: "Inspect source ↗", exact: true })
    .click();
  await page.getByRole("dialog", { name: "Original source" }).waitFor();
  assert.match(
    await page.getByRole("dialog").textContent(),
    /<script>Untrusted text stays escaped.<\/script>/,
  );
  await page.keyboard.press("Escape");
  await record.getByRole("button", { name: "Useful", exact: true }).click();
  await record.getByText("Rating saved.", { exact: true }).waitFor();
  assert.equal(
    (await page.evaluate(() => window.actions)).filter((a) => a.kind === "rate")
      .length,
    1,
  );
  const withheld = inbox.locator('[data-record-id="r2"]');
  assert.equal(
    await withheld
      .locator("summary")
      .getByText("Source access changed", { exact: true })
      .count(),
    1,
  );
  await withheld.locator(":scope > summary").click();
  assert.equal(await withheld.locator("blockquote").count(), 0);
  assert.equal(
    await withheld.getByRole("button", { name: "Useful", exact: true }).count(),
    0,
  );
  await record
    .getByRole("button", { name: "Mark reviewed", exact: true })
    .click();
  await inbox
    .getByText("Review recorded. Your idea is unchanged.", { exact: true })
    .waitFor();
  await inbox
    .getByRole("button", { name: "Next updates", exact: true })
    .click();
  await inbox.getByText("Page 2 of 2", { exact: true }).waitFor();
  assert.equal(await inbox.locator(".inbox-record").count(), 1);
  await inbox
    .getByRole("button", { name: "Previous updates", exact: true })
    .click();
  await inbox.getByText("Page 1 of 2", { exact: true }).waitFor();
  await inbox.locator(".inbox-filter-disclosure > summary").click();
  await inbox
    .getByLabel("Show updates", { exact: true })
    .selectOption("reviewed");
  await page.waitForFunction(
    () => document.querySelectorAll(".inbox-record").length === 1,
  );
  assert.equal(
    await inbox.locator(".inbox-record").getAttribute("data-record-id"),
    "r1",
  );
  await inbox.getByLabel("Show updates", { exact: true }).selectOption("all");
  await inbox.getByText("Page 1 of 2", { exact: true }).waitFor();
  await inbox.locator(".inbox-filter-disclosure > summary").click();
  await inbox.getByRole("button", { name: /Weekly review/ }).click();
  assert.equal(
    (await page.evaluate(() => window.actions)).filter(
      (a) => a.kind === "weekly-open",
    ).length,
    1,
  );
  const daily = inbox.locator(".daily-updates");
  await daily.locator(":scope > summary").click();
  const recap = inbox.locator(".daily-recap");
  await recap.locator(":scope > summary").click();
  await recap.locator(".daily-recap-record").waitFor();
  assert.equal(
    await recap
      .getByRole("button", { name: "Mark reviewed", exact: true })
      .count(),
    0,
  );
  await daily.locator(":scope > summary").click();
  for (const width of [1440, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 1100 });
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      `Inbox overflow at ${width}`,
    );
    await page.mouse.move(0, 0);
    await page.screenshot({
      path: path.join(screenshots, `updates-${width}.png`),
    });
  }
  await page.evaluate(() => window.show("updates", { empty: true }));
  await inbox
    .getByRole("heading", { name: "No updates in this view", exact: true })
    .waitFor();
  await page.evaluate(() => window.show("updates", { inboxError: true }));
  await inbox
    .getByRole("alert")
    .filter({ hasText: "Authored inbox read failure." })
    .waitFor();
  await page.evaluate(() => window.options({ inboxError: false }));
  await inbox.getByRole("button", { name: "Retry inbox", exact: true }).click();
  await inbox.getByText("Page 1 of 2", { exact: true }).waitFor();
  await page.evaluate(() => window.show("updates", { delay: true }));
  await page.waitForFunction(() => window.pending.length === 1);
  await page.evaluate(() => window.show("world"));
  await world.locator(".world-news-item").first().waitFor();
  await page.evaluate(() => window.pending[0]());
  assert.equal(await page.locator(".update-inbox").count(), 0);
  await page.evaluate(() => window.show("ui"));
  await page
    .getByRole("heading", { name: "Shared UI parts", exact: true })
    .waitFor();
  const exampleFilters = page.getByRole("group", {
    name: "Example story filters",
  });
  await exampleFilters.getByRole("button", { name: /^Company/ }).click();
  assert.equal(
    await exampleFilters
      .getByRole("button", { name: /^Company/ })
      .getAttribute("aria-pressed"),
    "true",
  );
  const disclosure = page
    .locator(".ui-preview .ui-disclosure")
    .filter({ has: page.getByText("Inspect evidence", { exact: true }) });
  await disclosure.locator(":scope > summary").focus();
  await page.keyboard.press("Enter");
  assert.equal(await disclosure.evaluate((el) => el.open), true);
  assert.ok(
    await disclosure
      .locator(":scope > summary")
      .evaluate((el) => getComputedStyle(el).display === "flex"),
  );
  await page.setViewportSize({ width: 320, height: 1100 });
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );
  assert.deepEqual(errors, []);
  assert.deepEqual(requests, []);
  console.log(
    JSON.stringify({
      passed:
        "world/inbox filters, keyboard disclosures, source safety, review/rating, paging, recap reads, empty/error/withheld states, stale response fencing",
      viewports: [1440, 768, 390, 320],
      http_requests: 0,
      screenshots,
    }),
  );
} finally {
  await browser.close();
}
