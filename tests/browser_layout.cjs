// Read-only layout regression against an already running local app.
// Does not refresh sources, enable watches, generate research or save edits.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const os = require('node:os');
let browser;
(async () => {
  browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_PATH });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, reducedMotion: 'reduce' });
  const errors = [], writes = [], external = [], checked = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.route('**/*', route => {
    const request = route.request(), url = new URL(request.url());
    if (!['127.0.0.1', 'localhost'].includes(url.hostname)) {
      external.push(url.hostname); return route.abort();
    }
    if (request.method() !== 'GET') {
      writes.push(url.pathname); return route.abort();
    }
    return route.continue();
  });
  const base = process.env.THESIS_TEST_URL || 'http://127.0.0.1:8841';
  const company = process.env.THESIS_LAYOUT_COMPANY || '528be36b-8e44-57e9-a9fa-fbd2ee8bbdd1';
  await page.goto(`${base}/?company=${company}&view=workspace`);
  await page.locator('.company-header').waitFor();
  const sentiment = page.getByRole('region', { name: 'News and social sentiment', exact: true });
  await sentiment.waitFor();
  assert.ok(await page.locator('.reasoning').evaluate(e => parseFloat(getComputedStyle(e).fontSize) >= 14));
  for (const selector of ['.watch-options', '.private-check-options', '.monitoring-details', '.price-inspection']) {
    assert.equal(await page.locator(selector).evaluate(e => e.open), false, `${selector} starts disclosed on demand`);
  }
  assert.equal(await page.getByText('Draft first. Monitoring when you’re ready.', { exact: true }).count(), 0);
  const main = page.locator('.main-workspace');
  const geometry = () => page.evaluate(() => {
    const box = s => document.querySelector(s).getBoundingClientRect().toJSON();
    const main = document.querySelector('.main-workspace');
    return { header: box('.topbar'), footer: box('.workspace-footer'), main: box('.main-workspace'),
      watch: box('.watchlist'), idea: box('.idea-panel'),
      pageWidth: document.documentElement.scrollWidth, pageHeight: document.documentElement.scrollHeight,
      mainWidth: main.scrollWidth, mainClient: main.clientWidth, scroll: main.scrollTop };
  });
  for (const [width, height] of [[2560,1440],[1920,1080],[1440,900],[1280,800],[1024,768],[800,900]]) {
    console.log(`Checking ${width}x${height}`);
    await page.setViewportSize({ width, height });
    await main.evaluate(e => e.scrollTo(0, 0));
    const before = await geometry();
    assert.ok(before.pageWidth <= width, `document overflow ${width}`);
    assert.ok(before.pageHeight <= height + 1, `desktop frame grows ${width}`);
    assert.ok(before.mainWidth <= before.mainClient + 1, `main overflow ${width}`);
    assert.equal(before.header.y, 0);
    assert.equal(before.footer.x, 0);
    assert.equal(before.footer.width, width);
    assert.ok(Math.abs(before.footer.bottom - height) <= 1, `footer bottom ${width}`);
    assert.ok(before.main.bottom <= before.footer.y + 1);
    if (width > 980) {
      assert.equal(before.watch.x, 0);
      assert.ok(Math.abs(before.watch.right - before.main.x) <= 1);
    }
    assert.ok(Math.abs(before.main.right - before.idea.x) <= 1);
    await main.focus();
    await page.keyboard.press('PageDown');
    await page.waitForFunction(() => document.querySelector('.main-workspace').scrollTop > 100, { }, { timeout: 5000 });
    // Let native PageDown animation finish before resetting or resizing the pane.
    await page.waitForTimeout(350);
    const after = await geometry();
    assert.equal(after.header.y, before.header.y);
    assert.equal(after.footer.y, before.footer.y);
    assert.equal(after.watch.y, before.watch.y);
    assert.equal(after.idea.y, before.idea.y);
    await main.evaluate(e => e.scrollTop = e.scrollHeight);
    assert.ok(await main.evaluate(e => Math.abs(e.scrollHeight - e.clientHeight - e.scrollTop) < 2));
    const aside = page.locator('.idea-panel');
    await aside.evaluate(e => e.scrollTop = e.scrollHeight);
    assert.ok(await aside.evaluate(e => Math.abs(e.scrollHeight - e.clientHeight - e.scrollTop) < 2));
    await aside.evaluate(e => e.scrollTop = 0);
    await main.evaluate(e => e.scrollTop = 0);
    await main.evaluate(e => e.blur());
    await page.screenshot({ path: path.join(process.env.THESIS_LAYOUT_SCREENSHOTS || os.tmpdir(), `thesis-layout-${width}.png`) });
    checked.push(`${width}x${height}`);
  }
  await page.setViewportSize({ width: 1920, height: 1080 });
  const search = page.getByPlaceholder('Name or symbol');
  await search.fill('GOOGL');
  assert.equal(await page.locator('.company-row .watch-item').count(), 1);
  await search.fill('company-that-is-not-covered');
  await page.getByText('No matching company in your sidebar.', { exact: true }).waitFor();
  await search.fill('');
  await page.getByRole('tab', { name: 'Fundamentals', exact: true }).click();
  await page.getByRole('tab', { name: 'Fundamentals', exact: true }).press('ArrowRight');
  assert.equal(await page.getByRole('tab', { name: 'Expectations', exact: true }).getAttribute('aria-selected'), 'true');
  await page.getByRole('tab', { name: 'Evidence radar', exact: true }).click();
  await page.locator('.brief-citations .source-link').first().click();
  await page.getByRole('dialog', { name: 'Source evidence' }).waitFor();
  await page.keyboard.press('Escape');
  assert.equal(await page.getByRole('dialog').count(), 0);
  // Navigation resets the research scroll while preserving the shared shell.
  for (const view of ['My ideas', 'Updates', 'History', 'Workspace']) {
    await page.getByRole('navigation', { name: 'Workspace navigation' }).getByRole('button', { name: view, exact: true }).click();
    await main.waitFor();
    assert.equal(await main.evaluate(e => e.scrollTop), 0);
    const g = await geometry();
    assert.ok(g.pageWidth <= 1920 && g.pageHeight <= 1081, `view frame ${view}`);
    assert.ok(g.mainWidth <= g.mainClient + 1, `view overflow ${view}`);
    if (view === 'Updates') await page.screenshot({ path: path.join(process.env.THESIS_LAYOUT_SCREENSHOTS || os.tmpdir(), 'thesis-layout-inbox.png') });
  }
  // Watch-only controls are absent while stopped; inspecting visible options is read-only.
  if (await sentiment.getByRole('checkbox', {name:'Watch news + social changes',exact:true}).isChecked()) {
    await sentiment.locator('.watch-options > summary').click();
    await sentiment.getByText('Original reply context · off', { exact: true }).waitFor();
    await sentiment.locator('.private-check-options > summary').click();
    await sentiment.getByLabel('Private check focus').selectOption('question');
    assert.equal(await sentiment.getByLabel('Private check focus').inputValue(), 'question');
  } else {
    assert.equal(await sentiment.locator('.watch-options').count(),0);
    assert.equal(await sentiment.locator('.private-check-options').count(),0);
  }
  await sentiment.locator('.sample-method > summary').click();
  await sentiment.getByText('News framing and expressed social opinions are separate samples.', { exact: false }).waitFor();
  const warnings = sentiment.locator('.coverage-notice > summary');
  if (await warnings.count()) {
    await warnings.click();
    await sentiment.getByText(/Saved with an earlier analysis method/).waitFor();
  }
  for (const width of [740,390,320]) {
    await page.setViewportSize({ width, height: 900 });
    await page.evaluate(() => window.scrollTo(0, 0));
    const g = await geometry();
    assert.ok(g.pageWidth <= width, `mobile overflow ${width}`);
    assert.ok(g.mainWidth <= g.mainClient + 1, `mobile main overflow ${width}`);
    assert.equal(g.watch.width, 0);
    await page.getByRole('combobox', { name: 'Company', exact: true }).waitFor({ state: 'visible' });
    await page.evaluate(() => window.scrollTo(0, 700));
    assert.equal((await geometry()).header.y, 0, `mobile header ${width}`);
    await page.screenshot({ path: path.join(process.env.THESIS_LAYOUT_SCREENSHOTS || os.tmpdir(), `thesis-layout-${width}.png`) });
    checked.push(`${width}x900`);
  }
  assert.deepEqual(errors, []);
  assert.deepEqual(writes, []);
  assert.deepEqual(external, []);
  console.log(JSON.stringify({ passed: true, viewports: checked, navigation: 4, sourceDialog: true, keyboardScroll: true, sourceOrModelRequests: 0 }));
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => { await browser?.close(); });
