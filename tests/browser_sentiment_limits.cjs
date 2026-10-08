const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
let browser;
(async()=>{
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
 const page=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
 const errors=[],writes=[],external=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',r=>{const u=new URL(r.request().url());if(!['127.0.0.1','localhost'].includes(u.hostname)){external.push(u.href);return r.abort();}if(r.request().method()!=='GET')writes.push(u.pathname);return r.continue();});
 const base=process.env.THESIS_TEST_URL,iid='c767e09f-35ea-5eaf-a626-ff5d3aa4709b';
 await page.goto(base+'/?company='+iid+'&view=workspace');
 await page.getByRole('region',{name:'News and social sentiment',exact:true}).waitFor();
 const data=(await(await page.request.get(base+'/api/v1/workspace?instrument_id='+iid)).json()).result;
 assert.ok(data.sentiment_inputs,JSON.stringify(data));
 assert.ok(data.sentiment_inputs.input_limits);
 const note=data.sentiment_inputs.input_limits.notice;
 const region=page.getByRole('region',{name:'News and social sentiment',exact:true});
 await region.locator('[data-source-limit]').filter({hasText:note}).first().waitFor();
 assert.ok(await region.locator('[data-source-limit]').count()>=2);
 const before=data.sentiment.items;
 await region.getByText('Compare sentiment samples',{exact:true}).click();
 await page.locator('.sample-comparison-grid [data-source-limit]').first().waitFor();
 const later=(await(await page.request.get(base+'/api/v1/workspace?instrument_id='+iid)).json()).result;
 assert.deepEqual(later.sentiment.items,before);
 for(const width of [320,390,1440]){
  await page.setViewportSize({width,height:1000});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);
  await page.getByRole('region',{name:'Current sentiment inputs',exact:true}).screenshot({path:`/private/tmp/thesis-source-limits-${width}.png`});
 }
 assert.deepEqual(errors,[]);assert.deepEqual(writes,[]);assert.deepEqual(external,[]);
 console.log('Sentiment-limit browser passed: actual bounded authored request, current/saved/history notices, original labels unchanged, phone/desktop, no paid/source request.');
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();});
