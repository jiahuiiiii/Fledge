// Actual React price preview/inbox; authored data, zero browser HTTP requests.
import assert from "node:assert/strict";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const frontend = path.join(root,"frontend");
const require = createRequire(path.join(frontend,"package.json"));
const {build} = await import(pathToFileURL(require.resolve("vite")));
const {default:react} = await import(pathToFileURL(require.resolve("@vitejs/plugin-react")));
const {chromium} = await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE || require.resolve("playwright")));
const out = await mkdtemp(path.join(tmpdir(),"fledge-price-preview-"));
const entry = path.join(out,"fixture.jsx");
await writeFile(entry,`
import React,{useState} from 'react';
import {createRoot} from 'react-dom/client';
import Card from ${JSON.stringify(path.join(frontend,"src/components/MoveAlertCard.jsx"))};
import Inbox from ${JSON.stringify(path.join(frontend,"src/components/UpdateInbox.jsx"))};
import {api} from ${JSON.stringify(path.join(frontend,"src/api/client.js"))};
import ${JSON.stringify(path.join(frontend,"src/styles/tokens.css"))};
import ${JSON.stringify(path.join(frontend,"src/styles/app.css"))};
import ${JSON.stringify(path.join(frontend,"src/styles/mobile.css"))};
window.actions=[];
let reviewed=null;
let companyMode=false;
let dailyMode=false;
let actualMode=false;
const members=['NVDA','AVGO','AMZN','GOOGL'].map((symbol,i)=>({symbol,instrument_id:symbol,
 price:i<2?'96.8':'98.3',previous_close:'100',change_percent:i<2?'-3.2':'-1.7',quoted_at:'2026-10-14T20:00:00Z',
 context_only:i>1,triggered:i<2,thresholds:{session:'3',relative:'2',two_sessions:'5'},reasons:i<2?['session_move']:[],
 indexes:{QQQ:{change_percent:'-2.1',gap_points:i<2?'-1.1':'.4'}},
 sector:i<2?{symbol:'SOXX',change_percent:'-2.8',gap_points:'-.4'}:null,two_sessions:null}));
const detail={id:'authored-move',preview:true,withheld:false,event_type:'market',title:'NVDA −3.2% today · Nasdaq −2.1%',
 symbol:'NVDA, AVGO, AMZN, GOOGL',members,review_action:null,
 explanation:{cause:'market',text:'The headline reports an AI rotation.',sentences:[{text:'The headline reports an AI rotation.',
 citations:[{source_id:'a1',quote:'Investors rotate out of AI <script>alert(1)</script>'}]}]},
 sources:[{id:'a1',title:'Authored market headline <img src=x>',publisher:'Authored Wire',published_at:'2026-10-14T19:00:00Z',url:'https://example.test/market'}],
 limitation:'Bounded saved excerpts; not complete coverage.'};
const companyDetail={id:'authored-company',instrument_id:'NVDA',symbol:'NVDA',preview:true,withheld:false,
 created_at:'2026-10-14T20:00:00Z',previous_items:[],previous_sources:[],
 payload:{title:'New company developments to review',reason:'A newly analysed company development has cited importance evidence.',
 previous_cutoff:'2026-10-13T20:00:00Z',items:[{id:'item_1',source_id:'n1',sentiment:'neutral',statement:'reported_development',
 evidence_policy:'authored-current-policy',explanation:'The source describes a company announcement.',
 citations:[{source_id:'n1',quote:'Nvidia announced a new supply agreement.'}],
 importance:{level:'high',category:'deal',citations:[{source_id:'n1',quote:'Nvidia announced a new supply agreement.'}]}}]},
 sources:[{id:'n1',title:'Nvidia announces a new supply agreement',body:'Nvidia announced a new supply agreement.',
 source:'Authored Wire',kind:'news',published_at:'2026-10-14T19:00:00Z',url:'https://example.test/deal'}]};
api.priceReferences=async(id)=>{window.actions.push({kind:'read-sector',id});return {sector:{symbol:'SOXX',origin:'classification'},choices:[{symbol:'SOXX',name:'Semiconductor fund'}]};};
api.setPriceReference=async(id,symbol)=>{window.actions.push({kind:'save-sector',id,symbol});return {symbol,origin:'owner'};};
api.reviewMoveAlert=async(id,action)=>{window.actions.push({kind:'review-move',id,action});reviewed=action;};
api.reviewAlert=async()=>{throw new Error('Move routed to company review');};
api.rateAlert=async(kind,id,value)=>{window.actions.push({kind:'rate',alertKind:kind,id,value});return {value};};
api.dailyUpdates=async()=>{window.actions.push({kind:'read-daily'});return {enabled:true,today_spend:null,digests:[],spending:[],notices:[]};};
api.researchReview=async(filters)=>({instrument_id:filters.instrument_id||null,review:filters.review,page:filters.page,
 daily_reports_enabled:dailyMode,
 page_size:20,total:1,cutoff:'2026-10-15T00:00:00Z',records:companyMode ? [{kind:'company',id:companyDetail.id,
 title:companyDetail.payload.title,created_at:companyDetail.created_at,detail:{...companyDetail,preview:!actualMode},feedback_enabled:true,
 routing:{preview:!actualMode,channel:'telegram',reason:'At least one cited company development has high importance.'}}] : [{kind:'move',id:detail.id,title:detail.title,feedback_enabled:true,
 created_at:'2026-10-14T20:00:00Z',review_action:reviewed,detail:{...detail,review_action:reviewed}}],
 companies:members.map(m=>({id:m.instrument_id,symbol:m.symbol,name:'Authored company',mode:'sec',
 coverage:{concerns:[],watch:{enabled:true},social_feeds:[]}})),totals:{pending_count:reviewed?0:1}});
function Wrapper({options}){
 const [filters,setFilters]=useState({company:options.scoped?'NVDA':'',review:'all',page:0,cutoff:''});
 const visibleMembers=options.twoSessions ? [{...members[0],change_percent:'1',reasons:['two_session_move'],
 two_sessions:{change_percent:'-5.6',from_session:'2026-10-13'}}] : members;
 return <div className="app-shell" style={{display:'block',padding:16,maxWidth:1000,margin:'auto'}}>
 {options.inbox ? <Inbox filters={filters} onFiltersChange={setFilters} catalogue={[]}
 onOpen={()=>{}} onReviewed={async()=>{}}/> : <Card alert={{...detail,members:visibleMembers,withheld:!!options.withheld}} readOnly={!!options.readOnly}
 onOpen={(id,view)=>window.actions.push({kind:'open',id,view})}
 onReview={(id,action)=>window.actions.push({kind:'review-move',id,action})}/>}
 </div>;
}
const root=createRoot(document.getElementById('root'));let serial=0;
window.showFixture=(options={})=>{
 companyMode=!!options.company;
 actualMode=!!options.actual;
 dailyMode=!!options.daily;
 if(options.clean){
  detail.explanation.sentences[0].citations[0].quote='Investors rotate out of AI on spending worries.';
  detail.sources[0].title='Investors weigh AI spending as technology shares fall';
 }
 root.render(<Wrapper key={++serial} options={options}/>);
};
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
page.on("pageerror",e=>errors.push(e.message));
await page.route("**/*",route=>{requests.push(route.request().url());return route.abort();});
try{
 await page.setContent('<style>'+css+'</style><div id="root"></div>');
 await page.addScriptTag({content:js});
 await page.getByText('Preview · not sent to Telegram',{exact:true}).waitFor();
 assert.equal(await page.getByText('Market context only · did not cross an individual move threshold.',{exact:true}).count(),2);
 assert.equal(await page.locator('script:not([type]) img').count(),0);
 assert.equal(await page.locator('.move-alert-card img').count(),0);
 assert.equal(await page.getByRole('link',{name:'Authored market headline <img src=x> ↗'}).getAttribute('href'),'https://example.test/market');
 const evidence=page.getByRole('region',{name:'Explanation and supporting headlines'});
 assert.equal(await evidence.getByText('The headline reports an AI rotation.',{exact:true}).count(),1);
 assert.equal(await evidence.locator('figure').count(),1);
 assert.equal(await page.getByRole('table',{name:'Price move comparison'}).locator('tbody tr').count(),4);
 await page.getByText('Sector comparison settings',{exact:true}).click();
 const choice=page.getByRole('combobox',{name:'Sector comparison for NVDA'});
 await choice.selectOption('');
 assert.equal((await page.evaluate(()=>window.actions)).filter(a=>a.kind==='save-sector').length,0);
 await page.getByRole('button',{name:'Save sector comparison',exact:true}).click();
 await page.getByText(/Sector comparison saved for future checks/).waitFor();
 assert.deepEqual((await page.evaluate(()=>window.actions)).find(a=>a.kind==='save-sector'),{kind:'save-sector',id:'NVDA',symbol:null});
 await page.getByText('Sector comparison settings',{exact:true}).click();
 await page.evaluate(()=>window.showFixture({clean:true}));
 await page.getByText('Investors rotate out of AI on spending worries.',{exact:true}).waitFor();
 assert.equal(await page.getByText('A positive gap means a stronger move than Nasdaq; a negative gap means weaker.',{exact:true}).count(),1);
 for(const width of [1440,390,320]){
  await page.setViewportSize({width,height:1100});
  assert.equal(await page.locator('.move-alert-card').count(),1);
  assert.equal(await page.getByText('Preview · not sent to Telegram',{exact:true}).count(),1);
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:path.join(out,'preview-'+width+'.png'),fullPage:true});
 }
 await page.evaluate(()=>window.showFixture({twoSessions:true}));
 await page.getByRole('cell',{name:/−5.6% over 2 sessions/}).waitFor();
 assert.equal(await page.getByRole('columnheader',{name:'Today',exact:true}).count(),1);
 await page.evaluate(()=>window.showFixture({withheld:true}));
 await page.getByText(/Price details and the explanation are withheld/).waitFor();
 assert.equal(await page.getByText(/Investors rotate out of AI/).count(),0);
 assert.equal(await page.getByRole('button').count(),0);
 await page.evaluate(()=>window.showFixture({readOnly:true}));
 await page.getByText('Preview · not sent to Telegram',{exact:true}).waitFor();
 assert.equal(await page.getByRole('button',{name:/sector comparison|Mark reviewed|Leave unresolved/}).count(),0);
 await page.evaluate(()=>window.showFixture({inbox:true}));
 const record=page.locator('[data-kind="move"]');
 await record.locator(':scope > summary').click();
 await record.getByRole('button',{name:'Useful',exact:true}).click();
 await record.getByText('Rating saved.',{exact:true}).waitFor();
 assert.deepEqual((await page.evaluate(()=>window.actions)).find(a=>a.kind==='rate'),{kind:'rate',alertKind:'move',id:'authored-move',value:'useful'});
 await record.getByRole('button',{name:'Mark reviewed',exact:true}).click();
 await page.getByText('Review recorded. Your idea is unchanged.',{exact:true}).waitFor();
 assert.ok((await page.evaluate(()=>window.actions)).some(a=>a.kind==='review-move'&&a.id==='authored-move'&&a.action==='reviewed'));
 await record.locator(':scope > summary').click();
 await record.getByRole('region',{name:'Rate this alert'}).waitFor();
 for(const width of [1440,390,320]){
  await page.setViewportSize({width,height:1100});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await record.getByRole('region',{name:'Rate this alert'}).scrollIntoViewIfNeeded();
  await page.screenshot({path:path.join(out,'inbox-'+width+'.png'),animations:'disabled'});
 }
 await page.evaluate(()=>window.showFixture({inbox:true,company:true}));
 const company=page.locator('[data-kind="company"]');
 await company.getByText('Preview · not sent to Telegram',{exact:true}).waitFor();
 await company.locator(':scope > summary').click();
 await company.getByText(/Importance assessment: high · deal/).waitFor();
 await company.getByLabel('Delivery preview').getByText(/Routing preview · Telegram immediately/).waitFor();
 assert.equal(await company.locator('blockquote').count(),1);
 assert.equal(await company.locator('blockquote').innerText(),'Nvidia announced a new supply agreement.');
 await company.getByRole('button',{name:'Useful',exact:true}).click();
 await company.getByText('Rating saved.',{exact:true}).waitFor();
 for(const width of [1440,390,320]){
  await page.setViewportSize({width,height:1100});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await company.getByRole('region',{name:'Rate this alert'}).scrollIntoViewIfNeeded();
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  await company.getByRole('region',{name:'Rate this alert'}).screenshot({path:path.join(out,'company-rating-'+width+'.png'),animations:'disabled'});
  await page.screenshot({path:path.join(out,'company-routing-'+width+'.png'),animations:'disabled'});
 }
 await page.evaluate(()=>window.showFixture({inbox:true,company:true,actual:true}));
 await company.locator(':scope > summary').click();
 await company.getByLabel('Delivery route').getByText(/Delivery route · Telegram immediately/).waitFor();
 assert.equal(await company.getByText('Preview · not sent to Telegram',{exact:true}).count(),0);
 assert.equal(await company.getByLabel('Delivery preview').count(),0);
 for(const width of [1440,390,320]){
  await page.setViewportSize({width,height:1100});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  assert.equal(await company.locator('blockquote').count(),1);
  await company.getByLabel('Delivery route').scrollIntoViewIfNeeded();
  await page.screenshot({path:path.join(out,'company-actual-routing-'+width+'.png'),animations:'disabled'});
 }
 const beforeDaily=(await page.evaluate(()=>window.actions)).filter(a=>a.kind==='read-daily').length;
 await page.evaluate(()=>window.showFixture({inbox:true,daily:true}));
 await page.getByRole('group',{name:'Daily recaps and AI spending'}).waitFor();
 assert.equal((await page.evaluate(()=>window.actions)).filter(a=>a.kind==='read-daily').length,beforeDaily+1);
 await page.evaluate(()=>window.showFixture({inbox:true,daily:true,scoped:true}));
 await page.locator('[data-kind="move"]').waitFor();
 assert.equal(await page.getByRole('group',{name:'Daily recaps and AI spending'}).count(),0);
 assert.equal((await page.evaluate(()=>window.actions)).filter(a=>a.kind==='read-daily').length,beforeDaily+1);
 assert.deepEqual(errors,[]);assert.deepEqual(requests,[]);
 console.log(JSON.stringify({passed:13,viewports:[1440,390,320],network_requests:0,output:out}));
}catch(error){console.error(JSON.stringify({errors,output:out,body:(await page.locator('body').innerText()).slice(0,2200)}));throw error;}
finally{await browser.close();}
