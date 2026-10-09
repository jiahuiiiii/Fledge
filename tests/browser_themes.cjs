const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs');let browser;
(async()=>{
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
 const shots=process.env.THESIS_SCREENSHOT_DIR||'/private/tmp';
 const page=await browser.newPage({viewport:{width:1440,height:1050},reducedMotion:'reduce'}),errors=[],external=[],paid=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>{if(r.method()==='POST'&&!r.url().endsWith('/loading'))paid.push(new URL(r.url()).pathname);});
 await page.route('**/*',r=>{const u=new URL(r.request().url());if(!['127.0.0.1','localhost'].includes(u.hostname)){external.push(u.href);return r.abort();}return r.continue();});
 await page.route('https://financialmodelingprep.com/image-stock/*',r=>r.fulfill({status:404,body:''}));
 let modelStatus={briefing_enabled:true,budget:{unresolved:0,running:0,needs_attention:0,remaining_usd:'10'}};
 await page.route('**/api/v1/model-status',r=>r.fulfill({json:{result:modelStatus}}));
 const base=process.env.THESIS_TEST_URL,iid='c767e09f-35ea-5eaf-a626-ff5d3aa4709b';
 await page.route('**/api/v1/companies/*/loading',r=>r.fulfill({json:{result:{active:false,steps:[],lookback_days:7}}}));
 await page.goto(base+'/?company='+iid+'&view=workspace');
 await page.getByRole('tab',{name:'News & discussion',exact:true}).click();
 const sentiment=page.getByRole('region',{name:'News and social sentiment',exact:true});
 await sentiment.getByRole('group',{name:'Sentiment source type',exact:true}).getByRole('button',{name:'Company news',exact:true}).click();
 await sentiment.getByText('What are people discussing?',{exact:true}).click();
 const panel=page.getByRole('region',{name:'Discussion themes',exact:true});
 await panel.getByLabel('Saved theme reading',{exact:true}).waitFor();
 assert.equal(await panel.locator('.theme-card').count(),1);
 const records=(await(await page.request.get(base+'/api/v1/companies/'+iid+'/discussion-themes')).json()).result;
 assert.equal(records.items.length,3);
 await sentiment.getByRole('button',{name:'Reddit discussion',exact:true}).click();
 assert.match(await panel.innerText(),/A differing view on this issue/);assert.match(await panel.innerText(),/same author/);
 await panel.getByText('Inspect supporting passages',{exact:true}).last().click();
 await panel.getByRole('button',{name:'Open theme source ↗',exact:true}).click();await page.getByRole('dialog').waitFor();assert.match(await page.getByRole('dialog').innerText(),/price too high/);await page.keyboard.press('Escape');
 await sentiment.getByRole('button',{name:'Hacker News',exact:true}).click();
 assert.match(await panel.innerText(),/No specific differing view identified/);assert.doesNotMatch(await panel.innerText(),/The same author also questions/);
 assert.match(await panel.innerText(),/1 saved parent message supplied as context/);
 await panel.getByText('Inspect supporting passages',{exact:true}).click();
 await panel.getByText('Parent context used for this finding',{exact:true}).click();
 assert.match(await panel.innerText(),/Microsoft software frustrates me because it crashes/);
 assert.match(await panel.innerText(),/I think Microsoft software is reliable/);
 assert.match(await panel.innerText(),/not another source or independent confirmation/);
 assert.equal(await panel.getByRole('link',{name:'Open cited parent discussion ↗',exact:true}).getAttribute('href'),'https://news.ycombinator.com/item?id=99');
 const dl=page.waitForEvent('download');await panel.getByRole('link',{name:'Download this theme reading',exact:true}).click();const html=fs.readFileSync(await(await dl).path(),'utf8');assert.match(html,/price too high/);assert.match(html,/hackernews/);assert.doesNotMatch(html,/<script/);
 assert.match(html,/Parent context used for this finding/);assert.match(html,/I think Microsoft software is reliable/);
 await panel.getByLabel('Saved theme reading',{exact:true}).selectOption(records.items[1].id);assert.match(await panel.innerText(),/Earlier source sample/);assert.match(await panel.innerText(),/earlier interpretation method/);assert.equal(await panel.locator('.theme-claim-source').count(),0);
 assert.equal(await panel.getByText('Parent context used for this finding',{exact:true}).count(),0);
 await panel.getByLabel('Saved theme reading',{exact:true}).selectOption(records.items[0].id);assert.doesNotMatch(await panel.innerText(),/Earlier source sample/);assert.equal(await panel.locator('.theme-claim-source').count(),1);
 assert.deepEqual(paid,[]);
 const before=(await(await page.request.get(base+'/api/v1/workspace?instrument_id='+iid)).json()).result;
 await panel.getByRole('button',{name:'Summarise discussions',exact:true}).click();await panel.getByRole('button',{name:'Summarise discussions',exact:true}).waitFor();
 assert.equal((await(await page.request.get(base+'/api/v1/companies/'+iid+'/discussion-themes')).json()).result.items.length,3);
 const after=(await(await page.request.get(base+'/api/v1/workspace?instrument_id='+iid)).json()).result;
 for(const key of ['versions','news_watch','sentiment','updates'])assert.deepEqual(before[key],after[key]);
 for(const width of [320,390,1440]){await page.setViewportSize({width,height:1050});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:`${shots}/thesis-themes-${width}.png`,fullPage:true});}
 // A poll sees the active reservation while this panel's own request is pending.
 // It must keep progress visible, without claiming another request blocks it.
 let release;
 const pendingResponse=new Promise(resolve=>{release=resolve;});
 await page.route('**/api/v1/companies/*/sentiment/*/discussion-themes',async r=>{
  modelStatus={...modelStatus,budget:{...modelStatus.budget,running:1,unresolved:1}};
  await pendingResponse;
  modelStatus={...modelStatus,budget:{...modelStatus.budget,running:0,unresolved:0}};
  await r.fulfill({json:{result:records.items[0]}});
 });
 await panel.getByRole('button',{name:'Summarise discussions',exact:true}).click();
 await panel.getByRole('button',{name:'Creating discussion summary…',exact:true}).waitFor();
 await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
 await sentiment.getByText(/AI is analysing a request/).waitFor();
 assert.match(await panel.innerText(),/Creating your summary and checking its evidence/);
 assert.doesNotMatch(await panel.innerText(),/Another AI request|unavailable right now/);
 assert.equal(await panel.getByRole('button',{name:'Creating discussion summary…',exact:true}).isDisabled(),true);
 assert.equal(paid.length,2);
 await panel.screenshot({path:`${shots}/thesis-themes-pending.png`});
 release();
 await panel.getByText('Discussion summary ready below.',{exact:true}).waitFor();
 assert.equal(await panel.getByRole('button',{name:'Summarise discussions',exact:true}).isEnabled(),true);
 await page.unroute('**/api/v1/companies/*/sentiment/*/discussion-themes');
 const failure='The AI reached its response limit before producing a discussion summary. No theme reading was saved. This AI attempt still used budget; no automatic retry was made.';
 await page.route('**/api/v1/companies/*/sentiment/*/discussion-themes',r=>r.fulfill({status:422,json:{result:{errors:[{error_message:failure}]}}}));
 await panel.getByRole('button',{name:'Summarise discussions',exact:true}).click();await panel.getByRole('alert').waitFor();assert.match(await panel.getByRole('alert').innerText(),/response limit.*still used budget/);assert.equal(await panel.locator('.theme-card').count(),1);
 await panel.screenshot({path:`${shots}/thesis-themes-failed.png`});
 // A read-only reload rechecks source permission; withdrawn evidence disappears.
 await page.route('**/api/v1/companies/*/discussion-themes?*',async r=>{const response=await r.fetch(),body=await response.json();for(const v of [body.result.current,...body.result.items])if(v){v.withheld=true;v.result=null;v.sources=[];}await r.fulfill({response,json:body});});
 await panel.getByRole('button',{name:'Reload saved readings',exact:true}).click();await panel.getByText('Source access changed. This interpretation and its evidence are withheld.',{exact:true}).waitFor();assert.equal(await panel.locator('.theme-card').count(),0);
 for(const [budget,message] of [
  [{unresolved:1,running:1,needs_attention:0,remaining_usd:'2'},'Another AI request is running.'],
  [{unresolved:1,running:0,needs_attention:1,remaining_usd:'2'},'ended without a confirmed charge'],
  [{unresolved:0,running:0,needs_attention:0,remaining_usd:'0'},'allowance has been used'],
 ]){
  modelStatus={briefing_enabled:true,budget};
  await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
  await panel.getByRole('status').filter({hasText:message}).waitFor();
  assert.equal(await panel.getByRole('button',{name:'Summarise discussions',exact:true}).isDisabled(),true);
  assert.equal(await panel.getByLabel('Saved theme reading',{exact:true}).isEnabled(),true);
 }
 modelStatus={...modelStatus,briefing_enabled:false};
 await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
 await panel.getByRole('status').filter({hasText:'AI is switched off'}).waitFor();
 assert.equal(await panel.getByRole('button',{name:'Summarise discussions',exact:true}).isDisabled(),true);
 await panel.screenshot({path:`${shots}/thesis-themes-blocked.png`});
 // The owner's no-history state still explains the outcome of a failed attempt.
 modelStatus={briefing_enabled:true,budget:{unresolved:0,running:0,needs_attention:0,remaining_usd:'10'}};
 await page.route('**/api/v1/companies/*/discussion-themes?*',r=>r.fulfill({json:{result:{current:null,items:[],next_cursor:null}}}));
 await page.reload();
 await page.getByRole('tab',{name:'News & discussion',exact:true}).click();
 await sentiment.getByText('What are people discussing?',{exact:true}).click();
 await panel.getByText('No discussion summary saved yet.',{exact:true}).waitFor();
 await panel.getByRole('button',{name:'Summarise discussions',exact:true}).click();
 await panel.getByRole('alert').filter({hasText:'response limit'}).waitFor();
 assert.equal(await panel.locator('.theme-card').count(),0);
 assert.match(await panel.innerText(),/No theme reading was saved/);
 for(const width of [1440,390,320]){
  await page.setViewportSize({width,height:1050});
  await page.evaluate(()=>window.scrollTo(0,0));
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`empty/error overflow ${width}`);
  await page.screenshot({path:`${shots}/thesis-themes-empty-error-${width}.png`,fullPage:true});
 }
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.equal(paid.length,4);
 console.log('Theme browser passed: separate platforms, saved parent and child evidence, same-issue differing view, source dialog, original quotes, immutable current/legacy history, source labels beside each claim, cached generation, export, unchanged watches/labels, pending own reservation without false warning, precise failure, blocked reasons with readable history and withdrawal, 320/390/1440 layouts. No paid calls.');
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();});
