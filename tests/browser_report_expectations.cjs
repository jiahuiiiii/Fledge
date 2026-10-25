const {chromium}=require(process.env.PLAYWRIGHT_MODULE);
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[],external=[],writes=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',r=>{const u=new URL(r.request().url());if(!['localhost','127.0.0.1'].includes(u.hostname)){external.push(u.href);return r.abort();}if(r.request().method()!=='GET'){writes.push(u.pathname);if(!['/api/v1/idea','/api/v1/demo/advance'].includes(u.pathname))return r.abort();}return r.continue();});
  const url=process.env.THESIS_TEST_URL;await page.goto(url+'/?company=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa&view=workspace');
  await page.getByRole('button',{name:'Research questions',exact:true}).click();
  await page.getByRole('dialog',{name:'Your research',exact:true}).getByRole('button',{name:'Save my reasoning',exact:true}).click();
  const modal=page.getByRole('dialog',{name:'Save your reasoning',exact:true});await page.getByLabel('My reasoning',{exact:true}).fill('Authored test: growth needs newer reporting evidence by my chosen date.');
  await modal.getByText('Add monitoring rules',{exact:true}).click();
  await modal.getByRole('button',{name:'Add condition',exact:true}).click();await page.getByLabel('Percent',{exact:true}).fill('15');
  await modal.getByText('When you expect the next figures',{exact:true}).click();
  await modal.getByLabel('Expected period end 1',{exact:true}).fill('2025-07-01');
  await modal.getByRole('checkbox').check();await modal.getByLabel('Expected figures by 1',{exact:true}).fill('2025-08-30');assert.equal(await modal.getByRole('checkbox').isChecked(),false);
  for(const width of [320,390,1440]){await page.setViewportSize({width,height:1100});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await modal.locator('.reporting-age-editor').first().screenshot({path:`/private/tmp/thesis-report-editor-${width}.png`});}
  await modal.getByRole('checkbox').check();await modal.getByRole('button',{name:'Approve monitoring',exact:true}).click();
  const iid='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
  const workspace=async()=>(await(await page.request.get(url+`/api/v1/workspace?instrument_id=${iid}`)).json()).result;
  async function waitState(expected) {
    for(let n=0;n<150;n++) {
      const data=await workspace();
      if(data.versions[0]?.evaluations[0]?.manifest.report_expectations?.[0]?.state===expected) return data;
      await page.waitForTimeout(200);
    }
    assert.fail(`No completed reporting assessment reached ${expected}`);
  }
  await waitState('waiting');
  const budget=async()=>(await(await page.request.get(url+'/api/v1/model-status')).json()).result.budget;
  const before=await budget();
  const advance=async(stage)=>{const response=await page.request.post(url+'/api/v1/demo/advance',{headers:{'x-thesis-request':'local-ui'},data:{expected_stage:stage}});assert.equal(response.status(),200);};
  await advance(0);await waitState('overdue');
  await page.getByRole('button',{name:'Updates',exact:true}).click();
  const update=page.locator('.change-summary').filter({hasText:'Expected reporting evidence changed'});await update.waitFor();assert.match(await update.innerText(),/does not prove a late company filing/);
  await update.click();const history=page.locator('.history-page');await history.getByText('Expected figures missing',{exact:true}).waitFor();
  assert.match(await history.innerText(),/2025-08-30/);
  for(const width of [320,390,1440]){await page.setViewportSize({width,height:1100});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await history.locator('.report-expectation').screenshot({path:`/private/tmp/thesis-report-overdue-${width}.png`});}
  const download=page.waitForEvent('download');await history.getByRole('button',{name:'Download research record',exact:true}).click();await(await download).saveAs('/private/tmp/thesis-report-overdue.html');
  const html=require('node:fs').readFileSync('/private/tmp/thesis-report-overdue.html','utf8');assert.match(html,/Expected figures are missing/);assert.match(html,/2025-08-30/);
  const dataCompany=iid;
  await advance(1);await waitState('available');await page.goto(url+'/?company='+dataCompany+'&view=idea');
  const data=await workspace();
  assert.equal(data.versions[0].evaluations[0].manifest.report_expectations[0].state,'available');assert.equal(data.versions[0].evaluations[0].outcome,'not_met');
  await page.getByRole('main').getByRole('button',{name:'Edit my idea',exact:true}).click();
  assert.equal(await modal.getByLabel('Expected period end 1',{exact:true}).inputValue(),'2025-07-01');await modal.getByRole('checkbox').check();await modal.getByRole('button',{name:'Clear reporting expectation',exact:true}).click();assert.equal(await modal.getByRole('checkbox').isChecked(),false);await page.keyboard.press('Escape');
  assert.deepEqual(await budget(),before);assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.ok(writes.every(v=>v==='/api/v1/idea'));
  console.log('Reporting-expectation browser passed: explicit approval/reset, waiting → missing → available period, actual local Updates/history/export, threshold outcome retained, 320/390/1440 layouts and zero API credits.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
