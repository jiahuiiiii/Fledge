const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
let browser;
(async()=>{
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
 const page=await browser.newPage({viewport:{width:1440,height:1050},reducedMotion:'reduce'});
 const errors=[],external=[],paid=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',r=>{const u=new URL(r.request().url());if(!['127.0.0.1','localhost'].includes(u.hostname)){external.push(u.href);return r.abort();}if(/\/(sentiment|refresh|generate|event-review|evidence-review|brief)$/.test(u.pathname))paid.push(u.href);return r.continue();});
 const base=process.env.THESIS_TEST_URL,iid='c767e09f-35ea-5eaf-a626-ff5d3aa4709b';
 await page.goto(base+'/?company='+iid+'&view=updates');
 const region=page.getByRole('region',{name:'Research update inbox',exact:true});
 const expand=async()=>{for(const summary of await region.locator('.inbox-record > summary').all()){if(await summary.evaluate(e=>!e.parentElement.open))await summary.click();}};
 await region.locator('.inbox-record').first().waitFor();await expand();
 const update=region.locator('.sentiment-alert').filter({has:page.getByRole('heading',{name:'New reporting changes an earlier story',exact:true})});
 await update.waitFor();assert.equal(await region.locator('.sentiment-alert').count(),2);
 await update.getByText('Conflicting reports · compare with the earlier report',{exact:true}).click();
 const text=await update.innerText();
 assert.match(text,/neutral/);assert.match(text,/An unconfirmed report says Microsoft will close the service/);assert.match(text,/Microsoft denies that the service will close/);
 assert.match(text,/does not establish which claim is true/);
 await update.getByRole('button',{name:'Inspect earlier report ↗',exact:true}).click();
 await page.getByRole('dialog').waitFor();assert.match(await page.getByRole('dialog').innerText(),/unconfirmed report/);await page.keyboard.press('Escape');
 await update.getByRole('button',{name:'Inspect alert source ↗',exact:true}).click();
 await page.getByRole('dialog').waitFor();assert.match(await page.getByRole('dialog').innerText(),/denies that the service will close/);await page.keyboard.press('Escape');
 for(const width of [320,390,1440]){
  await page.setViewportSize({width,height:1050});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);
  await page.screenshot({path:`/private/tmp/thesis-reporting-update-${width}.png`,fullPage:true});
 }
 const exportResponse=await page.request.get(base+'/api/v1/research-review/export');assert.equal(exportResponse.status(),200);
 const html=await exportResponse.text();assert.match(html,/AI comparison: these reports appear to make conflicting claims/);assert.doesNotMatch(html,/Earlier AI-written summary/);assert.match(html,/Earlier report: Authored Microsoft service-closure report/);assert.match(html,/Microsoft denies that the service will close/);assert.doesNotMatch(html,/<script/);
 await update.getByRole('button',{name:'Mark reviewed',exact:true}).click();
 await update.waitFor({state:'hidden'});
 await region.getByLabel('Show updates').selectOption('all');await region.locator('.inbox-record').first().waitFor();await expand();assert.equal(await region.locator('.sentiment-alert').count(),2);assert.match(await update.innerText(),/Reviewed/);
 await page.reload();await region.getByLabel('Show updates').selectOption('all');await region.locator('.inbox-record').first().waitFor();await expand();assert.match(await update.innerText(),/Reviewed/);
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.deepEqual(paid,[]);
 console.log('Reporting update browser passed: neutral clarification alerts, both exact sources, source modals, independent review persistence, inert weekly export, 320/390/1440 layouts; no source/model calls.');
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();});
