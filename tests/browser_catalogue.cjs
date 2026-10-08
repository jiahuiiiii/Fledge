const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
let browser;
(async()=>{
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
 const page=await browser.newPage({viewport:{width:1440,height:1100},reducedMotion:'reduce'});
 const errors=[],external=[],acquisitions=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',r=>{const u=new URL(r.request().url());if(!['127.0.0.1','localhost'].includes(u.hostname)){external.push(u.href);return r.abort();}if(/\/(sentiment|refresh|generate|event-review|evidence-review|brief)$/.test(u.pathname))acquisitions.push(u.href);return r.continue();});
 const base=process.env.THESIS_TEST_URL;
 await page.goto(base);
 await page.getByRole('button',{name:'+ Add company',exact:true}).click();
 const modal=page.getByRole('dialog');
 await modal.getByLabel('Find a company').fill('NVDA');
 await modal.getByRole('button',{name:/Open NVDA|Add NVDA/}).click();
 for(const [symbol,date] of [['NVDA','26 Jul 2026'],['AMZN','30 Jun 2026'],['META','30 Jun 2026']]){
   await page.locator('.watch-item').filter({hasText:symbol}).click();
   await page.getByRole('tab',{name:'Fundamentals',exact:true}).click();
   const panel=page.getByRole('region',{name:'Financial performance',exact:true});
   await panel.getByRole('button',{name:'Latest quarter',exact:true}).click();
   await panel.getByText(new RegExp(date)).first().waitFor();
   assert.equal(await panel.locator('.financial-metric').count(),15);
   const cash=panel.locator('details').filter({has:page.locator('summary').filter({hasText:'Operating cash flow'})});
   await cash.locator('summary').click();
   assert.match(await cash.innerText(),/NetCashProvidedByUsedInOperatingActivities/);
   assert.match(await cash.innerText(),/Reported inputs/);
   const fcf=panel.locator('details').filter({has:page.locator('summary').filter({hasText:'Free cash flow'})});
   if(symbol!=='META') assert.match(await fcf.innerText(),/Unavailable/);
   for(const width of [320,390,1440]){
     await page.setViewportSize({width,height:1100});
     assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`${symbol} overflow ${width}`);
     const rows=page.locator('.metric-row');
     for(let i=0;i<await rows.count();i++){
       const value=await rows.nth(i).locator(':scope > strong').boundingBox();
       const period=await rows.nth(i).locator(':scope > span:last-child').boundingBox();
       assert.ok(value.x+value.width<=period.x,`${symbol} metric overlaps period ${width}`);
     }
     if(symbol==='NVDA'&&width===390)await page.locator('.metrics-table').screenshot({path:'/private/tmp/thesis-catalogue-mobile-metrics.png'});
     if(symbol==='NVDA')await page.screenshot({path:`/private/tmp/thesis-catalogue-${width}.png`,fullPage:true});
   }
   const url=new URL(page.url()),iid=url.searchParams.get('company');
   const state=(await(await page.request.get(base+'/api/v1/workspace?instrument_id='+iid)).json()).result;
   assert.equal(state.versions.length,0);assert.ok(!state.news_watch?.enabled);
 }
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.deepEqual(acquisitions,[]);
 console.log('Expanded catalogue browser passed: searchable company picker; actual-record NVIDIA/Amazon/Meta financial views and fiscal dates; missing FCF; 320/390/1440 layouts; no saved ideas, watches, source or model requests.');
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();});
