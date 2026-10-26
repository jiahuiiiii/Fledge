const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
let browser;
(async () => {
  browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_PATH });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
  const base = process.env.THESIS_TEST_URL, iid = 'c767e09f-35ea-5eaf-a626-ff5d3aa4709b';
  const errors = [], writes = [];
  let refreshes = 0, fail = false;
  page.on('pageerror', e => errors.push(e.message));
  await page.request.get(base + '/api/v1/session');
  const saved = (await (await page.request.get(base + `/api/v1/companies/${iid}/price-history`)).json()).result;
  const time = Date.parse('2026-10-08T15:00:00Z');
  const fixture = structuredClone(saved);
  fixture.configured = true;
  fixture.error = null;
  fixture.next_refresh_at = new Date(time).toISOString();
  fixture.snapshot.retrieved_at = new Date(time - 120000).toISOString();
  fixture.snapshot.series.delay_minutes = 15;
  // Date the authored latest bar explicitly; the seed is completed history.
  fixture.snapshot.series.bars = fixture.snapshot.series.bars.filter(b=>b.date<'2026-10-08');
  fixture.snapshot.series.bars.push({date:'2026-10-08',open:'110',high:'120',low:'100',close:'111',volume:null,provisional:true});
  fixture.snapshot.series.latest_quote = {price:'111',quoted_at:new Date(time-120000).toISOString(),session:'regular session'};
  await page.clock.install({ time: new Date(time) });
  await page.route('**/*', async route => {
    const req = route.request(), url = new URL(req.url());
    if (!req.url().startsWith(base)) return route.abort();
    if (url.pathname.endsWith('/price-history/refresh')) {
      writes.push(url.pathname);
      const now = await page.evaluate(() => Date.now());
      // Model the server's shared cooldown: simultaneous header/chart reads
      // reuse the completed snapshot instead of manufacturing a second check.
      if (Date.parse(fixture.next_refresh_at) > now)
        return route.fulfill({json:{result:{id:fixture.snapshot.id,sessions:fixture.snapshot.series.bars.length}}});
      refreshes++;
      if (fail) return route.fulfill({ status: 429, json: { result: { errors: [{ error_message: 'Yahoo price check unavailable.' }] } } });
      fixture.snapshot.id = `authored-price-${refreshes}`;
      fixture.snapshot.retrieved_at = new Date(now).toISOString();
      fixture.next_refresh_at = new Date(now + 60000).toISOString();
      const series = fixture.snapshot.series;
      series.bars = series.bars.filter(b => b.date !== '2026-10-08');
      series.bars.push({ date: '2026-10-08', open: '110', high: '120', low: '100', close: String(111 + refreshes), volume: null, provisional: true });
      series.latest_quote = { price: String(111 + refreshes), quoted_at: new Date(now).toISOString(), session: 'regular session' };
      series.requested_through = new Date(now).toISOString();
      return route.fulfill({ json: { result: { id: fixture.snapshot.id, sessions: series.bars.length } } });
    }
    if (url.pathname.endsWith('/price-history') && url.pathname.includes(iid)) return route.fulfill({ json: { result: fixture } });
    if (req.method() !== 'GET') {
      if (url.pathname.endsWith('/loading')) return route.fulfill({ json: { result: null } });
      throw new Error('Unexpected write: ' + url.pathname);
    }
    return route.continue();
  });
  await page.goto(base + '/?company=' + iid + '&view=workspace');
  const {disclosure} = require('./browser_helpers.cjs');
  const panel = page.getByRole('region',{name:'Daily price history',exact:true});
  await page.getByRole('region',{name:'Company overview',exact:true}).waitFor();
  assert.equal(await panel.isVisible(),false,'the chart starts collapsed');
  assert.equal(refreshes,0,'initial render reads saved prices');
  // The company header now checks prices every minute independently of the chart.
  await page.clock.runFor(61000);
  await disclosure(page,'Price chart · past year');
  await page.mouse.move(1,1);
  await panel.locator('.price').getByText('112.00',{exact:true}).waitFor();
  assert.equal(refreshes,1,'the header refreshes while the chart is collapsed');
  assert.match(await panel.innerText(),/15-minute data delay/);
  await panel.getByRole('button',{name:'1M',exact:true}).click();
  await panel.getByRole('button',{name:'Candles',exact:true}).click();
  // A manual refresh observes the shared provider cooldown and reuses this read.
  await panel.getByRole('button',{name:'Refresh prices',exact:true}).click();
  assert.equal(refreshes,1,'a fresh shared snapshot is reused');
  await page.clock.runFor(61000);
  await page.mouse.move(1,1);
  await panel.locator('.price').getByText('113.00',{exact:true}).waitFor();
  assert.equal(refreshes,2);
  assert.equal(await panel.getByRole('button',{name:'1M',exact:true}).getAttribute('aria-pressed'),'true');
  assert.match(await panel.getByRole('img').getAttribute('aria-label'),/line chart/);
  await panel.getByRole('button',{name:'1Y',exact:true}).click();
  await panel.getByText('Inspect a trading session',{exact:true}).click();
  const slider=panel.getByRole('slider',{name:'Trading session',exact:true});
  await slider.focus(); await slider.press('Home');
  assert.equal(await slider.getAttribute('aria-valuetext'),fixture.snapshot.series.bars[0].date);
  assert.match(await panel.innerText(),/daily close/);
  await slider.press('End');
  assert.match(await panel.locator('output').innerText(),/provisional/);
  await panel.getByText('Inspect daily prices and source',{exact:true}).click();
  assert.equal(await panel.locator('tbody tr').count(),fixture.snapshot.series.bars.length);
  assert.match(await panel.innerText(),/no AI call/);
  for(const width of [320,390,1440]) {
    await page.setViewportSize({width,height:1000});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);
    await page.screenshot({path:`/private/tmp/thesis-latest-prices-${width}.png`});
  }
  await page.getByRole('tab',{name:'Financials',exact:true}).click();
  await page.clock.runFor(61000);
  assert.equal(refreshes,3,'the selected company header keeps updating on other research tabs');
  await page.getByRole('tab',{name:'Overview',exact:true}).click();
  await page.mouse.move(1,1);
  await panel.locator('.price').getByText('114.00',{exact:true}).waitFor();
  await disclosure(page,'Price chart · past year',false);
  await page.clock.runFor(61000);
  assert.equal(refreshes,4,'collapsing the chart preserves header updates');
  await disclosure(page,'Price chart · past year');
  await panel.locator('.price').getByText('115.00',{exact:true}).waitFor();
  // Explicit failures retain the last successful prices and expose the error.
  fail=true;
  fixture.next_refresh_at=new Date(await page.evaluate(()=>Date.now())-1).toISOString();
  await panel.getByRole('button',{name:'Refresh prices',exact:true}).click();
  await panel.getByRole('alert').getByText('Yahoo price check unavailable.',{exact:true}).waitFor();
  const failedCount=refreshes;
  assert.match(await panel.innerText(),/115.00/);
  fail=false;
  await panel.getByRole('button',{name:'Refresh prices',exact:true}).click();
  await panel.locator('.price').getByText(String(111+failedCount+1)+'.00',{exact:true}).waitFor();
  const beforeHidden=refreshes;
  await page.evaluate(()=>{
    Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});
    Object.defineProperty(document,'visibilityState',{configurable:true,get:()=> 'hidden'});
    document.dispatchEvent(new Event('visibilitychange'));
  });
  await page.clock.runFor(120000);
  assert.equal(refreshes,beforeHidden,'a hidden browser pauses both price timers');
  await page.evaluate(()=>{
    Object.defineProperty(document,'hidden',{configurable:true,get:()=>false});
    Object.defineProperty(document,'visibilityState',{configurable:true,get:()=> 'visible'});
    document.dispatchEvent(new Event('visibilitychange'));
  });
  await page.clock.runFor(1100);
  await panel.locator('.price').getByText(String(112+beforeHidden)+'.00',{exact:true}).waitFor();
  fixture.available=false; fixture.snapshot=null;
  const beforeWithdrawal=refreshes;
  await page.clock.runFor(61000);
  await panel.getByText(/Saved chart data is withheld/).waitFor();
  assert.equal(await panel.getByRole('img').count(),0);
  await page.clock.runFor(120000);
  assert.equal(refreshes,beforeWithdrawal,'withdrawn source is not fetched');
  assert.deepEqual(errors,[]);
  assert.ok(writes.every(p=>p.endsWith('/price-history/refresh')));
  console.log('Latest-price browser passed: collapsed chart, independent company-header updates, shared cooldown, ranges/mode, keyboard evidence, responsive layouts, failed-check retention and recovery, hidden-page pause and source withdrawal. Provider replies authored; no provider or AI dispatch.');
  await browser.close();
})().catch(async error => { console.error(error); if (browser) await browser.close(); process.exit(1); });
