const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[],external=[],writes=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',r=>{const u=new URL(r.request().url());if(!['localhost','127.0.0.1'].includes(u.hostname)){external.push(u.href);return r.abort();}if(r.request().method()!=='GET'){writes.push(u.pathname);return r.abort();}return r.continue();});
  await page.goto(process.env.THESIS_TEST_URL+'/?company=c767e09f-35ea-5eaf-a626-ff5d3aa4709b&view=idea');
  const panel=page.getByRole('main').getByRole('region',{name:'Event conditions',exact:true});
  await panel.getByText('Report matches your required event',{exact:true}).waitFor();
  assert.match(await panel.innerText(),/Event occurrence window 2026-09-01 through 2026-09-30/);
  assert.match(await panel.innerText(),/Selected event date:.*September 3, 2026.*2026-09-03/);
  await panel.getByRole('button',{name:'Inspect event source 1 ↗',exact:true}).click();
  assert.match(await page.getByRole('dialog').innerText(),/Authored fixture.*September 3, 2026/);await page.keyboard.press('Escape');
  for(const width of [320,390,1440]){await page.setViewportSize({width,height:1100});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await panel.screenshot({path:`/private/tmp/thesis-event-occurrence-${width}.png`});}
  const download=page.waitForEvent('download');await page.getByRole('button',{name:'Download research record',exact:true}).click();await(await download).saveAs('/private/tmp/thesis-event-occurrence-result.html');
  const html=require('node:fs').readFileSync('/private/tmp/thesis-event-occurrence-result.html','utf8');assert.match(html,/Selected event date: September 3, 2026/);assert.match(html,/Event happened 2026-09-01/);
  await page.getByRole('button',{name:'History',exact:true}).click();const state=(await(await page.request.get(process.env.THESIS_TEST_URL+'/api/v1/workspace?instrument_id=c767e09f-35ea-5eaf-a626-ff5d3aa4709b')).json()).result;
  await page.getByLabel('Record',{exact:true}).selectOption('event:'+state.versions[0].event_reviews[0].id);
  assert.match(await page.getByRole('main').innerText(),/Selected event date:.*September 3, 2026/);
  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.deepEqual(writes,[]);
  console.log('Occurrence browser passed: dated assessment, exact original source, saved check/history/export and 320/390/1440 layouts; no writes or external calls.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
