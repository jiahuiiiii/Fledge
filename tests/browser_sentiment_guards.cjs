// Authored UI fixtures. No owner reading is changed and no model is dispatched.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
let browser;
(async()=>{
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
 const page=await browser.newPage({viewport:{width:1440,height:1100},reducedMotion:'reduce'});
 const errors=[],writes=[],external=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',r=>{
  const u=new URL(r.request().url());
  if(!['127.0.0.1','localhost'].includes(u.hostname)){
   if(r.request().resourceType()!=='image')external.push(u.href);
   return r.abort();
  }
  if(r.request().method()!=='GET'){writes.push(u.pathname);return r.fulfill({json:{result:{active:false,steps:[]}}});}
  return r.continue();
 });
 const base=process.env.THESIS_TEST_URL,iid='c767e09f-35ea-5eaf-a626-ff5d3aa4709b';
 await page.goto(base+'/?company='+iid+'&view=workspace');
 await page.getByRole('tab',{name:'News & discussion',exact:true}).waitFor();
 const saved=(await(await page.request.get(base+'/api/v1/workspace?instrument_id='+iid)).json()).result;
 let state=JSON.parse(JSON.stringify(saved));
 const ref={status:'available',close:'360.14',date:'2026-10-08',currency:'USD',retrieved_at:'2026-10-08T20:10:00+00:00',basis:'Authored USD OHLC fixture.'};
 const source={id:'price-guard-fixture',title:'Reddit comment',body:'MSFT to $340',source:'Reddit · r/stocks',kind:'social',platform:'reddit',published_at:'2026-10-08T21:00:00+00:00',available_at:'2026-10-08T21:05:00+00:00',url:'https://www.reddit.com/r/stocks/comments/fixture/'};
 const item={id:'item_price',source_id:source.id,channel:'social',relevance:'relevant',sentiment:'unclear',statement:'opinion',topic:'valuation',basis:'unclear',evidence_policy:'sentiment-source-extracts-1',explanation:'A price target alone does not state whether the author expects a rise or a fall.',citations:[{source_id:source.id,passage_id:'p1',quote:source.body}],previous_citations:[],guard:{policy:'sentiment-evidence-guards-1',applied:true,rule:'bare_price_target',model_sentiment:'positive',model_basis:'expressed_evaluation'},price_comparisons:[{status:'compared',amount:'340',kind:'price_target',quote:source.body,author_direction:'not_stated',difference_percent:'-5.592269673460321',relation:'below',reference:ref}]};
 const counts={positive:0,negative:0,mixed:0,neutral:0,unclear:1};
 const sample={counts,selected:1,relevant:1,counted_groups:1,tone:'thin sample',interpretable_groups:0,minimum_directional_groups:5};
 state.sentiment={...state.sentiment,items:[item],sources:[source],earlier_method:false,prompt_version:'thesis-source-sentiment-23',summary_policy:'sentiment-coverage-9',summary:{news:{...sample,selected:0,relevant:0,counted_groups:0,counts:{...counts,unclear:0}},social:sample,social_platforms:{reddit:sample}},coverage:{...state.sentiment.coverage,available_news:0,available_social:1,social_platforms:{reddit:1,hackernews:0,x:0}}};
 await page.route('**/api/v1/workspace?*',r=>r.fulfill({json:{result:state}}));
 await page.route('**/api/v1/companies/'+iid+'/loading',r=>r.fulfill({json:{result:{active:false,steps:[],lookback_days:7}}}));
 const panel=page.getByRole('region',{name:'News and social sentiment',exact:true});
 const open=async()=>{
  await page.reload();await page.getByRole('tab',{name:'News & discussion',exact:true}).click();
  await panel.getByRole('group',{name:'Sentiment source type',exact:true}).getByRole('button',{name:'Reddit discussion',exact:true}).click();
 };
 await open();
 const row=panel.locator('article[data-source-id="price-guard-fixture"]');
 await row.getByText('Checked label',{exact:true}).waitFor();
 assert.equal(await row.locator('.sentiment-tag').innerText(),'Unclear');
 assert.match(await row.innerText(),/5.6% below the \$360.14 saved close \(2026-10-08\)/);
 assert.match(await panel.locator('.sentiment-summary').innerText(),/0 interpretable groups · 1 unclear/i);
 const evidence=page.getByRole('dialog',{name:'Story evidence',exact:true});
 for(const width of [1440,390,320]){
  await page.setViewportSize({width,height:1100});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await row.getByRole('button',{name:'Inspect evidence',exact:true}).click();
  await evidence.waitFor();
  assert.match(await evidence.innerText(),/AI's positive label to unclear/);
  assert.match(await evidence.innerText(),/\(\$340 − \$360.14\) ÷ \$360.14 × 100 = -5.59%/);
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await evidence.screenshot({path:path.join(process.env.THESIS_SCREENSHOT_DIR||'/private/tmp','sentiment-price-guard-'+width+'.png')});
  await page.keyboard.press('Escape');
  assert.ok(await row.getByRole('button',{name:'Inspect evidence',exact:true}).evaluate(e=>e===document.activeElement));
 }
 item.price_comparisons[0]={...item.price_comparisons[0],status:'unverified_post_time',reference:{status:'unverified_post_time'}};
 await open();assert.equal(await row.locator('.sentiment-price-context').count(),0);
 await row.getByRole('button',{name:'Inspect evidence',exact:true}).click();
 assert.match(await evidence.innerText(),/original post time is unverified/);
 assert.doesNotMatch(await evidence.innerText(),/Calculation:/);
 await page.keyboard.press('Escape');
 // Historical labels remain the saved labels under an earlier-method notice.
 state.sentiment.earlier_method=true;item.sentiment='positive';delete item.guard;delete item.price_comparisons;
 await open();assert.equal(await row.locator('.sentiment-tag').innerText(),'Positive');
 assert.match(await panel.innerText(),/earlier analysis method/i);
 const automaticLoading=writes.filter(url=>url.endsWith('/loading'));
 assert.deepEqual(writes.filter(url=>!url.endsWith('/loading')),[]);
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
 console.log('Price guard browser passed: code arithmetic, checked labels, unknown post time, counts, legacy reading, 320/390/1440px, keyboard; automatic loading blocked:',automaticLoading.length);
 await browser.close();
})().catch(async e=>{console.error(e);const page=browser?.contexts()[0]?.pages()[0];if(page){console.error(await page.locator('body').innerText());await page.screenshot({path:'/private/tmp/sentiment-price-guard-failure.png'});}if(browser)await browser.close();process.exit(1);});
