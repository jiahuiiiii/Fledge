const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
let browser;
(async () => {
  browser = await chromium.launch({ headless: true, ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}) });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors=[], external=[], mutations=[];
  page.on('pageerror', e => errors.push(e.message));
  page.on('request', r => { if(!r.url().startsWith(process.env.THESIS_TEST_URL)) external.push(r.url()); if(r.method()==='POST') mutations.push(r.url()); });
  // UI toggle responses are mocked; actual endpoint/scheduler isolation is tested
  // separately in test_filing_watch.py. Never opt this browser into real HTTP.
  let enabled=false, configured=true;
  await page.route('**/api/v1/workspace*', async route => {
    const response=await route.fetch(), body=await response.json();
    body.result.sec_status.configured=configured;
    body.result.filing_watch.enabled=enabled;
    body.result.filing_watch.next_check_at=enabled ? new Date(Date.now()+86400000).toISOString() : null;
    await route.fulfill({response,json:body});
  });
  await page.route('**/api/v1/companies/*/filing-watch', async route => {
    enabled=route.request().postDataJSON().enabled;
    await route.fulfill({json:{result:{enabled}}});
  });
  await page.goto(process.env.THESIS_TEST_URL);
  await page.locator('.watch-item').filter({hasText:'MSFT'}).click();
  await page.getByRole('tab',{name:'Fundamentals',exact:true}).click();
  const panel=page.getByRole('region',{name:'Daily filing checks',exact:true});
  await panel.getByRole('button',{name:'Start daily filing checks',exact:true}).waitFor();
  assert.match(await panel.innerText(),/Daily checks are off/);
  assert.match(await panel.getByRole('status').innerText(),/Check failed/);
  assert.match(await panel.innerText(),/No AI credits are used/);
  await panel.locator('summary').click();
  await panel.locator('article').first().waitFor();
  assert.equal(await panel.locator('article').count(),20);
  await panel.getByRole('button',{name:'Older filing checks',exact:true}).click();
  await page.waitForFunction(() => document.querySelectorAll('.filing-watch article').length===22);
  assert.match(await panel.locator('article a').first().getAttribute('href'),/sec.gov\/Archives/);
  assert.equal(mutations.length,0,'Reading journal must never POST');
  await panel.getByRole('button',{name:'Start daily filing checks',exact:true}).click();
  await panel.getByRole('button',{name:'Stop daily filing checks',exact:true}).waitFor();
  assert.match(await panel.innerText(),/Daily checks on/);
  await panel.getByRole('button',{name:'Stop daily filing checks',exact:true}).click();
  await panel.getByRole('button',{name:'Start daily filing checks',exact:true}).waitFor();
  assert.equal(mutations.length,2); assert.ok(mutations.every(s=>s.endsWith('/filing-watch')));
  for(const width of [1440,390,320]) {
    await page.setViewportSize({width,height:960});
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth<=innerWidth),`Filing monitor overflow ${width}`);
  }
  await page.setViewportSize({width:390,height:960});
  await page.screenshot({path:'/private/tmp/thesis-filing-watch-390.png',fullPage:true});
  configured=false;
  await page.reload(); await page.getByRole('tab',{name:'Fundamentals',exact:true}).click();
  assert.equal(await panel.getByRole('button',{name:'Start daily filing checks',exact:true}).isDisabled(),true);
  assert.deepEqual(errors,[]); assert.deepEqual(external,[]);
  console.log('Filing monitor browser passed: off/default, visible failure, 22-record history, exact source link, mocked enable/stop, missing identity, 320/390/1440 layouts, no source/AI calls.');
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();});
