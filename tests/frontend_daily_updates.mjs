// Actual recap UI, authored data, controlled promises and zero HTTP requests.
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
const out=await mkdtemp(path.join(tmpdir(),'fledge-daily-updates-'));
const entry=path.join(out,'fixture.jsx');
await writeFile(entry,`
import React from 'react';
import {createRoot} from 'react-dom/client';
import Daily from ${JSON.stringify(path.join(frontend,'src/components/DailyUpdates.jsx'))};
import {api} from ${JSON.stringify(path.join(frontend,'src/api/client.js'))};
import ${JSON.stringify(path.join(frontend,'src/styles/tokens.css'))};
import ${JSON.stringify(path.join(frontend,'src/styles/app.css'))};
import ${JSON.stringify(path.join(frontend,'src/styles/mobile.css'))};
window.actions=[];window.pending=[];let opts={};
const quote='Nvidia announced a new agreement <script>untrusted</script>.';
function record(page){return {kind:'company',id:'alert-'+page,created_at:'2026-10-16T20:00:00Z',feedback_enabled:true,
 detail:{id:'alert-'+page,instrument_id:'NVDA',symbol:'NVDA',created_at:'2026-10-16T20:00:00Z',withheld:false,previous_items:[],previous_sources:[],
 payload:{title:'Company update '+page,reason:'A cited company development.',previous_cutoff:'2026-10-15T20:00:00Z',
 items:[{id:'item_1',source_id:'n1',sentiment:'neutral',statement:'reported_development',evidence_policy:'authored',
 explanation:'The source describes an announcement.',citations:[{source_id:'n1',quote}]}]},
 sources:[{id:'n1',title:'Authored company announcement '+page,body:quote,source:'Authored Wire',kind:'news',published_at:'2026-10-16T19:00:00Z',url:'https://example.test/announcement'}]}};}
const today={day:'2026-10-17',charged_usd:'5.000000001',pending_max_usd:'0.7',experiment_charged_usd:'0.5',observed_at:'2026-10-17T06:00:00Z'};
api.dailyUpdates=async()=>{window.actions.push({kind:'read-history'});const current={...opts};
 if(current.historyError)throw new Error('Authored history read failure.');
 return {enabled:current.enabled!==false,today_spend:current.noSpend?null:today,
 digests:[{id:current.id||'daily-a',total:2,preview:true,window_end:'2026-10-16T23:00:00Z'}],
 spending:current.noSpend?[]:[{id:'spend1',day:'2026-10-16',observed_at:'2026-10-16T23:00:00Z',charged_nano_usd:5000000000,pending_max_nano_usd:1,current:today}],
 notices:current.noSpend?[]:[{id:'cost1',day:'2026-10-17',threshold_nano_usd:5000000000,charged_nano_usd:5000000001,created_at:'2026-10-17T06:00:00Z',preview:true}]};};
api.dailyDigest=(id,page)=>{window.actions.push({kind:'read-digest',id,page});const current={...opts};
 const result={id,page,page_size:1,total:2,records:[record(page)],window_start:'2026-10-15T23:00:00Z',window_end:'2026-10-16T23:00:00Z',limitation:'Saved membership; source access checked now.'};
 if(current.withheld)result.records[0].detail={...result.records[0].detail,withheld:true,payload:{},sources:[]};
 if(current.digestError)return Promise.reject(new Error('Authored recap read failure.'));
 if(current.delay)return new Promise(resolve=>window.pending.push(()=>resolve(result)));
 return Promise.resolve(result);};
api.rateAlert=async(kind,id,value)=>{window.actions.push({kind:'rate',alertKind:kind,id,value});return {value};};
const root=createRoot(document.getElementById('root'));let serial=0;
window.show=(next={})=>{opts=next;root.render(<div className="app-shell" style={{display:'block',padding:16,maxWidth:900,margin:'auto'}}>
 <Daily key={++serial} onSource={()=>window.actions.push({kind:'inspect-source'})} onOpen={()=>window.actions.push({kind:'navigate'})}/></div>);};
window.options=(patch)=>{opts={...opts,...patch};};
window.show();
`);
await build({configFile:false,root:frontend,plugins:[react()],logLevel:'error',define:{'process.env.NODE_ENV':JSON.stringify('production')},
 resolve:{alias:{react:path.join(frontend,'node_modules/react'),'react-dom':path.join(frontend,'node_modules/react-dom')}},
 build:{outDir:out,emptyOutDir:false,lib:{entry,name:'Fixture',formats:['iife'],fileName:()=>'fixture.js'},cssCodeSplit:false,minify:false}});
