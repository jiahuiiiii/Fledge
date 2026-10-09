const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
let browser;
(async () => {
  browser = await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH ? {executablePath:process.env.CHROMIUM_PATH} : {})});
  const page = await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[], external=[];let mockedLogos=0,peerWrites=0;page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(r.url().endsWith('/fmp/peers')&&r.method()==='PUT')peerWrites++;});
  await page.route('**/*',route=>{
    const url=route.request().url();
    if(url.startsWith(process.env.THESIS_TEST_URL))return route.continue();
    if(url==='https://financialmodelingprep.com/image-stock/MSFT.png'){mockedLogos++;return route.fulfill({status:404,body:'Authored missing logo'});}
    external.push(url);return route.abort();
  });
  await page.goto(process.env.THESIS_TEST_URL);
  await page.locator('.watch-item').filter({hasText:'MSFT'}).click();
  await page.getByRole('tab',{name:'Overview',exact:true}).click();
  const panel=page.getByRole('region',{name:'Understand the business',exact:true});
  await panel.getByText('The company says it sells subscription software to business customers.',{exact:true}).waitFor();
  await panel.getByRole('button',{name:'Inspect evidence ↗',exact:true}).click();
  assert.match(await page.getByRole('dialog').innerText(),/We sell subscription software/);
  assert.match(await page.getByRole('dialog').getByRole('link').getAttribute('href'),/^https:\/\/www.sec.gov\/Archives\//);
  await page.keyboard.press('Escape');
  // Long authored citation reproduces the owner's wall-of-text layout without changing stored research.
  const longQuote = 'We sell subscription software to business customers. ' +
    'This authored filing passage describes products, customers, infrastructure and the context of the saved company statement. '.repeat(30);
  await page.route('**/companies/*/business', async route => {
    const response = await route.fetch(), payload = await response.json();
    for (const reading of [payload.result.current, payload.result.latest, ...(payload.result.items || [])]) {
      if (!reading?.result) continue;
      for (const finding of reading.result.findings) for (const citation of finding.citations) citation.quote = longQuote;
    }
    return route.fulfill({response, json: payload});
  });
  await page.getByRole('tab',{name:'Financials',exact:true}).click();
  await page.getByRole('tab',{name:'Overview',exact:true}).click();
  const evidenceTrigger = panel.getByRole('button',{name:'Inspect evidence ↗',exact:true});
  await evidenceTrigger.click();
  const businessEvidence = page.getByRole('dialog',{name:'Original evidence',exact:true});
  await businessEvidence.getByRole('button',{name:'Read full passage',exact:true}).waitFor();
  assert.match(await businessEvidence.locator('.business-evidence-claim').innerText(),/The company says it sells subscription software/);
  const excerpt = businessEvidence.locator('blockquote');
  assert.ok(longQuote.startsWith((await excerpt.textContent()).slice(0,-1)));
  assert.ok((await excerpt.textContent()).length <= 421);
  for (const [width,height] of [[1440,1000],[390,800],[320,640]]) {
    await page.setViewportSize({width,height});
    await businessEvidence.locator('.business-evidence-body').evaluate(el=>{el.scrollTop=0;});
    const bounds=await businessEvidence.boundingBox();
    assert.ok(bounds.x>=0 && bounds.x+bounds.width<=width && bounds.y>=0 && bounds.y+bounds.height<=height);
    assert.ok(await businessEvidence.evaluate(el=>el.scrollWidth<=el.clientWidth));
    assert.ok(await businessEvidence.locator('.business-evidence-body').evaluate(el=>parseFloat(getComputedStyle(el).paddingLeft)>=16));
    await page.screenshot({path:`/private/tmp/thesis-business-evidence-preview-${width}.png`,animations:'disabled'});
    await businessEvidence.getByRole('button',{name:'Read full passage',exact:true}).click();
    assert.equal(await excerpt.textContent(),longQuote);
    await businessEvidence.locator('.business-evidence-body').evaluate(el=>{el.scrollTop=el.scrollHeight;});
    const close=await businessEvidence.getByRole('button',{name:'Close dialog',exact:true}).boundingBox();
    const expandedBounds=await businessEvidence.boundingBox();
    assert.ok(close.y>=expandedBounds.y && close.y+close.height<expandedBounds.y+90,'close stays visible when the passage scrolls');
    await page.screenshot({path:`/private/tmp/thesis-business-evidence-full-${width}.png`,animations:'disabled'});
    await businessEvidence.getByRole('button',{name:'Show less',exact:true}).click();
    assert.ok((await excerpt.textContent()).length<=421);
  }
  await page.keyboard.press('Escape');
  assert.equal(await evidenceTrigger.evaluate(el=>document.activeElement===el),true);
  await evidenceTrigger.click();
  assert.equal(await businessEvidence.getByRole('button',{name:'Read full passage',exact:true}).getAttribute('aria-expanded'),'false');
  await page.keyboard.press('Escape');
  await page.unroute('**/companies/*/business');
  await page.setViewportSize({width:1440,height:1000});
  await page.getByRole('tab',{name:'Financials',exact:true}).click();
  await require('./browser_income_flow.cjs')(page);
  await page.getByRole('button',{name:'Read saved document',exact:true}).first().click();
  await page.getByRole('dialog').getByText('Software | 120',{exact:true}).waitFor();
  assert.match(await page.getByRole('dialog').innerText(),/Software \| 120/);
  await page.keyboard.press('Escape');
  await page.getByRole('tab',{name:'Outlook',exact:true}).click();
  const forecasts=page.getByRole('region',{name:'Analyst forecasts',exact:true});
  await forecasts.getByText(/^Revenue: average 120/).waitFor();
  assert.match(await forecasts.innerText(),/currency: not supplied/i);
  await page.getByRole('tab',{name:'Compare & value',exact:true}).click();
  const fmp=page.getByRole('region',{name:'Comparison peers',exact:true});
  await fmp.getByRole('button',{name:'Add comparison company'}).click();
  await fmp.getByLabel('Comparison company 1').selectOption('NVDA');
  await fmp.getByLabel('Why is this comparison useful?').fill('Authored comparison: different products, shared data-center demand.');
  // Navigating back loads current source data without discarding the draft.
  await page.getByRole('tab',{name:'Financials',exact:true}).click();
  await Promise.all([page.waitForResponse(r=>r.url().endsWith('/fmp')&&r.request().method()==='GET'),page.getByRole('tab',{name:'Compare & value',exact:true}).click()]);
  assert.equal(await fmp.getByLabel('Comparison company 1').inputValue(),'NVDA');
  assert.equal(await fmp.getByLabel('Why is this comparison useful?').inputValue(),'Authored comparison: different products, shared data-center demand.');
  await page.route('**/companies/*/fmp/refresh',async route=>{
    const saved=await page.request.get(route.request().url().replace('/refresh',''));
    const body=await saved.json();return route.fulfill({json:{result:{context:body.result,outcomes:[]}}});
  });
  await Promise.all([page.waitForResponse(r=>r.url().endsWith('/fmp/refresh')),fmp.getByRole('button',{name:'Check FMP data',exact:true}).click()]);
  assert.equal(await fmp.getByLabel('Comparison company 1').inputValue(),'NVDA');
  assert.equal(await fmp.getByLabel('Why is this comparison useful?').inputValue(),'Authored comparison: different products, shared data-center demand.');
  await page.unroute('**/companies/*/fmp/refresh');
  await Promise.all([page.waitForResponse(r=>r.url().endsWith('/fmp/peers')&&r.request().method()==='PUT'),fmp.getByRole('button',{name:'Save comparisons',exact:true}).click()]);
  await fmp.getByRole('heading',{name:'NVDA',exact:true}).waitFor();
  assert.match(await fmp.innerText(),/first observed/i);
  const peers=page.getByRole('region',{name:'Peer comparison',exact:true});
  await peers.getByText('29.38×',{exact:true}).waitFor();
  assert.match(await peers.innerText(),/45.13×/);
  assert.equal(await peers.locator('.peer-chart-row').count(),2);
  await peers.locator('details').first().getByText('Source & comparison context',{exact:true}).click();
  assert.match(await peers.innerText(),/Exact value: 29.375 times/);
  assert.match(await peers.innerText(),/peTTM/);
  await peers.locator('details').first().getByText('Source & comparison context',{exact:true}).click();
  await peers.getByLabel('Figure & source').selectOption('pe_fmp');
  assert.deepEqual(await peers.locator('.peer-chart-value').allTextContents(),['30×','50×']);
  await peers.getByLabel('Figure & source').selectOption('growth_sec');
  assert.deepEqual(await peers.locator('.peer-chart-value').allTextContents(),['23.08%','33.33%']);
  assert.match(await peers.innerText(),/Compared with 1 Oct 2023 – 30 Sept? 2024/);
  await peers.locator('details').first().getByText('Source & comparison context',{exact:true}).click();
  assert.match(await peers.locator('details').first().innerText(),/52000000000 USD/);
  assert.match(await peers.locator('details').first().innerText(),/Original source payload:/);
  assert.match(await peers.locator('details').first().getByRole('link').first().getAttribute('href'),/^https:\/\/www.sec.gov\/Archives\//);
  await peers.locator('details').first().getByText('Source & comparison context',{exact:true}).click();
  await peers.getByLabel('Figure & source').selectOption('margin_sec');
  assert.deepEqual(await peers.locator('.peer-chart-value').allTextContents(),['39.06%','20%']);
  await peers.getByLabel('Figure & source').selectOption('fcf_sec');
  assert.deepEqual(await peers.locator('.peer-chart-value').allTextContents(),['US$40bn','US$-6bn']);
  assert.ok(Math.abs(await peers.locator('.peer-chart-track > span').nth(1).evaluate(el=>parseFloat(el.style.width))-6/46*100)<.001);
  assert.ok(await peers.locator('.peer-chart-track > i').first().evaluate(el=>parseFloat(el.style.left)>0));
  await peers.locator('details').nth(1).getByText('Source & comparison context',{exact:true}).click();
  assert.match(await peers.locator('details').nth(1).innerText(),/PaymentsToAcquirePropertyPlantAndEquipment/);
  assert.match(await peers.locator('details').nth(1).getByRole('link').first().getAttribute('href'),/^https:\/\/www.sec.gov\/Archives\//);
  await peers.getByLabel('Figure & source').focus();await page.keyboard.press('End');await page.keyboard.press('Enter');
  assert.deepEqual(await peers.locator('.peer-chart-value').allTextContents(),['US$68bn','US$18bn']);
  await peers.getByLabel('Figure & source').selectOption('growth_sec');
  for(const width of [1440,980,390,320]) {
    await page.setViewportSize({width,height:1000});
    await page.evaluate(async()=>{await Promise.all(document.getAnimations().filter(a=>a.effect.getComputedTiming().iterations!==Infinity).map(a=>a.finished.catch(()=>{})));});
    await peers.getByRole('heading',{name:'Peer comparison',exact:true}).evaluate(el=>el.scrollIntoView({block:'center'}));
    await page.evaluate(()=>{
      const h=document.querySelector('.peer-chart h3'),main=h.closest('.main-workspace');
      const offset=h.getBoundingClientRect().top-(innerWidth>980?270:145);
      if(main && getComputedStyle(main).overflowY==='auto')main.scrollTop+=offset;else window.scrollBy(0,offset);
    });
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Peer comparison overflow ${width}`);
    await page.screenshot({path:`/private/tmp/thesis-phase93-peer-growth-${width}.png`});
  }
  await page.emulateMedia({reducedMotion:'reduce'});
  assert.equal(await peers.locator('.peer-chart-reading').evaluate(el=>getComputedStyle(el).animationName),'none');
  await page.emulateMedia({reducedMotion:'no-preference'});
  // A discarded edit restores saved choices without another peer write.
  await fmp.getByRole('button',{name:'Add comparison company'}).click();
  await page.getByRole('tab',{name:'Financials',exact:true}).click();
  await Promise.all([page.waitForResponse(r=>r.url().endsWith('/fmp')&&r.request().method()==='GET'),page.getByRole('tab',{name:'Compare & value',exact:true}).click()]);
  assert.equal(await fmp.getByLabel('Comparison company 2').count(),1);
  assert.equal(await peers.locator('.peer-chart-row').count(),2);
  await fmp.getByRole('button',{name:'Discard changes',exact:true}).click();
  assert.equal(await fmp.getByLabel('Comparison company 2').count(),0);
  assert.equal(peerWrites,1);
  // A read begun before Save must not overwrite the saved response when late.
  let releaseOldRead,readHeld;
  const held=new Promise(resolve=>{readHeld=resolve;});
  const release=new Promise(resolve=>{releaseOldRead=resolve;});
  await page.route('**/companies/*/fmp',async route=>{
    const response=await route.fetch();const body=await response.json();
    readHeld();await release;return route.fulfill({response,json:body});
  },{times:1});
  await page.getByRole('tab',{name:'Financials',exact:true}).click();
  await page.getByRole('tab',{name:'Compare & value',exact:true}).click();
  await held;
  await fmp.getByLabel('Why is this comparison useful?').fill('Revised authored comparison: preserve the saved reasoning after a late read.');
  await Promise.all([page.waitForResponse(r=>r.url().endsWith('/fmp/peers')&&r.request().method()==='PUT'),fmp.getByRole('button',{name:'Save comparisons',exact:true}).click()]);
  const oldResponse=page.waitForResponse(r=>r.url().endsWith('/fmp')&&r.request().method()==='GET');
  releaseOldRead();await oldResponse;
  await peers.locator('.peer-chart-row').nth(1).getByText('Source & comparison context',{exact:true}).click();
  await peers.getByText('Your reason: Revised authored comparison: preserve the saved reasoning after a late read.',{exact:true}).waitFor();
  assert.equal(await fmp.getByLabel('Why is this comparison useful?').inputValue(),'Revised authored comparison: preserve the saved reasoning after a late read.');
  assert.equal(peerWrites,2);
  await peers.locator('.peer-chart-row').nth(1).getByText('Source & comparison context',{exact:true}).click();
  await page.getByRole('tab',{name:'Outlook',exact:true}).click();
  const publicForecasts=page.getByRole('region',{name:'Public annual financial forecasts',exact:true});
  await publicForecasts.getByRole('heading',{name:/FY 2026/}).waitFor();
  assert.match(await publicForecasts.innerText(),/currency is not stated/);
  assert.match(await publicForecasts.innerText(),/Restricted years \(2027\)/);
  assert.equal(await publicForecasts.getByRole('button',{name:'Check public forecasts'}).isDisabled(),true);
  assert.match(await publicForecasts.innerText(),/-1.11/);
  await publicForecasts.getByText('Exact values & definition',{exact:true}).first().click();
  assert.match(await publicForecasts.innerText(),/105,970,000,000/);
  for (const width of [1440,390,320]) {
    await page.setViewportSize({width,height:1000});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Business overflow ${width}`);
    await publicForecasts.getByRole('heading',{name:'Public annual forecasts',exact:true}).evaluate(el=>el.scrollIntoView({block:'center'}));
    await page.screenshot({path:`/private/tmp/thesis-phase88-public-forecasts-${width}.png`});
    await publicForecasts.locator('.forecast-ranges').evaluate(el=>el.scrollIntoView({block:'center'}));
    await page.screenshot({path:`/private/tmp/thesis-phase88-public-ranges-${width}.png`});
    await page.screenshot({path:`/private/tmp/thesis-phase87-business-${width}.png`,fullPage:true});
    await forecasts.getByRole('heading',{name:'Analyst forecasts',exact:true}).scrollIntoViewIfNeeded();
    await page.screenshot({path:`/private/tmp/thesis-phase87-business-visible-${width}.png`});
  }
  await page.getByRole('tab',{name:'Financials',exact:true}).click();
  await page.getByRole('region',{name:'Trailing results and borrowing',exact:true}).waitFor();
  await page.getByRole('tab',{name:'Outlook',exact:true}).click();
  const outlook=page.getByRole('region',{name:'Management outlook',exact:true});
  await outlook.getByText('≈ $34.8bn',{exact:true}).waitFor();
  assert.match(await outlook.innerText(),/Accounting basis unspecified · currency unspecified/);
  assert.match(await outlook.innerText(),/NON-GAAP/);
  await outlook.getByText('Original guidance & evidence',{exact:true}).first().click();
  assert.match(await outlook.innerText(),/Fourth quarter revenue guidance of approximately \$34.8 billion/);
  await outlook.getByText('Read the outlook in context',{exact:true}).click();
  assert.match(await outlook.innerText(),/cannot reconcile this non-GAAP forecast/);
  const releaseSelect=outlook.getByLabel('Saved release');
  await releaseSelect.focus();await page.keyboard.press('End');await page.keyboard.press('Enter');
  await outlook.getByText('Filed revenue: US$64bn',{exact:true}).waitFor();
  assert.match(await outlook.innerText(),/Within the displayed guidance range/);
  assert.match(await outlook.innerText(),/Historical source version/);
  await releaseSelect.focus();await page.keyboard.press('Home');await page.keyboard.press('Enter');
  for(const width of [1440,980,390,320]) {
    await page.setViewportSize({width,height:1000});
    await page.evaluate(async()=>{await Promise.all(document.getAnimations().filter(a=>a.effect.getComputedTiming().iterations!==Infinity).map(a=>a.finished.catch(()=>{})));});
    await outlook.getByRole('heading',{name:'Management outlook',exact:true}).evaluate(el=>el.scrollIntoView({block:'center'}));
    await page.evaluate(()=>{
      const h=document.querySelector('.management-outlook h2'),main=h.closest('.main-workspace');
      const offset=h.getBoundingClientRect().top-(innerWidth>980?280:145);
      if(main && getComputedStyle(main).overflowY==='auto')main.scrollTop+=offset;else window.scrollBy(0,offset);
    });
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Management outlook overflow ${width}`);
    assert.ok(await outlook.locator('.outlook-value').first().evaluate(el=>parseFloat(getComputedStyle(el).fontSize)>=24));
    await page.screenshot({path:`/private/tmp/thesis-phase91-management-outlook-${width}.png`});
  }
  await page.emulateMedia({reducedMotion:'reduce'});
  assert.equal(await outlook.locator('.outlook-reading').evaluate(el=>getComputedStyle(el).animationName),'none');
  await page.emulateMedia({reducedMotion:'no-preference'});
  await page.getByRole('tab',{name:'Financials',exact:true}).click();
  const position=page.getByRole('region',{name:'What it owns and owes',exact:true});
  await position.getByText('US$200bn',{exact:true}).waitFor();
  assert.equal(await position.locator('.position-measure').count(),4);
  assert.match(await position.innerText(),/US\$90bn/);
  assert.match(await position.innerText(),/US\$30bn/);
  assert.match(await position.innerText(),/US\$68bn/);
  assert.equal(await position.locator('.position-track > span').nth(1).evaluate(el=>parseFloat(el.style.width)),45);
  await position.locator('.overview-evidence').first().getByText('Evidence',{exact:true}).click();
  assert.match(await page.getByRole('dialog').innerText(),/Exact value: 200000000000 USD/);
  assert.match(await page.getByRole('dialog').locator('a').first().getAttribute('href'),/^https:\/\/www.sec.gov\/Archives\//);
  await page.keyboard.press('Escape');
  for(const width of [1440,980,390,320]) {
    await page.setViewportSize({width,height:1000});
    await page.evaluate(async()=>{await Promise.all(document.getAnimations().filter(a=>a.effect.getComputedTiming().iterations!==Infinity).map(a=>a.finished.catch(()=>{})));});
    await position.getByRole('heading',{name:'What it owns and owes',exact:true}).evaluate(el=>el.scrollIntoView({block:'center'}));
    await page.evaluate(()=>{
      const h=document.querySelector('.financial-position h2'),main=h.closest('.main-workspace');
      const offset=h.getBoundingClientRect().top-(innerWidth>980?300:160);
      if(main && getComputedStyle(main).overflowY==='auto')main.scrollTop+=offset;else window.scrollBy(0,offset);
    });
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Financial position overflow ${width}`);
    await page.screenshot({path:`/private/tmp/thesis-phase90-financial-position-${width}.png`});
  }
  await page.emulateMedia({reducedMotion:'reduce'});
  assert.equal(await position.locator('.position-reading').evaluate(el=>getComputedStyle(el).animationName),'none');
  await page.emulateMedia({reducedMotion:'no-preference'});
  const mix=page.getByRole('region',{name:'Where revenue comes from',exact:true});
  await mix.locator('.mix-total').getByText('US$16bn',{exact:true}).waitFor();
  assert.match(await mix.innerText(),/62.5%/);
  await mix.locator('.mix-members details').first().getByText('Inspect figure',{exact:true}).click();
  assert.match(await mix.innerText(),/US\$10,000,000,000/);
  assert.match(await mix.locator('.mix-members details a').first().getAttribute('href'),/#f-qservices$/);
  // Keyboard selection, exact period separation and safe withholding for overlap.
  await mix.getByLabel('Reporting period').focus();
  await page.keyboard.press('End');await page.keyboard.press('Enter');
  assert.equal(await mix.locator('.mix-total strong').innerText(),'US$64bn');
  await mix.getByLabel('View by').selectOption('Products and services');
  assert.match(await mix.innerText(),/87.5%/);
  await mix.getByLabel('View by').selectOption('Reported geographies');
  assert.equal(await mix.locator('.mix-bar').count(),0);
  assert.equal(await mix.locator('.mix-member-track').count(),0);
  assert.match(await mix.innerText(),/do not exactly reconcile/);
  assert.match(await mix.innerText(),/Countries and regions may overlap/);
  await mix.getByLabel('View by').selectOption('Operating segments');
  for(const width of [1440,390,320]) {
    await page.setViewportSize({width,height:1000});
    await page.evaluate(async()=>{await Promise.all(document.getAnimations().filter(a=>a.effect.getComputedTiming().iterations!==Infinity).map(a=>a.finished.catch(()=>{})));});
    await mix.getByRole('heading').evaluate(el=>el.scrollIntoView({block:'center'}));
    await page.evaluate(()=>{
      const heading=document.querySelector('.revenue-mix h2');
      const main=heading.closest('.main-workspace');
      const desired=innerWidth>980?300:160;
      const offset=heading.getBoundingClientRect().top-desired;
      if(main && getComputedStyle(main).overflowY==='auto')main.scrollTop+=offset;
      else window.scrollBy(0,offset);
    });
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Revenue mix overflow ${width}`);
    await page.screenshot({path:`/private/tmp/thesis-phase89-revenue-mix-${width}.png`});
  }
  await page.emulateMedia({reducedMotion:'reduce'});
  assert.equal(await mix.locator('.mix-reading').evaluate(el=>getComputedStyle(el).animationName),'none');
  await page.emulateMedia({reducedMotion:'no-preference'});
  const overview=page.getByRole('region',{name:'Financial overview',exact:true});
  await overview.getByRole('heading',{name:'Revenue, profitability & cash',exact:true}).waitFor();
  await overview.locator('.revenue-column').first().click();
  await overview.locator('.revenue-reading').getByText('Evidence',{exact:true}).click();
  assert.match(await page.getByRole('dialog').innerText(),/Exact value/);
  assert.match(await page.getByRole('dialog').getByRole('link').first().getAttribute('href'),/^https:\/\/www.sec.gov\/Archives\//);
  await page.keyboard.press('Escape');
  for (const width of [1600,1440,980,390,320]) {
    await page.setViewportSize({width,height:1000});
    await overview.scrollIntoViewIfNeeded();
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Fundamentals overflow ${width}`);
    await page.screenshot({path:`/private/tmp/thesis-phase87-fundamentals-${width}.png`,fullPage:true});
    await overview.getByRole('heading',{name:'Revenue, profitability & cash',exact:true}).scrollIntoViewIfNeeded();
    await overview.getByRole('heading',{name:'Revenue, profitability & cash',exact:true}).evaluate(el=>el.scrollIntoView({block:'start'}));
    await page.evaluate(()=>window.scrollBy(0,innerWidth>980?-270:-140));
    await page.screenshot({path:`/private/tmp/thesis-phase87-fundamentals-visible-${width}.png`});
    await overview.locator('.revenue-chart').evaluate(el=>el.scrollIntoView({block:'start'}));
    await page.evaluate(()=>window.scrollBy(0,innerWidth>980?-300:-190));
    await page.screenshot({path:`/private/tmp/thesis-phase87-revenue-visible-${width}.png`});
  }
  // Authored edge cases exercise missing/negative data without provider calls.
  await page.route('**/api/v1/workspace?*',async route=>{
    const response=await route.fetch();const payload=await response.json();
    payload.result.management_outlook={status:'unavailable',releases:[],message:'Original-filing source access is unavailable.',limitations:[]};
    const data=payload.result.financial_depth;
    const annual=payload.result.performance?.reports?.annual;
    if(annual) {
      const previous=structuredClone(annual);
      Object.assign(previous,{period_end:'2025-06-30',form:'10-Q',accession:'authored-earlier-quarter'});
      previous.metrics.forEach(row=>{row.end=previous.period_end;row.inputs.forEach(input=>{input.end=previous.period_end;input.accession=previous.accession;});});
      const cash=previous.metrics.find(row=>row.key==='cash');cash.value='0';cash.inputs[0].value='0';
      payload.result.performance.reports.quarter=previous;
      // A mismatched source fact must be withheld, even if its displayed row date matches.
      annual.metrics.find(row=>row.key==='liabilities').inputs[0].end='2024-09-30';
    }
    const segments=payload.result.segment_revenue;
    if(segments?.groups?.length) {
      for(const group of segments.groups) {
        group.chartable=false;group.reason='Authored missing category: percentage mix is withheld.';
        group.members[0].value=null;group.members[0].reason='Authored missing category';
        group.members.forEach(member=>member.percentage=null);
      }
    }
    if(data?.status==='available') {
      data.revenue_trend=[
        {period_end:'2021-09-30',value:'1000000000',inputs:[]},
        {period_end:'2022-09-30',value:null,reason:'Authored missing annual report',inputs:[]},
        {period_end:'2023-09-30',value:'3000000000',inputs:[]},
        {period_end:'2024-09-30',value:'4000000000',inputs:[]},
        {period_end:'2025-09-30',value:'2000000000',inputs:[]}
      ];
      const cash=data.trailing.find(row=>row.key==='operating_cash');
      const capital=data.trailing.find(row=>row.key==='capital_spending');
      const free=data.trailing.find(row=>row.key==='free_cash_flow');
      Object.assign(cash,{value:'1000000000',start:'2024-10-01',end:'2025-09-30'});
      Object.assign(capital,{value:'2000000000',start:cash.start,end:cash.end});
      Object.assign(free,{value:'-1000000000',start:cash.start,end:cash.end});
    }
    return route.fulfill({response,json:payload});
  });
  await page.reload();
  await page.getByRole('tab',{name:'Financials',exact:true}).click();
  await page.getByRole('tab',{name:'Outlook',exact:true}).click();
  assert.equal(await outlook.locator('.outlook-value').count(),0);
  assert.match(await outlook.innerText(),/Original-filing source access is unavailable/);
  await page.getByRole('tab',{name:'Financials',exact:true}).click();
  assert.match(await position.locator('.position-measure').nth(1).innerText(),/Unavailable/);
  assert.equal(await position.locator('.position-measure').nth(1).locator('.position-track').count(),0);
  await position.getByLabel('Balance-sheet date').focus();
  await page.keyboard.press('End');await page.keyboard.press('Enter');
  assert.match(await position.locator('.position-measure').nth(2).innerText(),/US\$0/);
  assert.equal(await position.locator('.position-measure').nth(2).locator('.position-track > span').evaluate(el=>parseFloat(el.style.width)),0);
  assert.match(await position.locator('.position-measure').nth(3).innerText(),/Unavailable/);
  assert.equal(await position.locator('.position-measure').nth(3).locator('.position-track').count(),0);
  assert.match(await mix.innerText(),/Unavailable/);
  assert.equal(await mix.locator('.mix-bar').count(),0);
  await overview.getByRole('button',{name:/fiscal year ended 30 Sep.*2022: Unavailable/}).click();
  assert.match(await overview.locator('.revenue-reading').innerText(),/Unavailable/);
  assert.equal(await overview.locator('.revenue-column[aria-pressed=true] .revenue-bar').count(),0);
  assert.equal(await overview.locator('.cash-bar-2').evaluate(el=>parseFloat(el.style.width)>0),true);
  assert.match(await overview.locator('.cash-measure').last().innerText(),/US\$-1bn/);
  await page.emulateMedia({reducedMotion:'reduce'});
  assert.equal(await overview.locator('.revenue-reading').evaluate(el=>getComputedStyle(el).animationName),'none');
  await page.screenshot({path:'/private/tmp/thesis-phase87-fundamentals-edge-320.png',fullPage:true});
  await overview.locator('.revenue-chart').evaluate(el=>el.scrollIntoView({block:'start'}));
  await page.evaluate(()=>window.scrollBy(0,-190));
  await page.screenshot({path:'/private/tmp/thesis-phase87-revenue-edge-visible-320.png'});
  await page.route('**/companies/*/fmp',async route=>{
    const response=await route.fetch();const payload=await response.json();
    payload.result.consensus.data=null;
    payload.result.public_forecasts.snapshot=null;
    payload.result.public_forecasts.history=[];
    payload.result.members[0].saved_finnhub.metrics.earnings.value='0';
    payload.result.members[1].saved_finnhub=null;
    payload.result.members[0].annual_growth.metric.value=null;
    payload.result.members[0].annual_growth.metric.reason='Authored: compatible annual prior revenue is unavailable.';
    payload.result.members[1].annual_growth={status:'unavailable',reason:'Structured filing source access is unavailable.'};
    return route.fulfill({response,json:payload});
  });
  await page.reload();
  await page.getByRole('tab',{name:'Compare & value',exact:true}).click();
  await page.getByRole('tab',{name:'Outlook',exact:true}).click();
  const alternative=forecasts.getByRole('link',{name:'Inspect public financial forecasts on Stock Analysis ↗',exact:true});
  await alternative.waitFor();
  assert.equal(await alternative.getAttribute('href'),'https://stockanalysis.com/stocks/msft/forecast/');
  assert.match(await forecasts.innerText(),/save the available annual table/);
  await page.getByRole('tab',{name:'Compare & value',exact:true}).click();
  await peers.locator('.peer-chart-value').nth(1).waitFor();
  assert.deepEqual(await peers.locator('.peer-chart-value').allTextContents(),['Unavailable','Unavailable']);
  assert.equal(await peers.locator('.peer-chart-track').count(),0);
  await peers.getByLabel('Figure & source').selectOption('pe_fmp');
  assert.deepEqual(await peers.locator('.peer-chart-value').allTextContents(),['30×','50×']);
  await peers.getByLabel('Figure & source').selectOption('growth_sec');
  assert.deepEqual(await peers.locator('.peer-chart-value').allTextContents(),['Unavailable','Unavailable']);
  assert.equal(await peers.locator('.peer-chart-track').count(),0);
  assert.match(await peers.innerText(),/compatible annual prior revenue is unavailable/);
  // Controlled sign-in UI check. These are authored responses; no email is sent.
  await page.route('**/api/v1/session',route=>route.fulfill({json:{result:{mode:'managed',authenticated:false}}}));
  let sent=0;
  await page.route('**/api/v1/auth/login',route=>{sent++;return route.fulfill({json:{result:{message:'Open the newest sign-in email in this browser. The link works once.'}}});});
  await page.reload();
  await page.getByLabel('Email address').fill('authored@example.test');
  await page.getByRole('button',{name:'Email me a sign-in link'}).click();
  await page.getByRole('status').filter({hasText:'newest sign-in email'}).waitFor();
  assert.equal(sent,1);assert.equal(await page.getByRole('region',{name:'Understand the business',exact:true}).count(),0);
  assert.equal(await page.getByRole('button',{name:/Request another link in \d+s/}).isDisabled(),true);
  await page.screenshot({path:'/private/tmp/thesis-auth-countdown-320.png',fullPage:true,animations:'disabled'});
  await page.clock.install();
  await page.clock.fastForward(61000);
  await page.route('**/api/v1/auth/login',route=>route.fulfill({status:429,headers:{'Retry-After':'2'},json:{result:{errors:[{error_message:'A sign-in email was requested recently. The countdown shows when you can request another.'}]}}}));
  await page.getByRole('button',{name:'Email me a sign-in link',exact:true}).click();
  await page.getByRole('alert').filter({hasText:'requested recently'}).waitFor();
  assert.equal(await page.getByRole('button',{name:/Request another link in \d+s/}).isDisabled(),true);
  await page.clock.fastForward(3000);
  assert.equal(await page.getByRole('button',{name:'Email me a sign-in link',exact:true}).isEnabled(),true);
  assert.equal(await page.getByLabel('Email address').inputValue(),'authored@example.test');
  await page.route('**/api/v1/session',route=>route.fulfill({json:{result:{mode:'managed',authenticated:true,account_id:'11111111-1111-4111-8111-111111111111',email:'authored@example.test',is_installation_owner:true}}}));
  await page.reload();
  await page.locator('.account-menu summary').click();
  assert.match(await page.locator('.account-menu').innerText(),/authored@example.test/);
  assert.match(await page.locator('.account-menu').innerText(),/monitoring settings are private/);
  await page.screenshot({path:'/private/tmp/thesis-auth-account-menu-320.png',animations:'disabled'});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.getByRole('button',{name:'Sign out',exact:true}).click();
  await page.getByRole('heading',{name:'Sign in to your research',exact:true}).waitFor();
  assert.equal(await page.locator('.revenue-flow').count(),0);
  await page.screenshot({path:'/private/tmp/thesis-phase87-login-320.png',fullPage:true});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
  assert.ok(mockedLogos>=1);
  console.log('Authored business, original evidence, private peers and sign-in UI pass; financial visuals pass at 1600/1440/980/390/320px, including unavailable annual values, negative cash flow and reduced motion. The missing-consensus external source link is correctly scoped and not fetched. External networking blocked and decorative logo mocked.');
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();});
