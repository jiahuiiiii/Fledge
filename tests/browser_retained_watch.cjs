const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
let browser;
(async()=>{
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
 const page=await browser.newPage({viewport:{width:1440,height:1050},reducedMotion:'reduce'});
 const errors=[],external=[],paid=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',r=>{const u=new URL(r.request().url());if(!['127.0.0.1','localhost'].includes(u.hostname)){external.push(u.href);return r.abort();}if(/\/(sentiment|refresh|generate|event-review|evidence-review|brief|idea-alert-check)$/.test(u.pathname)){paid.push(u.href);return r.abort();}return r.continue();});
 const base=process.env.THESIS_TEST_URL,iid='528be36b-8e44-57e9-a9fa-fbd2ee8bbdd1';
 await page.goto(base+'/?company='+iid+'&view=updates');
 const inbox=page.getByRole('region',{name:'Research update inbox',exact:true});
 await inbox.locator('.inbox-record').first().waitFor();
 assert.equal(await inbox.locator('.inbox-record').count(),1);
 await inbox.locator('.inbox-record > summary').click();
 const pending=inbox.locator('.sentiment-alert');assert.match(await pending.innerText(),/\$3.2/);
 await pending.getByRole('button',{name:'Inspect alert source ↗',exact:true}).first().click();
 const dialog=page.getByRole('dialog');await dialog.waitFor();assert.match(await dialog.innerText(),/cleared the way for digital publishers/);assert.match(await dialog.innerText(),/after alleging/);await page.keyboard.press('Escape');
 for(const width of [320,390,1440]){await page.setViewportSize({width,height:1050});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await inbox.screenshot({path:`/private/tmp/thesis-retained-watch-${width}.png`});}
 const response=await page.request.get(base+'/api/v1/research-review/export?days=0&review=all');assert.equal(response.status(),200);const html=await response.text();assert.match(html,/-1.7%/);assert.match(html,/\$3.2/);assert.doesNotMatch(html,/<script/);
 await pending.getByRole('button',{name:'Leave unresolved',exact:true}).click();
 await inbox.getByLabel('Show updates').selectOption('all');
 await page.waitForFunction(()=>document.querySelectorAll('.inbox-record').length===2);
 const expand=async()=>{for(const row of await inbox.locator('.inbox-record > summary').all()){if(await row.evaluate(e=>!e.parentElement.open))await row.click();}};
 await expand();assert.match(await inbox.innerText(),/Reviewed/);assert.match(await inbox.innerText(),/Left unresolved/);
 await page.reload();await inbox.getByLabel('Show updates').selectOption('all');await page.waitForFunction(()=>document.querySelectorAll('.inbox-record').length===2);await expand();assert.match(await inbox.innerText(),/Reviewed/);assert.match(await inbox.innerText(),/Left unresolved/);
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.deepEqual(paid,[]);
 console.log('Retained watch browser passed: actual Alphabet excerpts, authored arrival/failure timeline, two alerts with independent review states, source inspection, full export, reload, 320/390/1440; no provider requests.');
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();});