const js=await readFile(path.join(out,'fixture.js'),'utf8');
const css=await readFile(path.join(out,'fledge.css'),'utf8');
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
const page=await browser.newPage({viewport:{width:1440,height:1000}});
const errors=[],requests=[];
page.on('pageerror',e=>errors.push(e.message));
await page.route('**/*',route=>{requests.push(route.request().url());return route.abort();});
try{
 await page.setContent('<style>'+css+'</style><div id="root"></div>');await page.addScriptTag({content:js});
 const panel=page.getByRole('group',{name:'Daily recaps and AI spending'});
 await panel.locator(':scope > summary').getByText(/Daily recaps · AI today US\$5.00/).waitFor();
 assert.equal((await page.evaluate(()=>window.actions)).filter(a=>a.kind==='read-digest').length,0);
 await panel.locator(':scope > summary').click();
 await page.getByRole('region',{name:"Today's AI spending"}).locator(':scope > p').filter({hasText:/US\$0.70 maximum awaiting confirmation/}).waitFor();
 await page.getByText('Exact spending totals',{exact:true}).click();
 await page.getByText('US$5.000000001 confirmed · US$0.70 unresolved maximum.',{exact:true}).waitFor();
 await page.getByText('Exact spending totals',{exact:true}).click();
 await page.getByText('Earlier daily spending',{exact:true}).click();
 await page.getByText(/Saved at.*US\$5.00 confirmed, under US\$0.01 unresolved maximum/).waitFor();
 const recap=page.locator('.daily-recap');await recap.locator(':scope > summary').click();
 await recap.getByText('Authored company announcement 0',{exact:true}).waitFor();
 assert.equal(await recap.locator('img,script').count(),0);
 assert.equal(await recap.locator('blockquote').innerText(),'Nvidia announced a new agreement <script>untrusted</script>.');
 assert.equal(await recap.getByRole('button',{name:'Mark reviewed',exact:true}).count(),0);
 await recap.getByRole('button',{name:'Useful',exact:true}).click();
 await recap.getByText('Rating saved.',{exact:true}).waitFor();
 await recap.getByRole('button',{name:'Next recap updates',exact:true}).click();
 await recap.getByText('Authored company announcement 1',{exact:true}).waitFor();
 assert.equal(await recap.getByText('Authored company announcement 0',{exact:true}).count(),0);
 assert.ok(await recap.getByRole('button',{name:'Next recap updates',exact:true}).isDisabled());
 for(const width of [1440,390,320]){
  await page.setViewportSize({width,height:1000});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await panel.screenshot({path:path.join(out,'daily-'+width+'.png'),animations:'disabled'});
 }
 await page.evaluate(()=>window.options({withheld:true}));
 await recap.locator(':scope > summary').click();
 await recap.locator(':scope > summary').click();
 await recap.getByText(/Evidence is currently unavailable/).waitFor();
 assert.equal(await recap.locator('blockquote').count(),0);
 assert.equal(await recap.getByRole('button',{name:'Useful',exact:true}).count(),0);
 await page.evaluate(()=>window.show({digestError:true,noSpend:true}));
 await page.locator('.daily-updates > summary').click();
 assert.equal(await page.getByRole('region',{name:"Today's AI spending"}).count(),0);
 await page.locator('.daily-recap > summary').click();
 await page.getByRole('alert').getByText('Authored recap read failure.',{exact:true}).waitFor();
 await page.evaluate(()=>window.options({digestError:false}));
 await page.getByRole('button',{name:'Try reading recap again',exact:true}).click();
 await page.getByText('Authored company announcement 0',{exact:true}).waitFor();
 await page.evaluate(()=>window.show({delay:true,id:'old-daily'}));
 await page.locator('.daily-updates > summary').click();await page.locator('.daily-recap > summary').click();
 await page.getByRole('status').getByText('Reading saved recap…',{exact:true}).waitFor();
 await page.evaluate(()=>window.show({enabled:false}));
 await page.locator('.daily-updates').waitFor({state:'hidden'});
 await page.evaluate(()=>window.pending[0]());
 assert.equal(await page.getByText('Authored company announcement 0',{exact:true}).count(),0);
 const actions=await page.evaluate(()=>window.actions);
 assert.equal(actions.filter(a=>a.kind==='rate').length,1);
 assert.equal(actions.filter(a=>!['read-history','read-digest','rate'].includes(a.kind)).length,0);
 assert.deepEqual(errors,[]);assert.deepEqual(requests,[]);
 console.log(JSON.stringify({passed:10,viewports:[1440,390,320],http_requests:0,output:out}));
}finally{await browser.close();}
