const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
let browser;
(async()=>{
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
 const page=await browser.newPage({viewport:{width:1440,height:1050},reducedMotion:'reduce'});
 const errors=[],writes=[],external=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',r=>{const u=new URL(r.request().url());if(!['127.0.0.1','localhost'].includes(u.hostname)){external.push(u.href);return r.abort();}if(r.request().method()!=='GET')writes.push(u.pathname);return r.continue();});
 const base=process.env.THESIS_TEST_URL,iid='c767e09f-35ea-5eaf-a626-ff5d3aa4709b';
 await page.goto(base+'/?company='+iid+'&view=workspace');
 const panel=page.getByRole('region',{name:'Current sentiment inputs',exact:true});
 await panel.getByText('The inputs selected now differ from the saved sentiment reading.',{exact:true}).waitFor();
 await panel.getByText(/^Read current sources ·/).click();
 const saved=(await(await page.request.get(base+'/api/v1/workspace?instrument_id='+iid)).json()).result;
 for(const scope of ['news','reddit','hackernews']){
  await panel.getByRole('combobox',{name:'Current source type',exact:true}).selectOption(scope);
  const expected=saved.sentiment_inputs.sources.filter(s=>(s.kind==='news'?'news':s.platform||'reddit')===scope);
  assert.deepEqual(await panel.locator('article h3').allTextContents(),expected.map(s=>s.title));
  assert.deepEqual(await panel.locator('.original-source-text').allTextContents(),expected.map(s=>s.body));
  assert.equal(await panel.locator('.sentiment-tag,.sentiment-counts').count(),0);
 }
 await panel.getByRole('button',{name:'Inspect current source ↗',exact:true}).click();
 const dialog=page.getByRole('dialog');await dialog.waitFor();
 assert.match(await dialog.innerText(),/authored new reply/);
 await dialog.getByRole('heading',{name:'What is this replying to?',exact:true}).waitFor();
 await page.keyboard.press('Escape');
 await panel.getByRole('combobox',{name:'Current source type',exact:true}).selectOption('news');
 for(const width of [320,390,1440]){
  await page.setViewportSize({width,height:1050});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);
  await panel.screenshot({path:`/private/tmp/thesis-current-inputs-${width}.png`});
 }
 const unchanged=(await(await page.request.get(base+'/api/v1/workspace?instrument_id='+iid)).json()).result.sentiment;
 assert.deepEqual(unchanged,saved.sentiment);
 await page.setViewportSize({width:390,height:1050});
 await page.getByRole('combobox',{name:'Company',exact:true}).selectOption('4780d271-7c4a-5c18-80f8-74e164c21675');
 await panel.getByText('Sources are available to read before your first sentiment analysis.',{exact:true}).waitFor();
 await panel.getByText(/^Read current sources ·/).click();
 await panel.getByRole('combobox',{name:'Current source type',exact:true}).selectOption('news');
 await panel.getByText('No selected texts for this source type. Missing coverage is not neutral sentiment.',{exact:true}).waitFor();
 await panel.getByRole('combobox',{name:'Current source type',exact:true}).selectOption('hackernews');
 assert.match(await panel.innerText(),/I use Apple products/);
 await page.reload();await panel.getByText('Sources are available to read before your first sentiment analysis.',{exact:true}).waitFor();
 assert.deepEqual(errors,[]);assert.deepEqual(writes,[]);assert.deepEqual(external,[]);
 console.log('Current-source browser passed: exact news/Reddit/HN texts, new versus saved selection, no borrowed labels, original-source dialog, first-reading/empty-platform states, reload, 320/390/1440, no source/model request.');
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();});
