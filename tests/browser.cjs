// Optional end-to-end check. Run against a fresh fictional test instance (see README).
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
let browser,page;
(async()=>{
 browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{})});
 const context=await browser.newContext({viewport:{width:1440,height:1060},reducedMotion:'reduce'});
 page=await context.newPage();
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto((process.env.THESIS_TEST_URL||'http://127.0.0.1:8842')+'/?company=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa');
 await page.getByRole('heading',{name:'Northstar Software',exact:true}).waitFor();
 await page.screenshot({path:'/private/tmp/thesis-desktop-initial.png',fullPage:true});
 await page.getByRole('button',{name:'Read source',exact:true}).first().click();
 await page.getByRole('dialog').waitFor();
 assert.match(await page.getByRole('dialog').innerText(),/AUTHORED FICTIONAL SOURCE/);
 await page.keyboard.press('Escape');
 await page.getByRole('button',{name:'Unresolved',exact:true}).click();
 await page.getByRole('status').filter({hasText:'Question left unresolved'}).waitFor();
 await page.getByRole('button',{name:'Save my reasoning',exact:true}).click();
 await page.getByLabel('My reasoning',{exact:true}).fill('Enterprise renewals may sustain growth, but slower growth or weaker margins would challenge my idea.');
 await page.getByRole('button',{name:'Save draft',exact:true}).click();
 await page.getByRole('status').filter({hasText:'Draft saved'}).waitFor();
 console.log('Draft saved; testing reload');
 await page.reload();
 await page.getByRole('button',{name:'Edit idea',exact:true}).click();
 await page.getByRole('dialog',{name:'Edit your idea',exact:true}).waitFor();
 assert.match(await page.getByLabel('My reasoning',{exact:true}).inputValue(),/Enterprise renewals/);
 await page.getByRole('button',{name:'Add condition',exact:true}).click();
 await page.getByRole('button',{name:'Add condition',exact:true}).click();
 await page.getByLabel('Metric',{exact:true}).nth(1).selectOption('operating_margin');
 await page.getByLabel('Percent',{exact:true}).nth(1).fill('20');
 assert.equal(await page.getByRole('button',{name:'Approve monitoring',exact:true}).isEnabled(),false);
 await page.getByRole('checkbox').check();
 await page.getByRole('button',{name:'Remove condition 2',exact:true}).click();
 assert.equal(await page.getByRole('checkbox').isChecked(),false);
 await page.getByRole('button',{name:'Add condition',exact:true}).click();
 await page.getByLabel('Metric',{exact:true}).nth(1).selectOption('operating_margin');
 await page.getByLabel('Percent',{exact:true}).nth(1).fill('20');
 await page.getByRole('checkbox').check();
 await page.getByLabel('Percent',{exact:true}).nth(0).fill('16');
 assert.equal(await page.getByRole('checkbox').isChecked(),false);
 await page.getByLabel('Percent',{exact:true}).nth(0).fill('15');
 await page.getByRole('checkbox').check();
 await page.getByRole('button',{name:'Approve monitoring',exact:true}).click();
 await page.getByText('All conditions met',{exact:true}).waitFor();
 await page.getByRole('button',{name:'Load next recorded development'}).click();
 await page.getByRole('heading',{name:'Renewal timing needs confirmation',exact:true}).waitFor();
 await page.getByRole('button',{name:'Load next recorded development'}).click();
 await page.getByText('Your idea needs a review',{exact:true}).waitFor();
 await page.getByRole('button',{name:'Mark reviewed',exact:true}).click();
 await page.getByText(/Marked reviewed ·/).waitFor();
 await page.getByRole('button',{name:'Load next recorded development'}).click();
 await page.getByText(/Sources unavailable or too old at this assessment/).waitFor();
 await page.getByRole('tab',{name:'Source coverage',exact:true}).click();
 assert.equal(await page.getByText('Unavailable',{exact:true}).count(),2);
 await page.getByRole('button',{name:'Load next recorded development'}).click();
 await page.getByRole('tab',{name:'Evidence radar',exact:true}).click();
 await page.getByRole('heading',{name:'Revenue growth was corrected to 13%',exact:true}).waitFor();
 await page.locator('.idea-panel').getByText('13%',{exact:true}).waitFor();
 assert.equal(await page.locator('.idea-panel .warning').count(),0);
 assert.equal(await page.getByRole('heading',{name:'Revenue growth slowed to 12%',exact:true}).count(),0);
 await page.getByRole('button',{name:'History',exact:true}).click();
 const oldRecord = await page.getByLabel('Record',{exact:true}).locator('option').filter({hasText:'Revision 2 · 24 Oct 2025 · Condition not met'}).first().getAttribute('value');
 await page.getByLabel('Record',{exact:true}).selectOption(oldRecord);
 const main=page.getByRole('main');
 await main.getByText('12%',{exact:true}).waitFor();
 await main.getByRole('button',{name:'Source',exact:true}).last().click();
 assert.match(await page.getByRole('dialog').innerText(),/growth of 12%/);
 await page.keyboard.press('Escape');
 await page.getByRole('button',{name:'Workspace',exact:true}).click();
 await page.screenshot({path:'/private/tmp/thesis-desktop-review.png',fullPage:true});
 for(const width of [390,320,768,1056]){
   await page.setViewportSize({width,height:900});
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow at ${width}`);
   if(width===390)await page.screenshot({path:'/private/tmp/thesis-mobile-review.png',fullPage:true});
 }
 // Company switching works on mobile and keeps reasoning separate.
 await page.setViewportSize({width:320,height:900});
 const aurora='bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
 const northstar='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
 await page.getByLabel('Company',{exact:true}).selectOption(aurora);
 await page.getByRole('heading',{name:'Aurora Devices',exact:true}).waitFor();
 await page.waitForFunction(()=>document.querySelector('.main-workspace')?.getAttribute('aria-busy')==='false');
 assert.match(await page.getByRole('main').innerText(),/No price history available/);
 assert.doesNotMatch(await page.getByRole('main').innerText(),/renewal|contract-level/i);
 await page.getByRole('button',{name:'Save my reasoning',exact:true}).click();
 await page.getByLabel('My reasoning',{exact:true}).fill('Sensor launches could support Aurora demand; component costs remain uncertain.');
 await page.getByRole('button',{name:'Add condition',exact:true}).click();
 await page.getByLabel('Percent',{exact:true}).fill('5');
 await page.getByRole('checkbox').check();
 await page.getByRole('button',{name:'Approve monitoring',exact:true}).click();
 await page.getByText('All conditions met',{exact:true}).waitFor();
 await page.getByRole('button',{name:'Load next recorded development'}).click();
 await page.getByRole('button',{name:'My ideas',exact:true}).click();
 await page.locator('.idea-summary').filter({hasText:'Aurora Devices'}).waitFor();
 assert.equal(await page.locator('.idea-summary').count(),1); // Shared scope remains Aurora.
 for(let n=0;n<2;n++){
   await page.locator('.idea-summary').filter({hasText:'Aurora Devices'}).click();
   await page.getByRole('main').getByText('Sensor launches could support Aurora demand; component costs remain uncertain.',{exact:true}).waitFor();
   await page.getByRole('button',{name:'My ideas',exact:true}).click();
 }
 for(let n=0;n<2;n++){
   await page.getByRole('button',{name:'Updates',exact:true}).click();
   await page.getByLabel('Inbox company',{exact:true}).selectOption(northstar);
   await page.locator('.change-summary').filter({hasText:'NSTR'}).first().click();
   const record=await page.getByLabel('Record',{exact:true}).inputValue();
   assert.equal(new URL(page.url()).searchParams.get('evaluation'),record);
   await page.reload();
   assert.equal(await page.getByLabel('Record',{exact:true}).inputValue(),record);
 }
 await page.getByRole('button',{name:'Updates',exact:true}).click();
 await page.getByLabel('Show updates',{exact:true}).selectOption('all');
 assert.match(await page.locator('.change-collection').innerText(),/Revenue growth: 18% \(2025-Q2\) → 12% \(2025-Q3\)/);
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'update overflow at 320');
 await page.screenshot({path:'/private/tmp/thesis-updates-mobile.png',fullPage:true});
 // Broken assessment links must never silently display a different record.
 const invalid=new URL(page.url());invalid.searchParams.set('view','history');invalid.searchParams.set('evaluation','missing-record');
 await page.goto(invalid.toString());
 await page.getByRole('heading',{name:'This assessment is unavailable',exact:true}).waitFor();
 await page.getByLabel('Company',{exact:true}).selectOption(northstar);
 await page.getByRole('button',{name:'Workspace',exact:true}).click();
 await page.setViewportSize({width:1056,height:900});
 await page.getByRole('button',{name:'Edit idea',exact:true}).click();
 await page.getByRole('dialog',{name:'Edit your idea',exact:true}).waitFor();
 await page.getByRole('button',{name:'Archive idea and stop monitoring',exact:true}).click();
 await page.getByText('archived',{exact:true}).waitFor();
 // Every revision, including unassessed draft and archive, remains inspectable.
 await page.getByRole('button',{name:'History',exact:true}).click();
 await page.getByLabel('Record',{exact:true}).selectOption({label:'Revision 1 · draft · saved definition'});
 assert.match(await page.getByRole('main').innerText(),/Enterprise renewals/);
 await page.getByLabel('Record',{exact:true}).selectOption({label:'Revision 3 · archived · saved definition'});
 assert.match(await page.getByRole('main').innerText(),/Not evaluated/);
 await page.getByLabel('Show',{exact:true}).selectOption('unreviewed');
 assert.equal(await page.getByLabel('Record',{exact:true}).locator('option').filter({hasText:'24 Oct 2025'}).count(),0);
 // Two tabs retain their text and force explicit saved-versus-draft resolution.
 await page.setViewportSize({width:1056,height:900});
 await page.getByRole('button',{name:'Edit idea',exact:true}).click();
 await page.getByLabel('My reasoning',{exact:true}).fill('Unsaved reasoning from the first tab.');
 const other=await page.context().newPage();
 await other.goto((process.env.THESIS_TEST_URL||'http://127.0.0.1:8842')+'/?company=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa');
 await other.getByRole('button',{name:'Edit idea',exact:true}).click();
 await other.getByLabel('My reasoning',{exact:true}).fill('The second tab saved a different interpretation.');
 await other.getByRole('button',{name:'Save draft',exact:true}).click();
 await other.getByRole('status').filter({hasText:'Draft saved'}).waitFor();
 await page.getByRole('button',{name:'Save draft',exact:true}).click();
 const comparison=page.getByRole('region',{name:'Resolve conflicting edits'});
 await comparison.waitFor();
 assert.match(await comparison.innerText(),/second tab saved/);
 assert.match(await comparison.innerText(),/Unsaved reasoning/);
 assert.equal(await page.getByRole('button',{name:'Save draft',exact:true}).isEnabled(),false);
 await page.getByRole('button',{name:'Keep my draft as a new revision',exact:true}).click();
 await page.getByRole('button',{name:'Save draft',exact:true}).click();
 await page.getByRole('status').filter({hasText:'Draft saved'}).waitFor();
 await page.reload();
 await page.locator('.idea-panel').getByText('Unsaved reasoning from the first tab.',{exact:true}).waitFor();
 await other.close();
 // Render the real unavailable-fact contract without altering the fixture database.
 await page.getByRole('button',{name:'Workspace',exact:true}).click();
 await page.route('**/api/v1/workspace*',async route=>{
   const response=await route.fetch();const payload=await response.json();
   payload.result.fundamentals=payload.result.fundamentals.map(f=>f.metric==='operating_margin'?{...f,value:null,status:'unavailable',document_version_id:null,reason:'No compatible quarterly margin observation'}:f);
   await route.fulfill({response,json:payload});
 });
 await page.reload();
 await page.getByRole('tab',{name:'Fundamentals',exact:true}).click();
 await page.getByText('No compatible quarterly margin observation',{exact:true}).waitFor();
 assert.equal(await page.locator('.metric-row').nth(1).isDisabled(),true);
 await page.unroute('**/api/v1/workspace*');
 // A republished reported claim retains its original facts and both source links.
 await page.route('**/api/v1/workspace*',async route=>{
   const response=await route.fetch();const payload=await response.json();const d=payload.result;
   const claim=d.claims.find(c=>c.kind==='reported' && d.observations.some(o=>o.document_version_id===c.document_version_id && o.period===d.demo.period) && !d.documents.some(v=>v.supersedes_id===c.document_version_id));
   const original=d.documents.find(v=>v.id===claim.document_version_id);
   const copy={...original,id:'browser-copy',source:'Fictional syndicated wire',title:'Republished source'};
   d.documents.push(copy);claim.source_version_ids=[original.id,copy.id];claim.origin_keys=['company'];claim.document_version_id=copy.id;
   await route.fulfill({response,json:payload});
 });
 await page.getByRole('button',{name:'Workspace',exact:true}).click();
 await page.reload();
 const provenance=page.locator('.source-provenance').first();
 await provenance.getByText('2 source versions · 1 declared origin',{exact:true}).click();
 assert.equal(await provenance.getByRole('button').count(),2);
 await provenance.getByRole('button').last().click();
 assert.match(await page.getByRole('dialog').innerText(),/Republished source/);
 await page.keyboard.press('Escape');
 await page.unroute('**/api/v1/workspace*');
 // UI-only mocked selection: browser tests must never trigger a paid call.
 let selectionReady=false, selectionRequests=0;
 await page.route('**/api/v1/model-status',route=>route.fulfill({json:{result:{enabled:true,budget:{unresolved:0}}}}));
 await page.route('**/api/v1/research/selection',async route=>{
   selectionRequests++;selectionReady=true;
   await route.fulfill({json:{result:{ready:true}}});
 });
 await page.route('**/api/v1/workspace*',async route=>{
   const response=await route.fetch();const payload=await response.json();
   if(selectionReady){ const d=payload.result.documents[0]; payload.result.selected_passages={
     limitation:'AI selected these original passages. Selection can omit relevant context.',omitted_passage_count:1,
     passages:[{id:d.id+':0',document_id:d.id,quote:d.body,source:d.source,published_at:d.published_at}]}; }
   await route.fulfill({response,json:payload});
 });
 await page.reload();
 await page.getByRole('button',{name:'Select key passages',exact:true}).click();
 const passages=page.getByRole('region',{name:'Source passage brief'});
 await passages.getByText(/1 source passages were not selected/).waitFor();
 assert.equal(selectionRequests,1);
 await passages.getByRole('button').first().click();
 await page.getByRole('dialog').waitFor();
 await page.keyboard.press('Escape');
 for(const width of [320,390,1440]){
   await page.setViewportSize({width,height:960});
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`passage overflow at ${width}`);
 }
 await page.screenshot({path:'/private/tmp/thesis-passages-desktop.png',fullPage:true});
 // An ambiguous request immediately refreshes the paused state, without a retry.
 selectionReady=false;
 await page.unroute('**/api/v1/model-status');
 let ambiguous=false;
 await page.route('**/api/v1/model-status',route=>route.fulfill({json:{result:{enabled:true,budget:{unresolved:ambiguous?1:0}}}}));
 await page.unroute('**/api/v1/research/selection');
 await page.route('**/api/v1/research/selection',async route=>{
   ambiguous=true;
   await route.fulfill({status:422,json:{result:{errors:[{error_message:'Request charge needs reconciliation'}]}}});
 });
 await page.reload();
 await page.getByRole('button',{name:'Select key passages',exact:true}).click();
 await passages.getByText(/Another AI request is in progress or awaiting charge confirmation/).waitFor();
 assert.equal(await page.getByRole('button',{name:'Select key passages',exact:true}).isDisabled(),true);
 assert.ok(await page.getByRole('button',{name:'Read source',exact:true}).count()>0);
 // Empty source state never invites an impossible paid action.
 await page.unroute('**/api/v1/workspace*');
 await page.route('**/api/v1/workspace*',async route=>{
   const response=await route.fetch();const payload=await response.json();
   Object.assign(payload.result,{documents:[],claims:[],observations:[],selected_passages:null});
   await route.fulfill({response,json:payload});
 });
 await page.reload();
 await passages.getByText('No permitted source passages available.',{exact:true}).waitFor();
 assert.equal(await page.getByRole('button',{name:'Select key passages',exact:true}).count(),0);
 assert.deepEqual(errors,[]);
 console.log('Browser journey passed: sources, unresolved, draft persistence, explicit approval, mixed outcome, review, outage, restatement, exact history, archive/draft history, two-tab conflict resolution, approval reset after removal, missing fundamentals, 320–1440px layouts, mobile company switching, separate ideas, repeated navigation, exact assessment URL reload, unavailable links, metric-period labels, copied-source provenance; no page errors.');
 await browser.close();
})().catch(async error=>{console.error(error);if(page){console.error(await page.locator('body').innerText());await page.screenshot({path:'/private/tmp/thesis-browser-failure.png',fullPage:true})}if(browser)await browser.close();process.exit(1)});
