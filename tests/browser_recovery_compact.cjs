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
  temp = await fs.mkdtemp(path.join(os.tmpdir(), "fledge-recovery-ui-"));
  await fs.writeFile(
    path.join(temp, "index.html"),
    `<html lang="en"><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body><div id="root"></div><script type="module" src="${path.join(root, "tests/ui/recovery-compact.jsx")}"></script></body></html>`,
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
  await page.route("**/api/**", (route) =>
    route.fulfill({ json: { result: { documents: [], has_gaps: false } } }),
  );
  await page.goto(base);
  await page.addStyleTag({
    content: "html { scroll-behavior: auto !important; }",
  });
  const screenshots = path.join(
    root,
    "docs/reviews/2026-10-25/recovery-screenshots",
  );
  await fs.mkdir(screenshots, { recursive: true });
  await require("./browser_financial_recovery.cjs")(page, screenshots);
  assert.deepEqual(errors, []);
  assert.deepEqual(requests, []);
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
