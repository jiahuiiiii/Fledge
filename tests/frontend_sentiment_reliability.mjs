// Isolated component browser checks. No Fledge server, API or network requests.
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
const { chromium } = await import(
  pathToFileURL(process.env.PLAYWRIGHT_MODULE || require.resolve("playwright"))
);
const out = await mkdtemp(path.join(tmpdir(), "fledge-phase1-ui-"));
const entry = path.join(out, "fixture.jsx");
await writeFile(
  entry,
  `
import React from 'react';
import {createRoot} from 'react-dom/client';
import Panel from ${JSON.stringify(path.join(frontend, "src/components/SentimentPanel.jsx"))};
import Basis from ${JSON.stringify(path.join(frontend, "src/components/SentimentBasis.jsx"))};
import ${JSON.stringify(path.join(frontend, "src/styles/tokens.css"))};
import ${JSON.stringify(path.join(frontend, "src/styles/app.css"))};
import ${JSON.stringify(path.join(frontend, "src/components/ContentFirstLayout.css"))};
import ${JSON.stringify(path.join(frontend, "src/components/ReadingFlow.css"))};
import ${JSON.stringify(path.join(frontend, "src/styles/mobile.css"))};
const root=createRoot(document.getElementById('root'));
window.actions=[];
window.showFixture=(options={})=>root.render(<div style={{padding:16,maxWidth:1100,margin:'auto'}}>
 <Panel data={{instrument:{id:'authored',symbol:'LUMD',name:'Lumen Devices'},versions:[],
 sentiment:{id:'reading',created_at:'2026-10-17T00:00:00Z',sources:[],items:[],summary:{},repairs:{repaired:1,total:8},withheld:!!options.withheld}}}
 modelStatus={{briefing_enabled:!options.disabled,budget:{running:0}}}
 loadingRun={{active:!!options.active,steps:[{key:'analysis',status:options.active?'running':'failed',batches:{message:'Saved retry failed',total:2,completed:1,failure:{split_available:true}}}]}}
 onAnalyze={(days,action)=>window.actions.push({days,...action})} />
 {!options.withheld && <Basis item={{evidence_policy:'authored',explanation:'Direction unclear.',repair:{policy:'sentiment-item-repair-1'},citations:[{quote:'Literal <script>example</script> evidence.'}],previous_citations:[]}}/>}
</div>);
window.showFixture();
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
const css = await readFile(path.join(out, "fledge.css"), "utf8");
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.CHROMIUM_PATH,
});
const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
const errors = [];
const requests = [];
page.on("pageerror", (e) => errors.push(e.message));
await page.route("**/*", (route) => {
  requests.push(route.request().url());
  return route.abort();
});
try {
  await page.setContent(`<style>${css}</style><div id="root"></div>`);
  await page.addScriptTag({ content: js });
  const panel = page.getByRole("region", {
    name: "News and social sentiment",
    exact: true,
  });
  await panel
    .getByText(
      "1 of 8 labels needed repair: the AI's label and its evidence disagreed.",
      { exact: true },
    )
    .waitFor();
  await page
    .getByText(
      "The AI's label and its evidence disagreed. Inconsistent fields were removed or marked unclear.",
      { exact: true },
    )
    .waitFor();
  assert.equal(await page.locator("script").count(), 1); // Only the fixture script; source text stays escaped.
  await panel.getByText("Read saved sources again", { exact: true }).click();
  await panel
    .getByRole("button", { name: "Re-read everything · paid AI", exact: true })
    .click();
  await panel
    .getByRole("button", {
      name: "Retry with smaller batches · paid AI",
      exact: true,
    })
    .click();
  assert.deepEqual(await page.evaluate(() => window.actions), [
    { days: 7, reread: true },
    { days: 7, split_failed: true },
  ]);
  for (const width of [1440, 390, 320]) {
    await page.setViewportSize({ width, height: 1100 });
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      `overflow at ${width}`,
    );
    await page.screenshot({
      path: path.join(out, `screen-${width}.png`),
      fullPage: true,
    });
  }
  await page.evaluate(() => window.showFixture({ active: true }));
  await panel
    .getByRole("button", { name: "Re-read everything · paid AI", exact: true })
    .waitFor();
  assert.ok(
    await panel
      .getByRole("button", {
        name: "Re-read everything · paid AI",
        exact: true,
      })
      .isDisabled(),
  );
  assert.equal(
    await panel
      .getByRole("button", {
        name: "Retry with smaller batches · paid AI",
        exact: true,
      })
      .count(),
    0,
  );
  await page.evaluate(() => window.showFixture({ disabled: true }));
  assert.ok(
    await panel
      .getByRole("button", {
        name: "Re-read everything · paid AI",
        exact: true,
      })
      .isDisabled(),
  );
  assert.ok(
    await panel
      .getByRole("button", {
        name: "Retry with smaller batches · paid AI",
        exact: true,
      })
      .isDisabled(),
  );
  await page.evaluate(() => window.showFixture({ withheld: true }));
  await panel
    .getByText("This analysis is withheld because source access changed.", {
      exact: true,
    })
    .waitFor();
  assert.equal(await page.getByText(/1 of 8 labels needed repair/).count(), 0);
  assert.deepEqual(errors, []);
  assert.deepEqual(requests, []);
  console.log(
    JSON.stringify({
      passed: 8,
      viewports: [1440, 390, 320],
      network_requests: 0,
      output: out,
    }),
  );
} catch (error) {
  console.error(
    JSON.stringify({
      errors,
      body: (await page.locator("body").innerText()).slice(0, 2000),
      output: out,
    }),
  );
  throw error;
} finally {
  await browser.close();
}
