const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs');let browser;
(async()=>{
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
 const page=await browser.newPage({viewport:{width:1440,height:1050},reducedMotion:'reduce'}),errors=[],external=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',r=>{const u=new URL(r.request().url());if(!['127.0.0.1','localhost'].includes(u.hostname)){external.push(u.href);return r.abort();}return r.continue();});
 await page.route('**/api/v1/model-status',r=>r.fulfill({json:{result:{briefing_enabled:true,budget:{unresolved:0,remaining_usd:'10'}}}}));
 const base=process.env.THESIS_TEST_URL,iid='c767e09f-35ea-5eaf-a626-ff5d3aa4709b';
 await page.goto(base+'/?company='+iid+'&view=workspace');
 await page.getByRole('tab',{name:'Expectations',exact:true}).click();
 const panel=page.getByRole('region',{name:'Company expectations',exact:true});await panel.getByLabel('Saved expectations').waitFor();
 assert.equal(await panel.locator('.expectation-card').count(),2);
 assert.match(await panel.innerText(),/Reported management outlook/);assert.match(await panel.innerText(),/INDIVIDUAL VIEW · NOT CONSENSUS/);
 assert.match(await panel.innerText(),/calendar 2026/);assert.match(await panel.innerText(),/Not stated in the selected passages/);
 const records=(await(await page.request.get(base+'/api/v1/companies/'+iid+'/expectations')).json()).result;
 assert.equal(records.items.length,2);
 await panel.getByLabel('Saved expectations').selectOption(records.items[1].id);assert.equal(await panel.locator('.expectation-card').count(),1);
 await panel.getByLabel('Saved expectations').selectOption(records.latest.id);assert.equal(await panel.locator('.expectation-card').count(),2);
 await panel.getByText('Inspect expectation evidence',{exact:true}).first().click();
 await panel.getByRole('button',{name:'Open expectation source ↗',exact:true}).first().click();await page.getByRole('dialog').waitFor();assert.match(await page.getByRole('dialog').innerText(),/calendar 2026/);await page.keyboard.press('Escape');
 const dl=page.waitForEvent('download');await panel.getByRole('link',{name:'Download this expectation reading',exact:true}).click();const html=fs.readFileSync(await(await dl).path(),'utf8');assert.match(html,/calendar 2026/);assert.match(html,/Harbor Research/);assert.doesNotMatch(html,/<script/);
 await panel.getByRole('button',{name:'Draft a research question ↗',exact:true}).first().click();await page.getByRole('dialog').waitFor();assert.match(await page.getByLabel('Research question',{exact:true}).inputValue(),/What has changed since/);await page.keyboard.press('Escape');
 const before=(await(await page.request.get(base+'/api/v1/workspace?instrument_id='+iid)).json()).result;
 assert.equal(before.versions.length,0);assert.ok(!before.news_watch?.enabled);
 await panel.getByRole('button',{name:'Extract from saved news',exact:true}).click();await panel.getByRole('button',{name:'Extract from saved news',exact:true}).waitFor();
 assert.equal((await(await page.request.get(base+'/api/v1/companies/'+iid+'/expectations')).json()).result.items.length,2);
 for(const width of [320,390,1440]){await page.setViewportSize({width,height:1050});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);await page.screenshot({path:`/private/tmp/thesis-expectations-${width}.png`,fullPage:true});}
 // A current matching reading can remain selectable even outside the first history page.
 await page.route('**/api/v1/companies/*/expectations',async r=>{if(r.request().method()!=='GET')return r.continue();const response=await r.fetch();const body=await response.json();body.result.items=body.result.items.filter(i=>i.id!==body.result.current_reading.id);await r.fulfill({response,json:body});});
 await page.reload();await page.getByRole('tab',{name:'Expectations',exact:true}).click();await panel.getByLabel('Saved expectations').waitFor();assert.equal(await panel.getByLabel('Saved expectations').inputValue(),records.current_reading.id);assert.equal(await panel.locator('.expectation-card').count(),2);await page.unroute('**/api/v1/companies/*/expectations');
 await panel.getByRole('button',{name:'Open reported performance ↗',exact:true}).click();assert.equal(await page.getByRole('tab',{name:'Fundamentals',exact:true}).getAttribute('aria-selected'),'true');
 await page.getByRole('tab',{name:'Expectations',exact:true}).click();await panel.getByLabel('Saved expectations').waitFor();
 await page.route('**/api/v1/companies/*/expectations',r=>r.request().method()==='POST'?r.fulfill({status:503,json:{result:{errors:[{error_message:'Authored extraction unavailable.'}]}}}):r.continue());
 await panel.getByRole('button',{name:'Extract from saved news',exact:true}).click();await panel.getByRole('alert').waitFor();assert.equal(await panel.locator('.expectation-card').count(),2);
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);console.log('Expectations browser passed: separate management/analyst views, missing values/horizons, source inspection, inert export, draft without save, cache reuse, immutable history, failure preserves saved reading, navigation and 320/390/1440 layouts. No paid calls.');
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();});
