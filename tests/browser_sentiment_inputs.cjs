// Isolated authored data: reading/evidence/settings must never write or generate.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
let browser;
(async()=>{
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
 const page=await browser.newPage({viewport:{width:1440,height:1050},reducedMotion:'reduce'});
 const errors=[],writes=[],external=[];
 const evidence=process.env.THESIS_DESIGN_EVIDENCE||'/private/tmp/thesis-reading-journey';fs.mkdirSync(evidence,{recursive:true});
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',r=>{const u=new URL(r.request().url());if(u.hostname==='financialmodelingprep.com'&&r.request().resourceType()==='image')return r.fulfill({status:404,body:''});if(!['127.0.0.1','localhost'].includes(u.hostname)){external.push(u.href);return r.abort();}if(/\/companies\/[^/]+\/loading$/.test(u.pathname))return r.fulfill({json:{result:{active:false,steps:[]}}});if(r.request().method()!=='GET'){writes.push(u.pathname);return r.abort();}return r.continue();});
 const base=process.env.THESIS_TEST_URL,iid='c767e09f-35ea-5eaf-a626-ff5d3aa4709b';
 await page.goto(base+'/?company='+iid+'&view=workspace');
 await page.getByRole('tab',{name:'News & discussion',exact:true}).click();
 const sentiment=page.getByRole('region',{name:'News and social sentiment',exact:true});
 assert.equal(await sentiment.getByRole('button',{name:'Company news',exact:true}).getAttribute('aria-pressed'),'true');
 assert.equal(await sentiment.locator('.social-source-summary,.provider-list,.social-coverage').count(),0);
 const news=page.getByRole('region',{name:'Company news and briefing',exact:true});
 await news.getByRole('heading',{name:'Recent company news',exact:true}).waitFor();
 assert.equal(await news.evaluate(el=>Boolean(el.compareDocumentPosition(document.querySelector('.sentiment-panel')) & Node.DOCUMENT_POSITION_FOLLOWING)),true);
 assert.equal(await news.locator('.news-brief-details').getAttribute('open'),null);
 for(const width of [1440,390,320]){
   await page.setViewportSize({width,height:1050});
   await news.getByRole('heading',{name:'Recent company news',exact:true}).evaluate(el=>el.scrollIntoView({block:'center'}));
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await page.screenshot({path:`${evidence}/headlines-${width}.png`});
 }
 await page.setViewportSize({width:1440,height:1050});
 const saved=(await(await page.request.get(base+'/api/v1/workspace?instrument_id='+iid)).json()).result;
 const trigger=sentiment.getByRole('button',{name:'Evidence',exact:true});
 await trigger.click();
 const evidenceDialog=page.getByRole('dialog',{name:'News & discussion · evidence',exact:true});
 const original=evidenceDialog.getByRole('region',{name:'Original selected sources',exact:true});
 const savedNews=saved.sentiment.sources.filter(s=>s.kind==='news');
 assert.ok(savedNews.length>0);
 for(const source of savedNews) assert.ok((await original.locator('.original-source-text').allTextContents()).includes(source.body));
 assert.equal(await original.locator('.sentiment-tag,.sentiment-counts').count(),0);
 await evidenceDialog.getByRole('button',{name:'Current sources',exact:true}).click();
 const panel=evidenceDialog.getByRole('region',{name:'Current sentiment inputs',exact:true});
 await panel.getByText('The inputs selected now differ from the saved sentiment reading.',{exact:true}).waitFor();
 for(const scope of ['news','reddit','hackernews']){
  await panel.getByRole('group',{name:'Current source type',exact:true}).getByRole('button',{name:({news:'Company news',reddit:'Reddit discussion',hackernews:'Hacker News'})[scope],exact:true}).click();
  const expected=saved.sentiment_inputs.sources.filter(s=>(s.kind==='news'?'news':s.platform||'reddit')===scope);
  assert.deepEqual(await panel.locator('article h3').allTextContents(),expected.map(s=>s.title));
  assert.deepEqual(await panel.locator('.original-source-text').allTextContents(),expected.map(s=>s.body));
  assert.equal(await panel.locator('.sentiment-tag,.sentiment-counts').count(),0);
 }
 await panel.getByRole('button',{name:'Inspect current source ↗',exact:true}).click();
 const sourceDialog=page.getByRole('dialog',{name:'Source evidence',exact:true});await sourceDialog.waitFor();
 assert.match(await sourceDialog.innerText(),/authored new reply/);
 await sourceDialog.getByRole('heading',{name:'What is this replying to?',exact:true}).waitFor();
 await page.keyboard.press('Escape');
 assert.equal(await evidenceDialog.isVisible(),true);
 assert.equal(await panel.getByRole('button',{name:'Inspect current source ↗',exact:true}).evaluate(el=>document.activeElement===el),true);
 await panel.getByRole('group',{name:'Current source type',exact:true}).getByRole('button',{name:'Company news',exact:true}).click();
 for(const width of [320,390,1440]){
  await page.setViewportSize({width,height:1050});
  assert.ok(await evidenceDialog.evaluate(el=>el.scrollWidth<=el.clientWidth+1),`dialog overflow ${width}`);
  const box=await evidenceDialog.boundingBox();assert.ok(box.x>=0&&box.x+box.width<=width+1);
  await page.screenshot({path:`${evidence}/evidence-${width}.png`});
 }
 await evidenceDialog.getByRole('button',{name:'History',exact:true}).click();
 await evidenceDialog.getByText('Watch check history',{exact:true}).click();
 await evidenceDialog.getByText('Compare sentiment samples',{exact:true}).waitFor();
 await page.keyboard.press('Escape');
 assert.equal(await trigger.evaluate(el=>document.activeElement===el),true);
 await page.locator('.company-header').getByRole('button',{name:'Data & sources',exact:true}).click();
 const coverage=page.getByRole('dialog',{name:'Data & sources',exact:true});
 await coverage.getByText('Publisher feeds & source connections',{exact:true}).click();
 await coverage.getByText('Social source coverage',{exact:true}).click();
 await coverage.getByRole('heading',{name:'Source library',exact:true}).waitFor();
 for(const width of [1440,390,320]){
  await page.setViewportSize({width,height:1050});
  assert.ok(await coverage.evaluate(el=>el.scrollWidth<=el.clientWidth+1));
  await page.screenshot({path:`${evidence}/connections-${width}.png`});
 }
 await page.keyboard.press('Escape');
 await sentiment.getByRole('button',{name:/^Watch ·/}).click();
 const watch=page.getByRole('dialog',{name:'News & discussion · watch',exact:true});
 const beforeWatch=await watch.getByRole('checkbox',{name:'Watch news + social changes',exact:true}).isChecked();
 for(let i=0;i<12;i++) { await page.keyboard.press('Tab');assert.equal(await watch.evaluate(el=>el.contains(document.activeElement)),true); }
 await page.keyboard.press('Escape');
 await sentiment.getByRole('button',{name:/^Watch ·/}).click();
 assert.equal(await watch.getByRole('checkbox',{name:'Watch news + social changes',exact:true}).isChecked(),beforeWatch);
 await page.keyboard.press('Escape');
 for(const width of [1440,390,320]){
  await page.setViewportSize({width,height:1050});
  await sentiment.getByRole('heading',{name:'What’s the tone?',exact:true}).evaluate(el=>el.scrollIntoView({block:'start'}));
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`page overflow ${width}`);
  await page.screenshot({path:`${evidence}/news-${width}.png`});
 }
 const unchanged=(await(await page.request.get(base+'/api/v1/workspace?instrument_id='+iid)).json()).result;
 assert.deepEqual(unchanged.sentiment,saved.sentiment);assert.deepEqual(unchanged.news_watch,saved.news_watch);
 await page.setViewportSize({width:390,height:1050});
 await page.getByRole('combobox',{name:'Company',exact:true}).selectOption('4780d271-7c4a-5c18-80f8-74e164c21675');
 await page.locator('.main-workspace[aria-busy="false"]').waitFor();
 await sentiment.getByRole('button',{name:'Evidence',exact:true}).click();
 await panel.getByText('Sources are available to read before your first sentiment analysis.',{exact:true}).waitFor();
 await panel.getByRole('group',{name:'Current source type',exact:true}).getByRole('button',{name:'Company news',exact:true}).click();
 await panel.getByText('No selected texts for this source type. Missing coverage is not neutral sentiment.',{exact:true}).waitFor();
 await panel.getByRole('group',{name:'Current source type',exact:true}).getByRole('button',{name:'Hacker News',exact:true}).click();
 assert.match(await panel.innerText(),/I use Apple products/);
 await page.reload();await page.getByRole('tab',{name:'News & discussion',exact:true}).click();
 await sentiment.getByRole('button',{name:'Evidence',exact:true}).click();
 await panel.getByText('Sources are available to read before your first sentiment analysis.',{exact:true}).waitFor();
 assert.deepEqual(errors,[]);assert.deepEqual(writes,[]);assert.deepEqual(external,[]);
 fs.writeFileSync(`${evidence}/verification.json`,JSON.stringify({errors,writes,external,viewports:[320,390,1440]},null,2));
 console.log('Reading/evidence browser passed: news default; exact saved/current texts; nested original-source dialog and focus return; coverage/history on demand; watch focus containment and no writes; missing sources; scope/reload; 320/390/1440. No source/model request.');
})().catch(async e=>{console.error(e);const page=browser?.contexts()[0]?.pages()[0];if(page)await page.screenshot({path:'/private/tmp/thesis-reading-failure.png'});process.exitCode=1;}).finally(async()=>{await browser?.close();});
