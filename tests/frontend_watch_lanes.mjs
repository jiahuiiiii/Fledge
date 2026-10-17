// Actual React watch settings/history, isolated from Fledge and the network.
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
const { default: react } = await import(pathToFileURL(require.resolve("@vitejs/plugin-react")));
const { chromium } = await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE || require.resolve("playwright")));
const out = await mkdtemp(path.join(tmpdir(), "fledge-watch-lanes-"));
const entry = path.join(out, "fixture.jsx");
await writeFile(entry, `
import React from 'react';
import {createRoot} from 'react-dom/client';
import Panel from ${JSON.stringify(path.join(frontend,"src/components/SentimentPanel.jsx"))};
import History from ${JSON.stringify(path.join(frontend,"src/components/WatchCheckHistory.jsx"))};
import {api} from ${JSON.stringify(path.join(frontend,"src/api/client.js"))};
import ${JSON.stringify(path.join(frontend,"src/styles/tokens.css"))};
import ${JSON.stringify(path.join(frontend,"src/styles/app.css"))};
import ${JSON.stringify(path.join(frontend,"src/components/ContentFirstLayout.css"))};
import ${JSON.stringify(path.join(frontend,"src/components/ReadingFlow.css"))};
import ${JSON.stringify(path.join(frontend,"src/styles/mobile.css"))};
const root=createRoot(document.getElementById('root'));
api.watchChecks=async()=>({items:['fast','slow'].map((lane,index)=>({id:lane,lane,status:'completed',
 started_at:'2026-10-17T00:00:00Z',completed_at:'2026-10-17T00:00:30Z',elapsed_seconds:30,
 reason:'Authored completed source check.',details:{market:lane==='fast'?'checked':'separate_fast_lane',
 social:lane==='slow'?'checked':'separate_slow_lane',analysis:'completed'}})),next_cursor:null});
window.actions=[];
window.showFixture=(options={})=>root.render(<div style={{padding:16,maxWidth:1100,margin:'auto'}}>
 {options.history ? <History instrumentId="authored"/> : <Panel
 data={{instrument:{id:'authored',symbol:'LUMD',name:'Lumen Devices'},versions:[],
 news_watch:{enabled:true,interval_minutes:60,lanes_enabled:options.lanes!==false,
 fast_check:{last_check_at:'2026-10-17T00:00:00Z'}},
 sentiment:{id:'reading',created_at:'2026-10-17T00:00:00Z',sources:[],items:[],summary:{}}}}
 modelStatus={{briefing_enabled:true,budget:{running:0}}}
 onWatch={(enabled,interval)=>window.actions.push({enabled,interval})}/>}
 </div>);
window.showFixture();
`);
await build({configFile:false,root:frontend,plugins:[react()],logLevel:"error",
 define:{"process.env.NODE_ENV":JSON.stringify("production")},
 resolve:{alias:{react:path.join(frontend,"node_modules/react"),"react-dom":path.join(frontend,"node_modules/react-dom")}},
 build:{outDir:out,emptyOutDir:false,lib:{entry,name:"Fixture",formats:["iife"],fileName:()=>"fixture.js"},cssCodeSplit:false,minify:false}});
const js=await readFile(path.join(out,"fixture.js"),"utf8");
const css=await readFile(path.join(out,"fledge.css"),"utf8");
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
const page=await browser.newPage({viewport:{width:1440,height:1100}});
const errors=[],requests=[];
page.on("pageerror",error=>errors.push(error.message));
await page.route("**/*",route=>{requests.push(route.request().url());return route.abort();});
try {
 await page.setContent(`<style>${css}</style><div id="root"></div>`);
 await page.addScriptTag({content:js});
 await page.getByRole("button",{name:"Watch · on",exact:true}).click();
 const dialog=page.getByRole("dialog",{name:"News & discussion · watch"});
 await dialog.getByText("Discussion checks every",{exact:false}).waitFor();
 await dialog.getByText(/News checks run every 15 minutes/).waitFor();
 await dialog.getByRole("combobox",{name:"Watch frequency"}).selectOption("240");
 assert.deepEqual(await page.evaluate(()=>window.actions),[{enabled:true,interval:240}]);
 for(const width of [1440,390,320]){
  await page.setViewportSize({width,height:1100});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:path.join(out,`settings-${width}.png`),fullPage:true});
 }
 await page.keyboard.press("Escape");
 await page.getByRole("button",{name:"Watch · on",exact:true}).waitFor();
 await page.evaluate(()=>window.showFixture({lanes:false}));
 await page.getByRole("button",{name:"Watch · on",exact:true}).click();
 await dialog.getByText("Check every",{exact:false}).waitFor();
 assert.equal(await dialog.getByText(/News checks run every 15 minutes/).count(),0);
 await page.keyboard.press("Escape");
 await page.evaluate(()=>window.showFixture({history:true}));
 await page.getByText("Watch check history",{exact:true}).click();
 await page.getByText("News check · Check completed",{exact:true}).waitFor();
 await page.getByText("Discussion check · Check completed",{exact:true}).waitFor();
 for(const details of await page.getByText("What was checked",{exact:true}).all())await details.click();
 await page.getByText("Checked separately by discussion checks",{exact:true}).waitFor();
 await page.getByText("Checked separately by news checks",{exact:true}).waitFor();
 for(const width of [1440,390,320]){
  await page.setViewportSize({width,height:1100});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:path.join(out,`history-${width}.png`),fullPage:true});
 }
 assert.deepEqual(errors,[]);assert.deepEqual(requests,[]);
 console.log(JSON.stringify({passed:6,viewports:[1440,390,320],network_requests:0,output:out}));
}catch(error){
 console.error(JSON.stringify({errors,output:out,body:(await page.locator("body").innerText()).slice(0,1800)}));
 throw error;
}finally{await browser.close();}
