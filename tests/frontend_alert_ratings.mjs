// Actual rating component, controlled async responses; no server or HTTP.
import assert from 'node:assert/strict';
import {mkdtemp,readFile,writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const frontend=path.join(root,'frontend');
const require=createRequire(path.join(frontend,'package.json'));
const {build}=await import(pathToFileURL(require.resolve('vite')));
const {default:react}=await import(pathToFileURL(require.resolve('@vitejs/plugin-react')));
const {chromium}=await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE));
const out=await mkdtemp(path.join(tmpdir(),'fledge-alert-rating-'));
const entry=path.join(out,'fixture.jsx');
await writeFile(entry,`
import React from 'react';
import {createRoot} from 'react-dom/client';
import Rating from ${JSON.stringify(path.join(frontend,'src/components/AlertRating.jsx'))};
import {api} from ${JSON.stringify(path.join(frontend,'src/api/client.js'))};
import ${JSON.stringify(path.join(frontend,'src/styles/tokens.css'))};
import ${JSON.stringify(path.join(frontend,'src/styles/app.css'))};
import ${JSON.stringify(path.join(frontend,'src/styles/mobile.css'))};
window.actions=[];window.pending=[];
api.rateAlert=(kind,id,value)=>{window.actions.push({kind,id,value});return new Promise((resolve,reject)=>window.pending.push({resolve,reject}));};
window.finish=(index,value='useful')=>window.pending[index].resolve({value});
window.fail=(index)=>window.pending[index].reject(new Error('Authored save failure. Try again.'));
const root=createRoot(document.getElementById('root'));
window.show=(record={})=>root.render(<main className="app-shell" style={{display:'block',padding:16,maxWidth:900,margin:'auto'}}>
<article className="card" data-alert-id={record.id||'a'}><h2>Company reports a lower outlook</h2><p>Evidence and source links stay together here.</p>
<Rating record={{kind:'company',id:'a',feedback_enabled:true,detail:{},...record}}/></article></main>);
window.show();
`);
await build({configFile:false,root:frontend,plugins:[react()],logLevel:'error',
 define:{'process.env.NODE_ENV':JSON.stringify('production')},
 resolve:{alias:{react:path.join(frontend,'node_modules/react'),'react-dom':path.join(frontend,'node_modules/react-dom')}},
 build:{outDir:out,emptyOutDir:false,lib:{entry,name:'Fixture',formats:['iife'],fileName:()=>'fixture.js'},cssCodeSplit:false,minify:false}});
const js=await readFile(path.join(out,'fixture.js'),'utf8');
const css=await readFile(path.join(out,'fledge.css'),'utf8');
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
const page=await browser.newPage({viewport:{width:1440,height:900}});
const errors=[],requests=[];
page.on('pageerror',e=>errors.push(e.message));
await page.route('**/*',route=>{requests.push(route.request().url());return route.abort();});
try{
 await page.setContent('<style>'+css+'</style><div id="root"></div>');
 await page.addScriptTag({content:js});
 const useful=page.getByRole('button',{name:'Useful',exact:true});
 const no=page.getByRole('button',{name:'Not useful',exact:true});
 await useful.waitFor();
 assert.equal(await useful.getAttribute('aria-pressed'),'false');
 assert.equal((await page.evaluate(()=>window.actions)).length,0);
 await useful.click();
 assert.ok(await useful.isDisabled());assert.ok(await no.isDisabled());
 await page.evaluate(()=>window.finish(0));
 await page.getByRole('status').getByText('Rating saved.',{exact:true}).waitFor();
 assert.equal(await useful.getAttribute('aria-pressed'),'true');
 await no.click();await page.evaluate(()=>window.fail(1));
 await page.getByRole('alert').getByText('Authored save failure. Try again.',{exact:true}).waitFor();
 assert.equal(await useful.getAttribute('aria-pressed'),'true');assert.ok(await no.isEnabled());
 await no.click();await page.evaluate(()=>window.finish(2,'not_useful'));
 await page.getByRole('status').waitFor();
 assert.equal(await no.getAttribute('aria-pressed'),'true');
 // Late A response must not change B or a fresh view of A (ABA navigation).
 await useful.click();await page.evaluate(()=>window.show({id:'b',feedback:{value:'not_useful'}}));
 await page.waitForFunction(()=>document.querySelector('article')?.dataset.alertId==='b' && !document.querySelector('button[disabled]'));
 assert.equal(await no.getAttribute('aria-pressed'),'true');
 await page.evaluate(()=>window.show({id:'a'}));
 await page.waitForFunction(()=>document.querySelector('article')?.dataset.alertId==='a' && !document.querySelector('[aria-pressed="true"]'));
 await page.evaluate(()=>window.finish(3));
 assert.equal(await useful.getAttribute('aria-pressed'),'false');
 assert.equal(await page.getByRole('status').count(),0);
 for(const width of [1440,390,320]){
  await page.setViewportSize({width,height:900});
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  assert.equal(await page.locator('article').count(),1);
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.locator('article').screenshot({path:path.join(out,'rating-'+width+'.png'),animations:'disabled'});
 }
 await page.evaluate(()=>window.show({detail:{withheld:true}}));
 await useful.waitFor({state:'hidden'});
 await page.evaluate(()=>window.show({feedback_enabled:false}));
 assert.equal(await page.getByRole('region',{name:'Rate this alert'}).count(),0);
 assert.deepEqual(await page.evaluate(()=>window.actions),[
  {kind:'company',id:'a',value:'useful'},{kind:'company',id:'a',value:'not_useful'},
  {kind:'company',id:'a',value:'not_useful'},{kind:'company',id:'a',value:'useful'}]);
 assert.deepEqual(errors,[]);assert.deepEqual(requests,[]);
 console.log(JSON.stringify({passed:8,viewports:[1440,390,320],http_requests:0,output:out}));
}finally{await browser.close();}
