const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
let browser;
(async () => {
  browser = await chromium.launch({ headless: true, ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}) });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [], external = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('request', r => { if (!r.url().startsWith(process.env.THESIS_TEST_URL)) external.push(r.url()); });
  let profileReady = false;
  await page.route('**/api/v1/workspace*', async route => {
    const response = await route.fetch(); const body = await response.json();
    if (!profileReady) body.result.performance = { status: 'empty', reason: 'Refresh filings to prepare annual and quarterly financials.', reports: {} };
    await route.fulfill({ response, json: body });
  });
  await page.goto(process.env.THESIS_TEST_URL);
  await page.locator('.watch-item').filter({ hasText: 'MSFT' }).click();
  await page.getByRole('tab', { name: 'Fundamentals', exact: true }).click();
  const panel = page.getByRole('region', { name: 'Financial performance', exact: true });
  await panel.getByText('Refresh filings to prepare annual and quarterly financials.', { exact: true }).waitFor();
  profileReady = true;
  await Promise.all([page.waitForResponse(r => r.url().includes('/api/v1/workspace')), page.evaluate(() => window.dispatchEvent(new Event('focus')))]);
  await panel.getByText('How is the business doing?', { exact: true }).waitFor();
  await page.unroute('**/api/v1/workspace*');
  assert.equal(await panel.getByRole('button', { name: 'Annual financials' }).getAttribute('aria-pressed'), 'true');
  await panel.getByRole('button', { name: 'Latest quarter', exact: true }).click();
  const cash = panel.locator('details').filter({ has: page.locator('summary').filter({ hasText: 'Operating cash flow' }) });
  await cash.locator('summary').click();
  assert.match(await cash.innerText(), /1 Jan 2025 – 30 Sept 2025/);
  assert.match(await cash.innerText(), /NetCashProvidedByUsedInOperatingActivities/);
  const fcf = panel.locator('details').filter({ has: page.locator('summary').filter({ hasText: 'Free cash flow' }) });
  await fcf.locator('summary').click();
  assert.match(await fcf.innerText(), /Non-GAAP/);
  assert.match(await fcf.innerText(), /Exact calculated value: 55 USD/);
  assert.match(await fcf.getByRole('link').getAttribute('href'), /000078901925000002/);
  assert.match(await panel.innerText(), /Net income[\s\S]*Unavailable/);
  assert.match(await panel.innerText(), /Commercial paper[\s\S]*USD 0/);
  await page.screenshot({ path: '/private/tmp/thesis-performance-1440.png', fullPage: true });
  for (const width of [320, 390, 768]) {
    await page.setViewportSize({ width, height: 960 });
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `Financial view overflow ${width}`);
  }
  await page.setViewportSize({ width: 390, height: 900 });
  await panel.getByRole('button', { name: 'Annual financials' }).click();
  assert.match(await panel.innerText(), /USD 500/);
  await page.screenshot({ path: '/private/tmp/thesis-performance-390.png', fullPage: true });
  // New source states are visible; old values are not rendered after withdrawal.
  await page.route('**/api/v1/workspace*', async route => {
    const response = await route.fetch(); const body = await response.json();
    body.result.performance = { status: 'unavailable', reason: 'Structured filing source access is unavailable.', reports: {} };
    await route.fulfill({ response, json: body });
  });
  await page.reload();
  await page.getByRole('tab', { name: 'Fundamentals', exact: true }).click();
  await panel.getByText('Structured filing source access is unavailable.', { exact: true }).waitFor();
  assert.equal(await panel.locator('.financial-metric').count(), 0);
  assert.deepEqual(errors, []); assert.deepEqual(external, []);
  console.log('Financial performance browser passed: independent views, YTD labels, source/formula evidence, missing versus zero, withdrawal and 320/390/768/1440 layouts; no external/model requests.');
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => { await browser?.close(); });
