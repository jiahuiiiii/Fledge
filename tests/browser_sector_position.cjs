const {chromium}=require(process.env.PLAYWRIGHT_MODULE);
const assert=require('node:assert/strict');
const fs=require('node:fs');
let browser;
(async()=>{
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
 const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[],external=[],writes=[];
 const folder=process.env.THESIS_SECTOR_SCREENSHOTS || '/private/tmp/thesis-sector-screenshots';fs.mkdirSync(folder,{recursive:true});
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',route=>{const r=route.request(),url=r.url();if(url.startsWith(process.env.THESIS_TEST_URL)){if(url.endsWith('/loading'))return route.fulfill({json:{result:null}});if(r.method()!=='GET'){writes.push(url);if(r.method()==='PUT'&&url.endsWith('/fmp/peers'))return route.continue();return route.fulfill({status:403,json:{error:'Authored test blocks unexpected mutation'}});}return route.continue();}if(url.startsWith('https://financialmodelingprep.com/image-stock/'))return route.fulfill({status:404,body:'Authored missing logo'});external.push(url);return route.abort();});
 await page.goto(process.env.THESIS_TEST_URL);await page.locator('.watch-item').filter({hasText:'MSFT'}).click();await page.getByRole('tab',{name:'Outlook',exact:true}).click();
 const outlook=page.locator('.outlook-page'),panel=outlook.getByRole('region',{name:'Competitor position',exact:true});
 await panel.getByRole('heading',{name:'Where MSFT stands among competitors',exact:true}).waitFor();
 assert.equal(await outlook.locator('.outlook-company-detail').first().evaluate(e=>e.open),false);
 await panel.locator('.position-group > summary').click();
 const peer=panel.getByLabel('Sector competitor 1');await peer.focus();await page.keyboard.press('n');await page.keyboard.press('Enter');assert.equal(await peer.inputValue(),'NVDA');
 await panel.getByLabel('Why compare NVDA').fill('Authored comparison of growth and margins; products differ.');
 await panel.getByRole('button',{name:'Apply comparison group',exact:true}).click();
 await panel.locator('.position-reading').getByText('MSFT is below NVDA.',{exact:true}).waitFor();assert.equal(writes.length,0);
 const rows=panel.locator('.position-bar-row');assert.equal(await rows.count(),2);assert.match(await rows.first().innerText(),/23.1%/);
 const evidence=rows.first().getByRole('button',{name:'Evidence',exact:true});await evidence.focus();await page.keyboard.press('Enter');const dialog=page.getByRole('dialog');assert.match(await dialog.innerText(),/Exact value: 23.076923/);assert.match(await dialog.innerText(),/Revenues|RevenueFromContract/);await page.keyboard.press('Escape');assert.equal(await evidence.evaluate(e=>document.activeElement===e),true);
 await panel.getByLabel('Competitor measure').focus();await page.keyboard.press('o');await page.keyboard.press('Enter');await panel.locator('.position-reading').getByText('MSFT is above NVDA.',{exact:true}).waitFor();
 for(const width of [1440,980,390,320]){await page.setViewportSize({width,height:1100});await panel.locator('.position-map-wrap').scrollIntoViewIfNeeded();assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:`${folder}/reported-map-${width}.png`,animations:'disabled'});await panel.locator('.position-reading').scrollIntoViewIfNeeded();await page.screenshot({path:`${folder}/reported-bars-${width}.png`,animations:'disabled'});}
 await page.setViewportSize({width:1440,height:1100});
 await panel.getByRole('button',{name:'Save peers for this company',exact:true}).click();await panel.getByText('Using your saved comparison companies.',{exact:false}).waitFor();assert.equal(writes.length,1);
 await page.getByRole('tab',{name:'Financials',exact:true}).click();const financial=page.locator('.financials-story').getByRole('region',{name:'Competitor position',exact:true});await financial.locator('.position-reading').getByText('MSFT is below NVDA.',{exact:true}).waitFor();
 await page.getByRole('tab',{name:'Outlook',exact:true}).click();await panel.locator('.position-group > summary').click();
 if(!await panel.locator('.position-group').evaluate(e=>e.open))await panel.locator('.position-group > summary').click();
 await panel.getByRole('button',{name:'Add peer',exact:true}).click();assert.equal(await panel.getByLabel('Sector competitor 2').inputValue(),'');
 await page.getByRole('tab',{name:'Financials',exact:true}).click();await page.getByRole('tab',{name:'Outlook',exact:true}).click();await panel.getByLabel('Sector competitor 2').waitFor();assert.equal(await panel.getByLabel('Sector competitor 2').inputValue(),'');
 // Future figures are authored controlled responses, separate from original filings.
 await page.route('**/sector-position*',async route=>{const response=await route.fetch(),body=await response.json();for(const m of body.result.members){m.consensus={status:'saved',snapshot_id:'authored-'+m.symbol,first_observed_at:'2026-10-09T00:00:00Z',data:{method:'fmp-research-1',forecasts:[{period_type:'annual',period_end:'2026-12-31',currency:'USD',metrics:[{key:'revenue',average:'100'}]},{period_type:'annual',period_end:'2027-12-31',currency:'USD',metrics:[{key:'revenue',average:m.symbol==='MSFT'?'120':'130'}]}]}};}return route.fulfill({response,json:body});});
 await page.getByRole('tab',{name:'Financials',exact:true}).click();await page.getByRole('tab',{name:'Outlook',exact:true}).click();await panel.getByRole('button',{name:'Expected growth',exact:true}).click();
 await panel.getByLabel('Competitor forecast year').focus();await page.keyboard.press('End');await page.keyboard.press('Enter');await panel.locator('.position-reading').getByText('MSFT is below NVDA.',{exact:true}).waitFor();assert.match(await panel.innerText(),/forecast-to-forecast/);assert.match(await panel.locator('.position-bar-row').first().innerText(),/20.0%/);
 await panel.locator('.position-forward-details > summary').click();assert.match(await panel.locator('.position-forward-details').innerText(),/non-gaap/);
 for(const width of [1440,320]){await page.setViewportSize({width,height:1100});await panel.locator('.position-reading').scrollIntoViewIfNeeded();assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:`${folder}/expected-${width}.png`,animations:'disabled'});}
 await page.emulateMedia({reducedMotion:'reduce'});
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.equal(writes.length,1);
 console.log(JSON.stringify({journey:'competitor position',authored:true,viewports:[1440,980,390,320],peerWrites:1,sourceRequests:0,aiRequests:0,errors}));await browser.close();
})().catch(async e=>{console.error(e);if(browser)await browser.close();process.exit(1);});
