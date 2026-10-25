// Exercise the shared header used by loading, research and Account pages; no HTTP.
import assert from "node:assert/strict";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
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
const out = await mkdtemp(path.join(tmpdir(), "fledge-header-"));
const entry = path.join(out, "fixture.jsx");
await writeFile(
  entry,
  `
import React,{useState} from 'react';
import {createRoot} from 'react-dom/client';
import WorkspaceHeader from ${JSON.stringify(path.join(frontend, "src/components/WorkspaceHeader.jsx"))};
import {Button,UserIcon} from ${JSON.stringify(path.join(frontend, "src/components/ui/index.js"))};
import {api} from ${JSON.stringify(path.join(frontend, "src/api/client.js"))};
import ${JSON.stringify(path.join(frontend, "src/components/AccountGate.css"))};
import ${JSON.stringify(path.join(frontend, "src/styles/tokens.css"))};
import ${JSON.stringify(path.join(frontend, "src/styles/app.css"))};
import ${JSON.stringify(path.join(frontend, "src/components/ContentFirstLayout.css"))};
import ${JSON.stringify(path.join(frontend, "src/components/ReadingFlow.css"))};
import ${JSON.stringify(path.join(frontend, "src/styles/mobile.css"))};
api.telegram=async()=>({configured:true,linked:false,deliveries:[],watches:0});
window.actions=[];
function Fixture({beginner=false,waiting=true}){
 const [view,setView]=useState('workspace');
 const account=<Button variant="plain" icon={<UserIcon/>} href="?view=account" aria-current={view==='account'?'page':undefined} onClick={event=>{event.preventDefault();setView('account');}}>Account</Button>;
 return <div className="app-shell" data-view={view}><WorkspaceHeader beginner={beginner} updatesWaiting={waiting} view={view} onNavigate={setView} onHome={()=>setView('workspace')} account={account}/><main id="workspace"><h1>Authored {view}</h1></main></div>;
}
const root=createRoot(document.getElementById('root'));let serial=0;
window.show=options=>root.render(<Fixture key={++serial} {...options}/>);window.show({});
`,
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
let css = await readFile(path.join(out, "fledge.css"), "utf8");
if (process.env.HEADER_INSTALLED_INDEX) {
  const index = path.resolve(process.env.HEADER_INSTALLED_INDEX),
    dist = path.dirname(index);
  const html = await readFile(index, "utf8");
  const links = [
    ...html.matchAll(/<link\b[^>]*rel="stylesheet"[^>]*href="([^"]+)"[^>]*>/g),
  ]
    .map((m) => m[1])
    .filter((h) => !h.includes("/responsive-header-"));
  assert.ok(links.length);
  css = (
    await Promise.all(
      links.map((h) => {
        assert.ok(h.startsWith("/assets/"));
        return readFile(path.join(dist, h.slice(1)), "utf8");
      }),
    )
  ).join("\n");
  const fonts = [
    ...css.matchAll(/url\(["']?(\/fonts\/[A-Za-z0-9_.-]+\.woff2)["']?\)/g),
  ];
  for (const font of fonts) {
    const bytes = await readFile(path.join(dist, font[1].slice(1)));
    css = css.replaceAll(
      font[0],
      `url(data:font/woff2;base64,${bytes.toString("base64")})`,
    );
  }
}
const fix = await readFile(
  path.join(frontend, "src/styles/header.css"),
  "utf8",
);
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.CHROMIUM_PATH,
});
const context = await browser.newContext({
  viewport: { width: 756, height: 900 },
  deviceScaleFactor: 2,
});
const page = await context.newPage();
const errors = [],
  requests = [];
const checked = [];
page.on("pageerror", (e) => errors.push(e.message));
await page.route("**/*", (route) => {
  requests.push(route.request().url());
  return route.abort();
});
const geometry = () =>
  page.evaluate(() => {
    const header = document.querySelector(".topbar"),
      nav = header.querySelector("nav");
    const rect = (el) => {
      const r = el.getBoundingClientRect();
      return {
        x: r.x,
        y: r.y,
        width: r.width,
        height: r.height,
        right: r.right,
        bottom: r.bottom,
      };
    };
    return {
      width: innerWidth,
      header: rect(header),
      nav: rect(nav),
      brand: rect(header.querySelector(".brand")),
      tools: rect(header.querySelector(".topbar-tools")),
      controls: [
        ...header.querySelectorAll(
          "nav button,.telegram-launch,.topbar-tools > .ui-button",
        ),
      ].map((el) => ({ text: el.textContent.trim(), ...rect(el) })),
      overflow: document.documentElement.scrollWidth > innerWidth,
    };
  });
try {
  await page.setContent("<style>" + css + '</style><div id="root"></div>');
  await page.addScriptTag({ content: js });
  await page
    .getByRole("navigation", { name: "Workspace navigation" })
    .waitFor();
  await page.addStyleTag({ content: fix });
  for (const waiting of [false, true])
    for (const beginner of [false, true]) {
      await page.evaluate((options) => window.show(options), {
        waiting,
        beginner,
      });
      await page
        .getByRole("navigation", { name: "Workspace navigation" })
        .getByRole("button", { name: "Home", exact: true })
        .waitFor();
      for (const width of [
        1440, 1024, 981, 980, 900, 820, 800, 768, 756, 740, 601, 600, 390, 320,
        756, 1440,
      ]) {
        await page.setViewportSize({ width, height: 900 });
        const g = await geometry();
        assert.equal(
          g.overflow,
          false,
          JSON.stringify({ waiting, beginner, width, g }),
        );
        for (const c of g.controls) {
          assert.ok(
            c.x >= -1 && c.right <= width + 1,
            JSON.stringify({ waiting, beginner, width, c }),
          );
          assert.ok(
            c.y >= g.header.y && c.bottom <= g.header.bottom + 1,
            JSON.stringify({ waiting, beginner, width, c }),
          );
        }
        if (width <= 980) {
          assert.ok(g.nav.y >= Math.max(g.brand.bottom, g.tools.bottom) - 1);
          assert.equal(g.nav.height, 44);
        } else {
          assert.equal(g.header.height, 60);
          assert.ok(g.tools.x >= g.nav.right);
        }
        for (let i = 1; i < g.controls.length; i++) {
          const a = g.controls[i - 1],
            b = g.controls[i];
          assert.ok(
            a.bottom <= b.y + 1 ||
              b.bottom <= a.y + 1 ||
              a.right <= b.x + 1 ||
              b.right <= a.x + 1,
            "Header controls overlap.",
          );
        }
        if (
          waiting &&
          !beginner &&
          [1440, 980, 756, 600, 390, 320].includes(width)
        )
          await page
            .locator(".topbar")
            .screenshot({ path: path.join(out, "header-" + width + ".png") });
        checked.push({ waiting, beginner, width });
      }
    }
  await page.evaluate(() => window.show({}));
  await page.setViewportSize({ width: 756, height: 900 });
  const account = page.getByRole("link", { name: "Account", exact: true });
  await account.click();
  assert.equal(await account.getAttribute("aria-current"), "page");
  assert.equal(await page.locator(".account-menu").count(), 0);
  const nav = page.getByRole("navigation", { name: "Workspace navigation" });
  await nav.getByRole("button", { name: "World", exact: true }).click();
  assert.equal(
    await nav
      .getByRole("button", { name: "World", exact: true })
      .getAttribute("aria-current"),
    "page",
  );
  await page
    .getByRole("button", { name: "Telegram alerts", exact: true })
    .click();
  await page
    .getByRole("dialog", { name: "Telegram alerts", exact: true })
    .waitFor();
  await page.keyboard.press("Escape");
  assert.deepEqual(errors, []);
  assert.deepEqual(requests, []);
  await writeFile(
    path.join(out, "geometry.json"),
    JSON.stringify({ checked }, null, 2),
  );
  console.log(
    JSON.stringify({
      passed: checked.length + 4,
      resize_cases: checked.length,
      http_requests: 0,
      output: out,
    }),
  );
} catch (error) {
  console.error(JSON.stringify({ out, errors, geometry: await geometry() }));
  throw error;
} finally {
  await browser.close();
}
