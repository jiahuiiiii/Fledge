const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
let browser;
(async () => {
  browser = await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH ? {executablePath:process.env.CHROMIUM_PATH} : {})});
  const page = await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
  const openFinancials=async()=>{await page.getByRole('tab',{name:'Financials',exact:true}).click();};
  const openAnalystForecasts=async()=>{await openFinancials();const d=page.locator('.financial-analyst-disclosure');await d.waitFor();if(!await d.evaluate(el=>el.open))await d.locator('summary').first().click();};
  page.setDefaultTimeout(10000);
  const errors=[], external=[];let mockedLogos=0;page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',route=>{
    const url=route.request().url();
    if(url.startsWith(process.env.THESIS_TEST_URL))return route.continue();
    if(url==='https://financialmodelingprep.com/image-stock/MSFT.png'){mockedLogos++;return route.fulfill({status:404,body:'Authored missing logo'});}
    external.push(url);return route.abort();
  });
  await page.goto(process.env.THESIS_TEST_URL);
  await page.locator('.watch-item').filter({hasText:'MSFT'}).click();
  await page.getByRole('tab',{name:'Overview',exact:true}).click();
  // The brief sits in a closed disclosure under "The business".
  await page.getByText('Business brief and research questions',{exact:true}).click();
  const panel=page.getByRole('region',{name:'Understand the business',exact:true});
  await panel.getByText('The company says it sells subscription software to business customers.',{exact:true}).waitFor();
  await panel.getByRole('button',{name:'View source',exact:true}).click();
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
  await page.reload();
  await require('./browser_helpers.cjs').disclosure(page, 'Business brief and research questions');
  const evidenceTrigger = panel.getByRole('button',{name:'View source',exact:true});
  await evidenceTrigger.click();
  const businessEvidence = page.getByRole('dialog',{name:'Original evidence',exact:true});
  await businessEvidence.getByRole('button',{name:'Read full passage',exact:true}).waitFor();
  assert.match(await businessEvidence.locator('.business-evidence-claim').innerText(),/The company says it sells subscription software/);
  const excerpt = businessEvidence.locator('blockquote');
  assert.ok(longQuote.startsWith((await excerpt.textContent()).replace(/…$/, '').trim()), `Unexpected quote preview: ${await excerpt.textContent()}`);
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
  // Financials contains the retained revenue flow and financial reading.
  await page.getByRole('tab',{name:'Financials',exact:true}).click();
  await require('./browser_income_flow.cjs')(page);
  await page.getByRole('tab',{name:'Financials',exact:true}).click();
  const {disclosure}=require('./browser_helpers.cjs');
  await disclosure(page,'Reported figures and filings');
  await page.getByRole('button',{name:'Read saved document',exact:true}).first().click();
  await page.getByRole('dialog').getByText('Software | 120',{exact:true}).waitFor();
  await page.keyboard.press('Escape');
  await openAnalystForecasts();
  const forecasts=page.getByRole('region',{name:'Analyst forecasts',exact:true});
  const fmpRanges=forecasts.getByRole('region',{name:'FMP financial expectations',exact:true}).locator('.forecast-range');
  await fmpRanges.first().waitFor();
  assert.match(await fmpRanges.first().innerText(),/120/);
  assert.match(await fmpRanges.nth(1).innerText(),/-1/);
  assert.equal(await fmpRanges.nth(1).locator('.forecast-track > span').evaluate(el=>parseFloat(el.style.left)),50);
  assert.match(await fmpRanges.nth(1).locator('.forecast-endpoints').innerText(),/-2[\s\S]*0/);
  assert.match(await forecasts.innerText(),/currency: not supplied/i);
  const publicForecasts=forecasts.getByRole('region',{name:'Public annual financial forecasts',exact:true});
  await publicForecasts.getByRole('heading',{name:/FY 2026/}).waitFor();
  assert.match(await publicForecasts.innerText(),/currency is not stated/);
  assert.match(await publicForecasts.innerText(),/Restricted years \(2027\)/);
  assert.equal(await publicForecasts.getByRole('button',{name:'Update data'}).isDisabled(),true);
  await publicForecasts.getByText('Exact values & definition',{exact:true}).first().click();
  assert.match(await publicForecasts.innerText(),/105,970,000,000/);
  await disclosure(page,'What management expects');
  const outlook=page.getByRole('region',{name:'Management outlook',exact:true});
  await outlook.getByText('≈ $34.8bn',{exact:true}).waitFor();
  const guidanceEvidence=outlook.locator('.outlook-forecast').first().getByRole('button',{name:'Evidence',exact:true});
  await guidanceEvidence.focus();await page.keyboard.press('Enter');
  const guidanceDialog=page.getByRole('dialog',{name:/original guidance/});
  assert.match(await guidanceDialog.innerText(),/Fourth quarter revenue guidance of approximately \$34.8 billion/);
  assert.match(await guidanceDialog.innerText(),/Exact point: 34800000000/);
  assert.match(await guidanceDialog.innerText(),/SEC filing accepted/);
  await page.keyboard.press('Escape');
  assert.equal(await guidanceEvidence.evaluate(el=>document.activeElement===el),true);
  await outlook.getByText('Read the outlook in context',{exact:true}).click();
  assert.match(await outlook.innerText(),/cannot reconcile this non-GAAP forecast/);
  const releaseSelect=outlook.getByLabel('Saved release');
  await releaseSelect.selectOption({index:1});
  await outlook.getByText('Filed revenue: US$64bn',{exact:true}).waitFor();
  assert.match(await outlook.innerText(),/Within the displayed guidance range/);
  assert.match(await outlook.innerText(),/Historical source version/);
  await releaseSelect.selectOption({index:0});
  for(const width of [1440,980,390,320]) {
    await page.setViewportSize({width,height:1000});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Business/forecasts overflow ${width}`);
    await page.screenshot({path:`/private/tmp/thesis-business-forecasts-${width}.png`,animations:'disabled'});
  }
  // Missing public/FMP data keeps a correctly scoped external reading link.
  await page.route('**/companies/*/fmp',async route=>{
    const response=await route.fetch(),payload=await response.json();
    payload.result.consensus.data=null;
    payload.result.public_forecasts.snapshot=null;
    payload.result.public_forecasts.history=[];
    return route.fulfill({response,json:payload});
  });
  await page.reload();await openAnalystForecasts();
  await disclosure(page,'FMP forecasts unavailable');
  const alternative=forecasts.getByRole('link',{name:'Inspect public financial forecasts on Stock Analysis ↗',exact:true});
  await alternative.waitFor();
  assert.equal(await alternative.getAttribute('href'),'https://stockanalysis.com/stocks/msft/forecast/');
  assert.match(await forecasts.innerText(),/save the available annual table/);
  await page.unroute('**/companies/*/fmp');
  // Zero/negative forecasts remain valid; missing endpoints never invent a range.
  await page.route('**/companies/*/fmp',async route=>{
    const response=await route.fetch(),payload=await response.json();
    const forecast=payload.result.consensus.data.forecasts[0];
    Object.assign(forecast.metrics[0],{low:null,average:'0',high:null});
    Object.assign(forecast.metrics[1],{low:'0',average:'0',high:'0'});
    payload.result.public_forecasts.available=false;
    return route.fulfill({response,json:payload});
  });
  await page.reload();await openAnalystForecasts();
  await fmpRanges.first().waitFor();
  assert.match(await fmpRanges.first().locator('.forecast-average').innerText(),/^0/);
  assert.match(await fmpRanges.first().locator('.forecast-endpoints').innerText(),/Not available/);
  assert.equal(await fmpRanges.first().locator('.forecast-track').count(),0);
  assert.equal(await fmpRanges.nth(1).locator('.forecast-track > span').evaluate(el=>parseFloat(el.style.left)),50);
  assert.match(await publicForecasts.innerText(),/Access to this source is disabled/);
  assert.equal(await publicForecasts.locator('.forecast-range').count(),0);
  assert.equal(await publicForecasts.getByText(/Saved public forecast observations/).count(),0);
  assert.equal(await publicForecasts.getByRole('button',{name:'Update data'}).isDisabled(),true);
  await page.route('**/api/v1/workspace?*',async route=>{
    const response=await route.fetch(),payload=await response.json();
    payload.result.management_outlook={status:'unavailable',releases:[],message:'Original-filing source access is unavailable.',limitations:[]};
    return route.fulfill({response,json:payload});
  });
  await page.reload();await openFinancials();await disclosure(page,'What management expects');
  assert.equal(await outlook.locator('.outlook-value').count(),0);
  assert.match(await outlook.innerText(),/Original-filing source access is unavailable/);
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
  await page.getByRole('link',{name:'Account',exact:true}).click();
  const accountPage=page.getByRole('region',{name:'Account',exact:true});
  assert.match(await accountPage.innerText(),/authored@example.test/);
  assert.equal(await accountPage.getByRole('button',{name:'Sign out',exact:true}).count(),1);
  await page.screenshot({path:'/private/tmp/thesis-auth-account-menu-320.png',animations:'disabled'});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.getByRole('button',{name:'Sign out',exact:true}).click();
  await page.getByLabel('Email address',{exact:true}).waitFor();
  assert.equal(await page.locator('.revenue-flow').count(),0);
  await page.screenshot({path:'/private/tmp/thesis-phase87-login-320.png',fullPage:true});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
  assert.ok(mockedLogos>=1);
  console.log('Authored business citations, income flow, original filings, forecast ranges/source gaps, management guidance and sign-in UI pass. Dedicated history and peer checks remain in their own journeys. The missing-consensus external source link is correctly scoped and not fetched. External networking blocked and decorative logo mocked.');
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();});
