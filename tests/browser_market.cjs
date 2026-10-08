const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
 try {
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 let paid=0;page.on('request',r=>{if(r.url().endsWith('/brief'))paid++;});
 await page.goto(process.env.THESIS_TEST_URL);
 await page.getByRole('heading',{name:'Microsoft',exact:true}).waitFor();
 await page.getByRole('heading',{name:'A reported contract remains unconfirmed'}).waitFor();
 const region=page.getByRole('region',{name:'Company news and briefing'});
 assert.match(await region.innerText(),/AI summary/);
 await region.locator('.brief-unknowns summary').click();
 const omission=region.getByText(/1 source passage containing ellipsis markers was excluded from AI input/);
 await omission.waitFor();
 assert.equal(await page.locator('.news-item').count(),5);
 await page.getByRole('button',{name:'Show all 7 stories'}).click();
 assert.equal(await page.locator('.news-item').count(),7);
 await page.getByRole('button',{name:'Show fewer stories'}).click();
 await page.locator('.market-point .source-link').first().click();
 const dialog=page.getByRole('dialog');
 await dialog.getByText('NEWS · PROVIDER SNIPPET',{exact:true}).waitFor();
 assert.match(await dialog.innerText(),/has not confirmed/);
 assert.match(await dialog.innerText(),/unfinished market fixture mentions future terms\.\.\./);
 assert.match(await dialog.getByRole('link',{name:'Read original article ↗'}).getAttribute('href'),/^https:\/\/example.test\//);
 await page.keyboard.press('Escape');
 await page.screenshot({path:'/private/tmp/thesis-market-synthetic-desktop.png',fullPage:true});
 for(const width of [320,390,768,1056,1440]) {
   await page.setViewportSize({width,height:960});
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Market overflow ${width}`);
   await omission.scrollIntoViewIfNeeded();
   const bounds=await omission.boundingBox();
   assert.ok(bounds.x>=0 && bounds.x+bounds.width<=width,`Shared omission message clipped at ${width}`);
   if(width===390) await page.screenshot({path:'/private/tmp/thesis-market-synthetic-mobile.png',fullPage:true});
 }
 await page.getByRole('button',{name:'Save my reasoning',exact:true}).click();
 await page.getByLabel('My reasoning',{exact:true}).fill('Synthetic pitch test: reported contract remains unconfirmed; inspect future margin changes.');
 await page.getByRole('button',{name:'Save draft',exact:true}).click();
 await page.reload();
 await page.getByRole('button',{name:'Edit idea',exact:true}).waitFor();
 await page.getByRole('heading',{name:'A reported contract remains unconfirmed'}).waitFor();
 await region.locator('.brief-unknowns summary').click();
 await omission.waitFor();
 assert.equal(paid,0,'Opening and refreshing must not trigger paid calls');
 let empty=true,hideBrief=false;
 await page.route('**/api/v1/workspace*',async route=>{
   const response=await route.fetch();const body=await response.json();
   Object.assign(body.result.market.status,{news_count:empty?0:null,news_error:empty?null:'Finnhub access was denied or rate-limited.'});
   if(hideBrief) body.result.market_brief=null;
   await route.fulfill({response,json:body});
 });
 await page.reload();await page.getByText(/No articles returned for the seven-day window/).waitFor();
 assert.equal(await page.locator('.news-item').count(),5);
 empty=false;await page.reload();await page.getByText(/News check unavailable/).waitFor();
 assert.equal(await page.getByText(/No articles returned for the seven-day window/).count(),0);
 // Shared brief availability follows its own stronger-model configuration,
 // independently of the legacy passage-selection model.
 hideBrief=true;
 let briefingEnabled=false,legacyEnabled=true,unresolved=0;
 await page.route('**/api/v1/model-status',route=>route.fulfill({json:{result:{enabled:legacyEnabled,briefing_enabled:briefingEnabled,comparison_enabled:briefingEnabled,budget:{unresolved}}}}));
 await page.reload();
 const summarise=page.getByRole('button',{name:'Summarise sources',exact:true});
 await summarise.waitFor();
 await region.getByText(/AI briefing is unavailable in this workspace/).waitFor();
 assert.equal(await summarise.isDisabled(),true,'Mini availability must not enable the stronger shared brief');
 briefingEnabled=true;legacyEnabled=false;
 await page.reload();await summarise.waitFor();
 await page.waitForFunction(()=>[...document.querySelectorAll('button')].some(b=>b.textContent==='Summarise sources'&&!b.disabled));
 assert.equal(await summarise.isEnabled(),true,'Shared brief can work when only its stronger model is configured');
 assert.equal(await region.getByText(/AI briefing is unavailable in this workspace/).count(),0);
 unresolved=1;
 await page.reload();await summarise.waitFor();
 await region.getByText(/Another AI request is in progress or awaiting charge confirmation/).waitFor();
 assert.equal(await summarise.isDisabled(),true,'An outstanding charge still blocks the stronger shared brief');
 assert.equal(paid,0,'Availability checks must not generate a briefing');
 assert.deepEqual(errors,[]);
 console.log('Market browser journey passed: cached sources and omission disclosure, excluded fragment retained in original, AI attribution, original link, draft persistence, empty/outage distinction, independent stronger-model availability, unresolved-charge block, mobile widths, no paid calls.');
 } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exitCode=1;});
