const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');let browser;
(async()=>{
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
 const page=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'}), errors=[],writes=[],external=[];
 page.on('pageerror',e=>errors.push(e.message));await page.route('**/*',r=>{const u=new URL(r.request().url());if(!['127.0.0.1','localhost'].includes(u.hostname)){external.push(u.href);return r.abort();}if(r.request().method()!=='GET')writes.push(u.pathname);return r.continue();});
 const base=process.env.THESIS_TEST_URL,iid='c767e09f-35ea-5eaf-a626-ff5d3aa4709b';
 await page.goto(base+'/?company='+iid+'&view=workspace');await page.getByText('Compare sentiment samples',{exact:true}).click();
 const panel=page.locator('.sentiment-history'), comparison=page.getByRole('region',{name:'Sentiment sample comparison',exact:true});
 await comparison.waitFor();assert.match(await comparison.innerText(),/analysis method changed/);assert.match(await comparison.innerText(),/same texts were selected/);
 const options=await panel.getByLabel('Later sentiment sample',{exact:true}).locator('option').evaluateAll(es=>es.map(e=>e.value));assert.equal(options.length,3);
 const labels=await panel.getByLabel('Later sentiment sample',{exact:true}).locator('option').allTextContents();assert.equal(new Set(labels).size,3);
 await panel.getByLabel('Later sentiment sample',{exact:true}).selectOption(options[1]);
 await comparison.getByRole('region',{name:'Social sample changes',exact:true}).getByText('8 newly selected · 8 no longer selected · 0 relabeled · 0 unchanged',{exact:true}).waitFor();
 assert.doesNotMatch(await comparison.innerText(),/analysis method changed/);
 const social=comparison.getByRole('region',{name:'Social sample changes',exact:true});await social.getByText('Inspect compared texts (16)',{exact:true}).click();
 await social.getByRole('button',{name:'Inspect earlier source ↗',exact:true}).first().click();
 const dialog=page.getByRole('dialog',{name:'Historical sentiment source',exact:true});await dialog.waitFor();assert.match(await dialog.innerText(),/positive opinion/);
 await dialog.getByRole('button',{name:'Close dialog'}).click();assert.ok(await panel.isVisible());
 await panel.getByLabel('Earlier sentiment sample',{exact:true}).selectOption('');await comparison.waitFor({state:'detached'});assert.equal(await comparison.count(),0);
 await panel.getByLabel('Earlier sentiment sample',{exact:true}).selectOption(options[2]);await comparison.waitFor();
 assert.equal(await page.getByRole('checkbox',{name:'Watch news + social changes',exact:true}).isChecked(),false);
 for(const width of [320,390,1440]){await page.setViewportSize({width,height:1000});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:`/private/tmp/thesis-sentiment-history-${width}.png`,fullPage:true});}
 await page.reload();await page.getByText('Compare sentiment samples',{exact:true}).click();await comparison.waitFor();assert.match(await comparison.innerText(),/analysis method changed/);
 assert.deepEqual(errors,[]);assert.deepEqual(writes,[]);assert.deepEqual(external,[]);console.log('Sentiment history browser passed: method/reanalysis warnings, separate sample changes, exact earlier source, selection clearing, reload, disabled watch, phone/desktop, no writes or external requests.');await browser.close();
})().catch(async e=>{console.error(e);if(browser)await browser.close();process.exit(1);});
