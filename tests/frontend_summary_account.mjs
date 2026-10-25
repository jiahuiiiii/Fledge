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
const out = await mkdtemp(path.join(tmpdir(), "fledge-summary-account-"));
const entry = path.join(out, "fixture.jsx");
await writeFile(
  entry,
  (
    await readFile(path.join(root, "tests/ui/summary-account.jsx"), "utf8")
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
  "docs/reviews/2026-10-25/summary-account-screenshots",
);
await mkdir(screenshots, { recursive: true });
const errors = [],
  requests = [];
page.on("pageerror", (e) => errors.push(e.message));
await page.route("**/*", async (route) => {
  if (
    route.request().isNavigationRequest() &&
    new URL(route.request().url()).hostname === "fledge.test"
  )
    return route.fulfill({
      contentType: "text/html; charset=utf-8",
      body:
        '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>' +
        css +
        '</style></head><body><div id="root"></div><script>' +
        js.replaceAll("</script>", "<" + "/script>".replace("/", "\\/")) +
        "</script></body></html>",
    });
  const resource = new URL(route.request().url());
  if (
    resource.hostname === "fledge.test" &&
    /^\/fonts\/[A-Za-z0-9_-]+\.woff2$/.test(resource.pathname)
  ) {
    return route.fulfill({
      contentType: "font/woff2",
      body: await readFile(
        path.join(frontend, "public", resource.pathname.slice(1)),
      ),
    });
  }
  requests.push(route.request().url());
  return route.abort();
});
try {
  await page.goto("http://fledge.test/?company=example&view=account");
  const account = page.getByRole("region", { name: "Account", exact: true });
  await account.getByRole("switch", { name: /Pro tools/ }).waitFor();
  assert.equal(
    (await page.evaluate(() => window.actions)).filter((a) =>
      ["workspace", "mode", "password", "recovery", "logout"].includes(a.kind),
    ).length,
    0,
  );
  assert.equal(await page.locator(".account-menu").count(), 0);
  assert.equal(
    await page
      .getByRole("heading", { name: "Account", exact: true })
      .evaluate((el) => el === document.activeElement),
    true,
  );
  assert.equal(
    await account.getByText("exampleuser", { exact: true }).count(),
    1,
  );
  for (const width of [1440, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 1100 });
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    );
    await page.mouse.move(0, 0);
    await page.screenshot({
      path: path.join(screenshots, `account-${width}.png`),
    });
  }
  await account.getByRole("switch", { name: /Pro tools/ }).click();
  assert.equal(
    await account.getByRole("switch", { name: /Pro tools/ }).isChecked(),
    false,
  );
  assert.deepEqual(
    (await page.evaluate(() => window.actions)).find((a) => a.kind === "mode"),
    { kind: "mode", value: "explain" },
  );
  await account
    .getByRole("button", { name: "Password and recovery code", exact: true })
    .click();
  const security = page.getByRole("dialog", {
    name: "Password and recovery code",
    exact: true,
  });
  await security.waitFor();
  assert.equal(
    await security
      .getByLabel("Current password", { exact: true })
      .evaluate((el) => el === document.activeElement),
    true,
  );
  assert.equal(
    (await page.evaluate(() => window.actions)).filter(
      (a) => a.kind === "password" || a.kind === "recovery",
    ).length,
    0,
  );
  await page.keyboard.press("Escape");
  assert.equal(await page.getByRole("dialog").count(), 0);
  await account
    .getByRole("button", { name: "← Back to research", exact: true })
    .click();
  await page.waitForURL(/view=workspace/);
  await page.locator("#workspace").waitFor();
  await page.evaluate(() => {
    const input = document.createElement("input");
    input.id = "draft-probe";
    input.value = "Unsaved draft";
    document.querySelector("#workspace").append(input);
  });
  await page.getByRole("link", { name: "Account", exact: true }).click();
  await page.waitForURL(/view=account/);
  assert.equal(await page.locator("#workspace").count(), 1);
  await page.goBack();
  await page.waitForURL(/view=workspace/);
  assert.equal(
    await page.locator("#draft-probe").inputValue(),
    "Unsaved draft",
  );
  assert.equal(
    (await page.evaluate(() => window.actions)).filter(
      (a) => a.kind === "workspace",
    ).length,
    1,
  );
  await page.getByRole("link", { name: "Account", exact: true }).click();
  await account.waitFor();
  await page.reload();
  await account.getByRole("switch", { name: /Pro tools/ }).waitFor();
  assert.equal(
    (await page.evaluate(() => window.actions)).filter(
      (a) => a.kind === "workspace",
    ).length,
    0,
  );
  await account
    .getByRole("button", { name: "Password and recovery code", exact: true })
    .click();
  await security
    .getByLabel("Current password", { exact: true })
    .fill("authored-password");
  await security
    .getByRole("button", { name: "Create a recovery code", exact: true })
    .click();
  await security.getByLabel("Recovery code", { exact: true }).waitFor();
  assert.equal(
    (await page.evaluate(() => window.actions)).filter(
      (a) => a.kind === "recovery",
    ).length,
    1,
  );
  await security
    .getByRole("button", { name: "I’ve saved it", exact: true })
    .click();
  await account.getByText("Recovery code is set.", { exact: true }).waitFor();
  await account
    .getByRole("button", { name: "Retake questions", exact: true })
    .click();
  await page.getByRole("button", { name: "Not now", exact: true }).click();
  await account
    .getByRole("heading", { name: "Account", exact: true })
    .waitFor();
  // Reopen the dedicated page to check the existing sign-out boundary.
  await page.reload();
  await account.getByRole("button", { name: "Sign out", exact: true }).click();
  await page
    .getByRole("heading", { name: "Welcome back", exact: true })
    .waitFor();
  assert.equal(
    await page.getByRole("region", { name: "Account", exact: true }).count(),
    0,
  );
  assert.equal(
    (await page.evaluate(() => window.actions)).filter(
      (a) => a.kind === "logout",
    ).length,
    1,
  );
  await page.evaluate(() => window.showSummary());
  const cards = page.locator(".bs-summary-cards");
  await cards.getByRole("link", { name: /World: 1 could help/ }).waitFor();
  assert.equal(await cards.getByRole("link").count(), 3);
  assert.equal(await cards.locator(".bs-shape").count(), 0);
  assert.equal(await page.locator(".bs-key").count(), 0);
  assert.match(await cards.textContent(), /1 good, 1 bad, 1 mixed, 1 neutral/);
  for (const width of [1440, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 1100 });
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    );
    assert.deepEqual(
      await cards
        .locator(".ui-card")
        .evaluateAll((els) =>
          els.map((el) => getComputedStyle(el).backgroundColor),
        ),
      ["rgb(24, 24, 27)", "rgb(24, 24, 27)", "rgb(24, 24, 27)"],
    );
    await page.mouse.move(0, 0);
    await page.screenshot({
      path: path.join(screenshots, `summary-${width}.png`),
    });
  }
  await cards.getByRole("link", { name: /News:/ }).focus();
  await page.keyboard.press("Enter");
  assert.equal(new URL(page.url()).hash, "#bs-news");
  assert.deepEqual(errors, []);
  assert.deepEqual(requests, []);
  console.log(
    JSON.stringify({
      passed:
        "Account direct URL/reload/back, retained research subtree, explicit mode/security/quiz/logout, neutral Summary cards and jump links",
      widths: [1440, 768, 390, 320],
      network_requests: 0,
      screenshots,
    }),
  );
} finally {
  await browser.close();
}
