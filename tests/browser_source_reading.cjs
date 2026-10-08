const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
let browser;
(async()=>{
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
 const page=await browser.newPage({viewport:{width:1440,height:1100},reducedMotion:'reduce'});
 const errors=[],external=[],paid=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',r=>{const u=new URL(r.request().url());if(!['127.0.0.1','localhost'].includes(u.hostname)){external.push(u.href);return r.abort();}if(/\/(sentiment|refresh|generate|event-review|evidence-review|brief)$/.test(u.pathname))paid.push(u.href);return r.continue();});
 const base=process.env.THESIS_TEST_URL,iid='c767e09f-35ea-5eaf-a626-ff5d3aa4709b';
 // Simulate one previously saved classifier's unrelated label. The source view
 // must still render the selected text instead of applying that classifier gate.
 await page.route('**/api/v1/workspace*',async route=>{
  const response=await route.fetch();const body=await response.json();
  body.result.sentiment.items[0].relevance='unrelated';body.result.sentiment.earlier_method=true;
  await route.fulfill({response,json:body});
 });
 await page.goto(base+'/?company='+iid+'&view=workspace');
 const panel=page.getByRole('region',{name:'News and social sentiment',exact:true});
 await panel.locator('.coverage-notice > summary').click();
 await panel.getByText(/Saved with an earlier analysis method/).waitFor();
 const raw=(await(await page.request.get(base+'/api/v1/workspace?instrument_id='+iid)).json()).result.sentiment;
 for(const channel of ['news','social']){
  await panel.getByRole('button',{name:channel==='news'?'Company news':'Reddit discussion',exact:true}).click();
  await panel.getByRole('button',{name:'Original sources',exact:true}).click();
  const original=panel.getByRole('region',{name:'Original selected sources',exact:true});
  const expected=raw.sources.filter(s=>!s.comparison_only&&s.kind===channel).sort((a,b)=>Date.parse(b.published_at)-Date.parse(a.published_at)||a.id.localeCompare(b.id));
  assert.deepEqual(await original.locator('article h3').allTextContents(),expected.map(s=>s.title));
  assert.deepEqual(await original.locator('.original-source-text').allTextContents(),expected.map(s=>s.body));
  assert.equal(await panel.locator('.sentiment-counts').count(),0);
  assert.equal(await panel.locator('.sentiment-tag').count(),0);
  await original.getByRole('button',{name:'Inspect original source ↗',exact:true}).first().click();
  await page.getByRole('dialog').waitFor();await page.keyboard.press('Escape');
  for(const width of [320,390,1440]){
   await page.setViewportSize({width,height:1100});
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`${channel} overflow ${width}`);
   if(channel==='news')await original.screenshot({path:`/private/tmp/thesis-original-sources-${width}.png`});
  }
  await panel.getByRole('button',{name:'AI interpretation',exact:true}).click();
  assert.ok(await panel.locator('.sentiment-counts').count());
 }
 await page.unroute('**/api/v1/workspace*');
 await page.route('**/api/v1/workspace*',async route=>{
  const response=await route.fetch();const body=await response.json();
  body.result.sentiment={...body.result.sentiment,withheld:true,items:[],sources:[],summary:{}};
  await route.fulfill({response,json:body});
 });
 await page.reload();await panel.getByText('This analysis is withheld because source access changed.',{exact:true}).waitFor();
 assert.equal(await panel.getByRole('button',{name:'Original sources',exact:true}).count(),0);
 assert.equal(await panel.getByRole('region',{name:'Original selected sources',exact:true}).count(),0);
 assert.equal(await panel.locator('.sentiment-tag,.sentiment-counts').count(),0);
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.deepEqual(paid,[]);
 console.log('Original source browser passed: identical selected text, chronological ordering, news/social separation, labels hidden, source inspection, earlier-method warning, access withdrawal, 320/390/1440 layouts, no source/model call.');
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();});
