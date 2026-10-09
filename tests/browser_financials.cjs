const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
let browser;
(async () => {
  browser = await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH ? {executablePath:process.env.CHROMIUM_PATH} : {})});
  const page = await browser.newPage({viewport:{width:1440,height:1100}});
  const errors=[], external=[], writes=[];
  const folder=process.env.THESIS_FINANCIALS_SCREENSHOTS || '/private/tmp/thesis-financials-screenshots';fs.mkdirSync(folder,{recursive:true});
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',route=>{
    const request=route.request(), url=request.url();
    if(url.startsWith(process.env.THESIS_TEST_URL)){
      if(url.endsWith('/loading'))return route.fulfill({json:{result:null}});
      if(['POST','PUT','DELETE'].includes(request.method())){writes.push({url,method:request.method()});return route.fulfill({status:403,json:{result:{error:'Test blocks unexpected writes'}}});}
      return route.continue();
    }
    if(url.startsWith('https://financialmodelingprep.com/image-stock/'))return route.fulfill({status:404,body:'Authored missing logo'});
    external.push(url);return route.abort();
  });
  await page.goto(process.env.THESIS_TEST_URL);
  await page.locator('.watch-item').filter({hasText:'MSFT'}).click();
  await page.getByRole('tab',{name:'Financials',exact:true}).click();
  const story=page.locator('.financials-story');
  const history=page.getByRole('region',{name:'Earnings and cash-flow history',exact:true});
  const position=page.getByRole('region',{name:'Liquidity detail',exact:true});
  const more=page.locator('.financial-more-detail');
  const debt=page.getByRole('region',{name:'Borrowing and equity history',exact:true});
  const balance=page.getByRole('region',{name:'Balance-sheet breakdown',exact:true});
  await history.locator('.story-selected-values').getByText('US$64bn',{exact:true}).waitFor();
  assert.equal(await story.locator(':scope > .financial-story-section:visible').count(),3);
  await more.locator(':scope > summary').click();
  assert.match(await story.innerText(),/23.1% higher/);
  assert.match(await story.innerText(),/US\$31.3 in net result/);
  assert.match(await story.innerText(),/left US\$40bn/);

  assert.match(await position.innerText(),/US\$30bn surplus/);
  assert.match(await debt.innerText(),/US\$38bn remains/);
  assert.match(await debt.innerText(),/61.8%/);
  assert.match(await debt.innerText(),/66.2%/);
  assert.match(await debt.innerText(),/6.3 times/);
  assert.equal(await position.locator('.story-pair-track > span').count(),4);
  const heights=await position.locator('.story-pair-track > span').evaluateAll(els=>els.map(el=>parseFloat(el.style.height)));
  assert.ok(Math.abs(heights[0]/heights[2]-60/140)<1e-6);
  const tiles=await balance.locator('.story-balance-map').first().locator('.story-map-block').evaluateAll(els=>els.map(el=>({area:parseFloat(el.style.width)*parseFloat(el.style.height),label:el.title})));
  assert.ok(Math.abs(tiles.reduce((sum,tile)=>sum+tile.area,0)-10000)<1e-2);
  assert.ok(Math.abs(tiles.find(tile=>tile.label.startsWith('Cash')).area-1500)<1e-2);
  const trigger=page.locator('.financial-summary-row article').first().getByRole('button');

  await trigger.focus();await page.keyboard.press('Enter');
  const evidence=page.getByRole('dialog',{name:/Revenue growth · (past 12 months|fiscal year)/,exact:true});
  assert.match(await evidence.innerText(),/US\$64 bil/);
  assert.match(await evidence.innerText(),/US\$52 bil/);
  assert.doesNotMatch(await evidence.innerText(), /RevenueFromContract|accession|64000000000/);
  assert.match(await evidence.getByRole('link').first().getAttribute('href'),/^https:\/\/www.sec.gov\/Archives\//);
  await page.keyboard.press('Escape'); assert.equal(await trigger.evaluate(el=>document.activeElement===el),true);
  const slider=history.getByLabel('Sales, earnings and cash flow reporting date');
  await slider.focus();await page.keyboard.press('Home');await page.keyboard.press('ArrowRight');await page.keyboard.press('ArrowRight');
  assert.match(await story.innerText(),/30 Sept? 2023/);
  assert.match(await story.innerText(),/period ended in a loss/);
  assert.match(await story.innerText(),/−US\$3bn/);
  await history.getByRole('button',{name:'Operating cash flow',exact:true}).click();
  assert.equal(await history.getByRole('button',{name:'Operating cash flow',exact:true}).getAttribute('aria-pressed'),'true');
  await story.getByRole('button',{name:'Fiscal year',exact:true}).click();
  assert.equal(await story.getByRole('button',{name:'Fiscal year',exact:true}).getAttribute('aria-pressed'),'true');
  await page.getByRole('tab',{name:'Overview',exact:true}).click();
  assert.equal(await story.locator('.revenue-flow:visible').count(),0);
  assert.equal(await page.locator('.overview-section .revenue-flow:visible').count(),1);
  await page.getByRole('tab',{name:'Financials',exact:true}).click();
  assert.equal(await story.getByRole('button',{name:'Fiscal year',exact:true}).getAttribute('aria-pressed'),'true');
  await slider.focus();await page.keyboard.press('End');
  for(const [width,height] of [[1440,1100],[980,1000],[390,844],[320,740]]) {
    await page.setViewportSize({width,height});
    for(const [name,section] of [['history',history],['position',position],['borrowing',debt],['balance',balance]]) {

      await section.scrollIntoViewIfNeeded();await page.mouse.move(1,1);
      if(!await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)){console.log(await page.evaluate(()=>[...document.querySelectorAll('.main-workspace *')].filter(el=>{const r=el.getBoundingClientRect();return r.width && r.right>innerWidth+1&&!el.closest('.story-chart-viewport,.flow-viewport,.revenue-chart-viewport')}).map(el=>({tag:el.tagName,cls:el.className,width:el.getBoundingClientRect().width,scroll:el.scrollWidth,text:el.textContent.slice(0,60)})).slice(0,40)));await page.screenshot({path:path.join(folder,`page-overflow-${name}-${width}.png`)});}
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`page overflow ${name} ${width}`);
      if(!await section.evaluate(el=>el.scrollWidth<=el.clientWidth)){
        console.log(await section.evaluate(el=>({width:el.clientWidth,scroll:el.scrollWidth,offenders:[...el.querySelectorAll('*')].filter(child=>{const r=child.getBoundingClientRect(),p=el.getBoundingClientRect();return r.right>p.right+1 && !child.closest('.story-chart-viewport');}).map(child=>({tag:child.tagName,cls:child.className,width:child.getBoundingClientRect().width,text:child.textContent.slice(0,70)}))})));
        await page.screenshot({path:path.join(folder,`overflow-${name}-${width}.png`)});
      }
      assert.ok(await section.evaluate(el=>el.scrollWidth<=el.clientWidth),`section overflow ${name} ${width}`);
      await section.getByRole('heading').first().evaluate(el=>el.scrollIntoView({block:'start'}));
      await page.evaluate(()=>{const chrome=document.querySelector('.company-header');const main=document.querySelector('.main-workspace');if(main&&getComputedStyle(main).overflowY==='auto')main.scrollTop-=chrome?.getBoundingClientRect().height+100||100;else window.scrollBy(0,-150);});
      await page.screenshot({path:path.join(folder,`${name}-${width}.png`),animations:'disabled'});
      if(name==='borrowing') {await section.locator('.financial-insights').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(folder,`${name}-readings-${width}.png`),animations:'disabled'});}
    }

    await trigger.click();await evidence.waitFor();
    assert.ok(await evidence.evaluate(el=>el.scrollWidth<=el.clientWidth));
    await page.keyboard.press('Escape');
  }
  await page.emulateMedia({reducedMotion:'reduce'});
  assert.equal(await story.locator('.story-history-svg').first().evaluate(el=>getComputedStyle(el).animationName),'none');
  await page.emulateMedia({reducedMotion:'no-preference'});
  await page.setViewportSize({width:1440,height:1100});
  // Authored missing value, changed reporting basis, negative equity and cash
  // spending greater than operating cash exercise safe gaps and explanations.
  await page.route('**/companies/*/financial-story',async route=>{
    const response=await route.fetch(),payload=await response.json(),data=payload.result;
    for(const rows of [data.annual,data.trailing]) {
      rows[1].metrics.find(row=>row.key==='revenue').value=null;
      const latest=rows.at(-1);
      for(const [key,value] of [['operating_cash','1000000000'],['capital_spending','2000000000'],['free_cash_flow','-1000000000']])latest.metrics.find(row=>row.key===key).value=value;
    }
    const latest=data.balances.at(-1);
    for(const [key,value] of [['current_liabilities',null],['equity','-10000000000'],['debt_equity',null],['other_assets',null]])latest.metrics.find(row=>row.key===key).value=value;
    return route.fulfill({response,json:payload});
  });
  await page.reload();await page.getByRole('tab',{name:'Financials',exact:true}).click();
  await history.locator('.story-selected-values').getByText('−US$1bn',{exact:true}).waitFor();
  await more.locator(':scope > summary').click();
  assert.match(await story.innerText(),/fell short by US\$1bn/);

  assert.match(await position.innerText(),/Missing obligations are not zero/);
  assert.match(await debt.innerText(),/ratio unavailable/);
  assert.equal(await balance.locator('.story-map-block').count(),0);

  assert.equal((await history.locator('.series-revenue path').getAttribute('d')).match(/M/g).length,2);
  await page.screenshot({path:path.join(folder,'missing-desktop.png'),animations:'disabled'});
  await page.unroute('**/companies/*/financial-story');
  await page.route('**/companies/*/financial-story',route=>route.fulfill({json:{result:{status:'unavailable',reason:'Authored source access withdrawn.'}}}));
  await page.reload();await page.getByRole('tab',{name:'Financials',exact:true}).click();
  await story.getByText('Authored source access withdrawn.',{exact:true}).waitFor();
  assert.equal(await story.locator('.story-history-svg').count(),0);
  assert.equal(await story.locator('.story-map-block').count(),0);
  assert.equal(await story.locator('.story-pair-track > span').count(),0);
  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.deepEqual(writes,[]);
  console.log('Financials passed: 3 main charts plus expanded detail, shared scales, proportional blocks, exact evidence, keyboard, retained selections, source gaps/withdrawal and 1440/980/390/320px; zero writes or external requests.');
  await browser.close();
})().catch(async error=>{console.error(error);if(browser)await browser.close();process.exit(1);});
