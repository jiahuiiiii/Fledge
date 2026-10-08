const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert=require('node:assert/strict');let browser;
(async()=>{
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto(process.env.THESIS_TEST_URL || 'http://127.0.0.1:8844');
 await page.locator('.watch-item').filter({hasText:'MSFT'}).click();
 await page.getByRole('tab',{name:'Valuation',exact:true}).click();
 const chart=page.getByRole('region',{name:'Analyst price targets',exact:true});
 await chart.getByRole('img',{name:/Last quote USD 110.00/}).waitFor();
 assert.match(await chart.innerText(),/−9.1% downside/);assert.match(await chart.innerText(),/\+14.1% upside/);assert.match(await chart.innerText(),/\+45.5% upside/);
 for(const width of [1920,1440,390,320]){
  await page.setViewportSize({width,height:1000});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await chart.screenshot({path:`/private/tmp/thesis-target-range-${width}.png`});
 }
 await page.setViewportSize({width:1440,height:1000});await page.evaluate(()=>scrollTo(0,0));
 await page.getByRole('button',{name:'Remove AAPL from sidebar',exact:true}).click();
 const group=page.getByRole('group',{name:'Removal actions'});await group.waitFor();
 await page.waitForFunction(()=>getComputedStyle(document.querySelector('.removal-notice-actions')).opacity==='1');
 const undo=group.getByRole('button',{name:'Undo',exact:true}),close=group.getByRole('button',{name:'Dismiss removal notice'});
 assert.equal((await undo.textContent()).trim(),'');assert.equal(await undo.locator('svg').count(),1);
 for(const width of [1920,1440,390,320]){
  await page.setViewportSize({width,height:1000});
  const u=await undo.boundingBox(),x=await close.boundingBox(),g=await group.boundingBox();
  assert.ok(x.x-u.x-u.width>=0 && x.x-u.x-u.width<=10,'Adjacent icons');
  assert.ok(g.x+g.width>width-40 && g.x+g.width<=width,'Right aligned group');
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.locator('.removal-notice').screenshot({path:`/private/tmp/thesis-removal-${width}.png`});
 }
 await page.setViewportSize({width:1440,height:1000});await undo.click();await page.locator('.watch-item').filter({hasText:'AAPL'}).waitFor();
 await page.getByRole('button',{name:'Remove AAPL from sidebar',exact:true}).click();await close.click();await group.waitFor({state:'hidden'});
 assert.deepEqual(errors,[]);console.log('Target range and icon banner passed at 320/390/1440/1920, including quote arithmetic, no overflow, adjacent icon-only controls, undo and dismiss.');
})().catch(e=>{console.error(e);process.exitCode=1}).finally(()=>browser?.close());
