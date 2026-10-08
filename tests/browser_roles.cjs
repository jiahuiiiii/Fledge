const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
let browser,page;
(async()=>{
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
 page=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
 const errors=[],external=[],paid=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',r=>{const u=new URL(r.request().url());if(!['127.0.0.1','localhost'].includes(u.hostname)){external.push(u.href);return r.abort();}if(/\/(generate|event-review|evidence-review|brief|sentiment|check)$/.test(u.pathname)&&r.request().method()==='POST')paid.push(u.href);return r.continue();});
 const base=process.env.THESIS_TEST_URL;
 await page.goto(base);
 await page.getByRole('button',{name:'Save my reasoning',exact:true}).click();
 const modal=page.getByRole('dialog');
 await modal.getByLabel('My reasoning',{exact:true}).fill('Fictional demonstration: I want to review slowing growth. This is my own risk threshold.');
 await modal.getByRole('button',{name:'Add condition',exact:true}).click();
 await modal.getByLabel('Percent',{exact:true}).fill('15');
 await modal.getByLabel('Condition',{exact:true}).selectOption('<=');
 await modal.getByRole('checkbox').check();
 await modal.getByLabel('Purpose of condition 1',{exact:true}).selectOption('risk');
 assert.equal(await modal.getByRole('checkbox').isChecked(),false);
 assert.equal(await modal.getByLabel('Percent',{exact:true}).inputValue(),'15');
 assert.equal(await modal.getByLabel('Condition',{exact:true}).inputValue(),'<=');
 for(const width of [320,390,1440]) {
  await page.setViewportSize({width,height:1000});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow at ${width}`);
  await modal.getByLabel("Purpose of condition 1",{exact:true}).scrollIntoViewIfNeeded();
  await page.screenshot({path:`/private/tmp/thesis-numerical-roles-editor-${width}.png`,fullPage:true});
 }
 await modal.getByRole('checkbox').check();
 await modal.getByRole('button',{name:'Approve monitoring',exact:true}).click();
 await modal.waitFor({state:'hidden'});
 await page.locator('.idea-panel').getByText('Risk threshold not reached',{exact:false}).first().waitFor();
 const getState=async()=> (await(await page.request.get(base+'/api/v1/workspace')).json()).result;
 const original=await getState();assert.equal(original.versions[0].conditions[0].role,'risk');
 for(const expected_stage of [0,1])assert.equal((await page.request.post(base+'/api/v1/demo/advance',{headers:{'X-Thesis-Request':'local-ui'},data:{expected_stage}})).status(),200);
 await page.locator('.idea-panel .condition-values b').getByText('12%',{exact:true}).waitFor({timeout:35000});
 await page.getByRole('button',{name:'Updates',exact:true}).click();
 const change=page.locator('.change-summary').filter({hasText:'Risk threshold reached'});
 await change.first().waitFor();await change.first().click();
 await page.locator('.history-page').getByText('Risk threshold reached',{exact:false}).first().waitFor();
 const download=page.waitForEvent('download');
 await page.locator('.history-page').getByRole('button',{name:/Download/}).click();
 const file=await download;const content=await fs.readFile(await file.path(),'utf8');
 assert.match(content,/Risk threshold reached/);assert.match(content,/Risk to watch/);assert.match(content,/12.00%/);
 for(const width of [320,390,1440]) {
  await page.setViewportSize({width,height:1000});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`history overflow at ${width}`);
  await page.screenshot({path:`/private/tmp/thesis-numerical-roles-history-${width}.png`,fullPage:true});
 }
 await page.getByLabel('Record',{exact:true}).selectOption(original.versions[0].evaluations[0].id);
 await page.locator('.history-page').getByText('Risk threshold not reached',{exact:false}).first().waitFor();
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.deepEqual(paid,[]);
 console.log('Numerical-role browser passed: explicit purpose; approval reset without changing threshold/operator; saved risk; 18→12 crossing in Updates; exact history and export; 320/390/1440 layouts; no provider calls.');
})().catch(async e=>{console.error(e);if(page)console.error((await page.locator('body').innerText()).slice(-8000));process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();});
