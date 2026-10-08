const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[],external=[],writes=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',r=>{const u=new URL(r.request().url());if(!['localhost','127.0.0.1'].includes(u.hostname)){external.push(u.href);return r.abort();}if(r.request().method()!=='GET'){writes.push({path:u.pathname,body:r.request().postDataJSON()});if(!u.pathname.endsWith('/event-review')&&!u.pathname.endsWith('/idea'))return r.abort();}return r.continue();});
  // Only availability is mocked; real API calls below must reuse seeded responses.
  await page.route('**/api/v1/model-status',async r=>{const response=await r.fetch();const json=await response.json();json.result.comparison_enabled=true;await r.fulfill({response,json});});
  const iid='c767e09f-35ea-5eaf-a626-ff5d3aa4709b',url=process.env.THESIS_TEST_URL;
  await page.goto(url+'/?company='+iid+'&view=idea');
  const main=page.getByRole('main'),panel=main.getByRole('region',{name:'Event conditions',exact:true});
  await panel.getByText(/Window 2 of 3/).waitFor();assert.match(await panel.innerText(),/Evidence does not establish this event/);
  const state=async()=> (await(await page.request.get(url+'/api/v1/workspace?instrument_id='+iid)).json()).result;
  const initial=await state(),version=initial.versions[0],eid=version.evaluations[0].id,cid=version.events[0].condition_id;
  const beforeBudget=(await(await page.request.get(url+'/api/v1/model-status')).json()).result.budget;
  await panel.getByRole('combobox',{name:/Window to check for/}).selectOption('1');
  await panel.getByRole('button',{name:'Check event evidence',exact:true}).click();
  await page.getByText(/Event evidence check saved\. Current monitoring uses only/).waitFor();
  assert.equal((await state()).versions[0].evaluations[0].id,eid);
  assert.equal(writes.at(-1).body.event_periods[cid],1);
  assert.deepEqual((await(await page.request.get(url+'/api/v1/model-status')).json()).result.budget,beforeBudget);
  await panel.getByRole('combobox',{name:/Window to check for/}).selectOption('3');
  await panel.getByRole('button',{name:'Check event evidence',exact:true}).click();
  await page.getByText('That recurring window has not started. No AI call was made.',{exact:true}).waitFor();
  assert.deepEqual((await(await page.request.get(url+'/api/v1/model-status')).json()).result.budget,beforeBudget);
  await panel.locator('.event-schedule summary').click();
  for(const width of [320,390,1440]){await page.setViewportSize({width,height:1100});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await panel.screenshot({path:`/private/tmp/thesis-recurring-current-${width}.png`});}
  await page.getByRole('button',{name:'History',exact:true}).click();
  const historical=version.event_reviews.find(r=>r.historical_window_check);assert.ok(historical);
  await page.getByLabel('Record',{exact:true}).selectOption('event:'+historical.id);
  const history=main.getByRole('region',{name:'Event conditions',exact:true});
  assert.match(await history.innerText(),/Window 1 of 3/);assert.match(await history.innerText(),/does not replace the current window/);
  await history.getByRole('button',{name:'Inspect event source 1 ↗',exact:true}).click();assert.match(await page.getByRole('dialog').innerText(),/Authored fixture/);await page.keyboard.press('Escape');
  const download=page.waitForEvent('download');await main.getByRole('button',{name:'Download research record',exact:true}).click();await(await download).saveAs('/private/tmp/thesis-recurring-history.html');
  const html=require('node:fs').readFileSync('/private/tmp/thesis-recurring-history.html','utf8');assert.match(html,/Checked window 1 of 3/);assert.match(html,/earlier-window check/);
  await page.goto(url+'/?company='+iid+'&view=idea');await main.getByRole('button',{name:'Edit my idea',exact:true}).click();
  const modal=page.getByRole('dialog');assert.equal(await modal.getByLabel('Event repeat interval 1',{exact:true}).inputValue(),'3');assert.equal(await modal.getByLabel('Event window count 1',{exact:true}).inputValue(),'3');
  await modal.getByRole('checkbox').check();await modal.getByLabel('Event window count 1',{exact:true}).fill('4');assert.equal(await modal.getByRole('checkbox').isChecked(),false);
  await modal.locator('.event-schedule summary').click();await modal.screenshot({path:'/private/tmp/thesis-recurring-editor-1440.png'});
  await modal.getByRole('checkbox').check();await modal.getByRole('button',{name:/Approve.*monitor/i}).click();await modal.waitFor({state:'hidden'});
  assert.equal((await state()).versions[0].events[0].repeat_count,4);assert.equal((await state()).versions[1].events[0].repeat_count,3);
  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
  assert.ok(writes.every(x=>x.path.endsWith('/event-review')||x.path.endsWith('/idea')));
  console.log('Recurring browser passed: current/prior windows, cached earlier check through actual API, no-charge future rejection, source/history/export, explicit revision approval and 320/390/1440 layouts.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
