const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
let browser, page;

(async () => {
  browser = await chromium.launch({headless: true, executablePath: process.env.CHROMIUM_PATH});
  page = await browser.newPage({viewport: {width: 1440, height: 1000}, reducedMotion: 'reduce'});
  const errors = [], external = [], modelRequests = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('request', r => {
    if (/\/(brief|evidence-review)$/.test(new URL(r.url()).pathname)) modelRequests.push(r.url());
  });
  await page.route('**/*', route => {
    const url = new URL(route.request().url());
    if (!['127.0.0.1', 'localhost'].includes(url.hostname)) {
      external.push(route.request().url());
      return route.abort();
    }
    return route.continue();
  });
  await page.goto(process.env.THESIS_TEST_URL);
  await page.getByRole('heading', {name: 'Microsoft', exact: true}).waitFor();
  await page.getByRole('heading', {name: 'Microsoft denies the reported contract', exact: true}).waitFor();
  const state = (await (await page.request.get(process.env.THESIS_TEST_URL + '/api/v1/workspace?instrument_id=' + new URL(page.url()).searchParams.get('company'))).json()).result;
  const version = state.versions[0];
  assert.equal(version.evaluations.length, 2);
  const [latest, original] = version.evaluations;
  assert.equal(latest.outcome, 'met');
  assert.equal(original.outcome, 'met');
  assert.deepEqual(latest.results.map(r => [r.metric, r.observed_value, r.outcome]), original.results.map(r => [r.metric, r.observed_value, r.outcome]));

  const tabs = page.getByRole('tablist', {name: 'Research views', exact: true});
  await tabs.getByRole('tab', {name: 'Evidence radar', exact: true}).focus();
  await page.keyboard.press('ArrowRight');
  assert.equal(await tabs.getByRole('tab', {name: 'Fundamentals', exact: true}).getAttribute('aria-selected'), 'true');
  assert.equal(await tabs.getByRole('tab', {name: 'Fundamentals', exact: true}).evaluate(el => el === document.activeElement), true);
  await page.getByRole('tabpanel', {name: 'Fundamentals', exact: true}).waitFor();
  await page.keyboard.press('ArrowLeft');
  assert.equal(await tabs.getByRole('tab', {name: 'Evidence radar', exact: true}).getAttribute('aria-selected'), 'true');
  await page.keyboard.press('End');
  assert.equal(await tabs.getByRole('tab', {name: 'Source coverage', exact: true}).getAttribute('aria-selected'), 'true');
  await page.keyboard.press('Home');
  assert.equal(await tabs.locator('[tabindex="0"]').count(), 1);
  await page.getByRole('tabpanel', {name: 'Evidence radar', exact: true}).waitFor();

  // Native classification filter does not turn an absent label into "no risk".
  const briefing = page.getByRole('region', {name: 'Company news and briefing'});
  const briefingView = page.getByRole('combobox', {name: 'Briefing view', exact: true});
  await briefingView.selectOption('reported');
  assert.equal(await briefing.locator('.market-point').count(), 1);
  await briefingView.selectOption('interpretation');
  assert.equal(await briefing.locator('.market-point').count(), 0);
  assert.match(await briefing.innerText(), /does not establish that no risks or uncertainty exist/);
  await briefingView.selectOption('uncertainty');
  assert.equal(await briefing.locator('.market-point').count(), 1);
  await briefingView.selectOption('all');
  assert.equal(await briefing.locator('.market-point').count(), 2);
  await page.getByLabel('YOUR RESEARCH QUESTION', {exact: true}).selectOption('What could weaken the growth story?');
  assert.match(await briefing.innerText(), /Reading focus:.*challenge growth/s);
  assert.match(await briefing.innerText(), /shared company briefing stays the same/);

  // Updates open their immutable record and foreground the actual new version.
  await page.getByRole('button', {name: 'Updates', exact: true}).click();
  await page.locator('.change-summary').filter({hasText: 'New source evidence to review'}).click();
  const main = page.getByRole('main');
  const evidence = main.getByRole('region', {name: 'Evidence and saved reasoning'});
  await evidence.getByRole('heading', {name: 'What changed in the evidence', exact: true}).waitFor();
  const recordLabels = await page.getByLabel('Record', {exact: true}).locator('option').allTextContents();
  assert.equal(new Set(recordLabels).size, recordLabels.length, 'History choices must remain distinguishable when date and outcome match');
  assert.ok(recordLabels.some(label => /Assessment 1 · \d{2}:\d{2}:\d{2} UTC/.test(label)));
  assert.ok(recordLabels.some(label => /Assessment 2 · \d{2}:\d{2}:\d{2} UTC/.test(label)));
  assert.equal(new URL(page.url()).searchParams.get('evaluation'), latest.id);
  assert.match(await main.innerText(), /A proposed enterprise contract could support recurring revenue/);
  assert.match(await evidence.innerText(), /CORRECTED SOURCE/);
  assert.match(await evidence.innerText(), /AI INTERPRETATION · SAVED REVISION 1/);
  assert.match(await evidence.innerText(), /May challenge your reasoning/);
  assert.match(await evidence.innerText(), /growth and margin conditions are unchanged/);
  const omittedPassageMessage = evidence.getByText(/1 source passage containing ellipsis markers was excluded from AI input/);
  await omittedPassageMessage.waitFor();
  assert.equal(await main.getByText('All conditions met', {exact: true}).count(), 1);
  assert.match(await main.innerText(), /These results check your selected figures, not your written reasoning/);
  const correctedCard = evidence.locator('.idea-evidence-source').filter({hasText: 'Synthetic correction: Microsoft denies the proposed contract'}).first();
  assert.match(await correctedCard.innerText(), /Synthetic Wire/);
  assert.match(await correctedCard.innerText(), /Published.*UTC/s);
  assert.match(await correctedCard.innerText(), /Available in this workspace/);

  const inspect = correctedCard.getByRole('button', {name: 'Inspect this source ↗', exact: true});
  await inspect.focus();
  await page.keyboard.press('Enter');
  await page.getByRole('dialog').waitFor();
  assert.match(await page.getByRole('dialog').innerText(), /Microsoft denied the proposed enterprise contract/);
  assert.match(await page.getByRole('dialog').innerText(), /unfinished synthetic description mentions future contract terms\.\.\./);
  await page.keyboard.press('Escape');
  await page.getByRole('dialog').waitFor({state: 'hidden'});
  assert.equal(await inspect.evaluate(el => el === document.activeElement), true, 'Closing source restores keyboard focus');
  await correctedCard.getByRole('button', {name: 'Compare earlier version ↗', exact: true}).click();
  assert.match(await page.getByRole('dialog').innerText(), /company has not confirmed the reported contract/);
  assert.doesNotMatch(await page.getByRole('dialog').innerText(), /Microsoft denied the proposed enterprise contract/);
  await page.keyboard.press('Escape');

  for (const width of [320, 390, 1440]) {
    await page.setViewportSize({width, height: 1000});
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `Evidence review overflow at ${width}`);
    await omittedPassageMessage.scrollIntoViewIfNeeded();
    assert.equal(await omittedPassageMessage.isVisible(), true, `Fragment omission message hidden at ${width}`);
    const bounds = await omittedPassageMessage.boundingBox();
    assert.ok(bounds.x >= 0 && bounds.x + bounds.width <= width, `Fragment omission message clipped at ${width}`);
    if (width !== 320) await page.screenshot({path: `/private/tmp/thesis-idea-review-${width}.png`, fullPage: true});
  }
  await page.reload();
  await evidence.getByRole('heading', {name: 'What changed in the evidence', exact: true}).waitFor();
  assert.match(await evidence.innerText(), /May challenge your reasoning/);
  const linkedReview = version.evidence_reviews.find(r => r.evaluation_id === latest.id);
  await page.getByLabel('Record', {exact: true}).selectOption(`comparison:${linkedReview.id}`);
  await evidence.getByRole('heading', {name: 'Evidence for this saved comparison', exact: true}).waitFor();
  await main.getByRole('button', {name: 'Open the linked numerical assessment ↗', exact: true}).click();
  assert.equal(await page.getByLabel('Record', {exact: true}).inputValue(), latest.id);
  assert.equal(await main.getByText('All conditions met', {exact: true}).count(), 1);

  // An earlier assessment must show the original source and its original interpretation.
  await page.getByLabel('Record', {exact: true}).selectOption(original.id);
  await evidence.getByRole('heading', {name: 'Evidence for this assessment', exact: true}).waitFor();
  assert.match(await evidence.innerText(), /Connection unresolved/);
  assert.match(await evidence.innerText(), /original report is unconfirmed/);
  assert.doesNotMatch(await evidence.innerText(), /Synthetic correction: Microsoft denies/);
  assert.equal(await evidence.getByRole('button', {name: 'Compare earlier version ↗', exact: true}).count(), 0);
  await evidence.locator('.reasoning-review-point button').first().click();
  assert.match(await page.getByRole('dialog').innerText(), /company has not confirmed the reported contract/);
  await page.keyboard.press('Escape');
  await page.reload();
  await evidence.getByText(/original report is unconfirmed/).waitFor();
  assert.equal(new URL(page.url()).searchParams.get('evaluation'), original.id);

  // Open the current idea, then save a qualitative revision without choosing a number.
  await page.getByRole('button', {name: 'My ideas', exact: true}).click();
  await page.locator('.idea-summary').filter({hasText: 'Microsoft'}).click();
  await evidence.getByRole('heading', {name: 'What changed in the evidence', exact: true}).waitFor();
  await main.getByRole('button', {name: 'Edit my idea', exact: true}).click();
  const dialog = page.getByRole('dialog', {name: 'Edit your idea', exact: true});
  await dialog.getByRole('button', {name: 'I cannot define a condition yet', exact: true}).click();
  await dialog.getByLabel('My reasoning', {exact: true}).fill('I need better evidence of recurring demand before defining any numerical threshold.');
  await dialog.getByRole('button', {name: 'Add condition', exact: true}).click();
  const percent = dialog.getByLabel('Percent', {exact: true});
  assert.equal(await percent.inputValue(), '', 'A new condition must not invent a threshold');
  assert.match(await dialog.innerText(), /Latest reported: 30%/);
  assert.match(await dialog.innerText(), /not a suggested threshold/);
  await dialog.getByRole('checkbox').check();
  assert.equal(await dialog.getByRole('button', {name: 'Approve monitoring', exact: true}).isEnabled(), false);
  await percent.fill('15');
  assert.equal(await dialog.getByRole('checkbox').isChecked(), false);
  await dialog.getByRole('checkbox').check();
  assert.equal(await dialog.getByRole('button', {name: 'Approve monitoring', exact: true}).isEnabled(), true);
  await percent.fill('');
  assert.equal(await dialog.getByRole('button', {name: 'Approve monitoring', exact: true}).isEnabled(), false);
  assert.match(await dialog.innerText(), /Blank condition rows are omitted when saving a draft/);
  await dialog.getByRole('button', {name: 'Save draft', exact: true}).click();
  await page.getByRole('status').filter({hasText: 'Draft saved'}).waitFor();
  await page.reload();
  await evidence.getByRole('heading', {name: 'Evidence for your saved idea', exact: true}).waitFor();
  assert.match(await evidence.innerText(), /A draft needs no numerical condition/);
  assert.doesNotMatch(await evidence.innerText(), /May challenge your reasoning/);
  const after = (await (await page.request.get(process.env.THESIS_TEST_URL + '/api/v1/workspace?instrument_id=' + state.instrument.id)).json()).result;
  assert.equal(after.versions[0].status, 'draft');
  assert.deepEqual(after.versions[0].conditions, []);
  assert.deepEqual(after.versions[0].evaluations, []);
  assert.deepEqual(after.versions[0].evidence_reviews, []);
  assert.equal(after.versions[1].evidence_reviews.length, 2);
  for (const width of [320, 390, 1440]) {
    await page.setViewportSize({width, height: 1000});
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `Draft review overflow at ${width}`);
  }

  // Qualitative-only comparisons remain reachable after new evidence, editing
  // and archiving even though this company never had a numerical assessment.
  await page.locator('.watch-item').filter({hasText: 'AURQ'}).click();
  await page.getByRole('heading', {name: 'Aurora Devices', exact: true}).waitFor();
  await page.getByRole('button', {name: 'History', exact: true}).click();
  const aurora = (await (await page.request.get(process.env.THESIS_TEST_URL + '/api/v1/workspace?instrument_id=bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb')).json()).result;
  assert.equal(aurora.versions[0].status, 'archived');
  assert.ok(aurora.versions.every(v => v.evaluations.length === 0));
  const firstVersion = aurora.versions.find(v => v.revision === 1);
  const [secondComparison, firstComparison] = firstVersion.evidence_reviews;
  assert.notEqual(firstComparison.snapshot_id, secondComparison.snapshot_id);
  const revisedComparison = aurora.versions.find(v => v.revision === 2).evidence_reviews[0];
  const historyRecord = page.getByLabel('Record', {exact: true});
  await historyRecord.locator('option').filter({hasText: 'AI comparison'}).first().waitFor({state: 'attached'});
  const qualitativeLabels = await historyRecord.locator('option').allTextContents();
  assert.equal(qualitativeLabels.filter(label => label.includes('AI comparison')).length, 3);
  assert.equal(new Set(qualitativeLabels).size, qualitativeLabels.length);
  await historyRecord.selectOption(`comparison:${firstComparison.id}`);
  await evidence.getByRole('heading', {name: 'Evidence for this saved comparison', exact: true}).waitFor();
  assert.match(await main.innerText(), /Sensor launch interest does not prove recurring customer demand/);
  assert.match(await evidence.innerText(), /First qualitative comparison before the later development/);
  assert.doesNotMatch(await evidence.innerText(), /Second qualitative comparison after/);
  assert.equal(await evidence.getByRole('button', {name: 'Compare with my saved idea', exact: true}).count(), 0);
  assert.equal(await main.locator('.condition-result').count(), 0);
  const originalCitation = firstComparison.points[0].citations[0];
  const originalDocument = aurora.documents.find(d => d.id === originalCitation.source_id);
  await evidence.locator('.reasoning-review-point button').first().click();
  await page.getByRole('dialog').getByText(originalDocument.title, {exact: true}).waitFor();
  assert.ok((await page.getByRole('dialog').innerText()).includes(originalCitation.quote));
  await page.keyboard.press('Escape');
  await page.reload();
  await evidence.getByText(/First qualitative comparison before the later development/).waitFor();
  assert.equal(new URL(page.url()).searchParams.get('evaluation'), `comparison:${firstComparison.id}`);
  await historyRecord.selectOption(`comparison:${secondComparison.id}`);
  await evidence.getByText(/Second qualitative comparison after the later development/).waitFor();
  assert.match(await main.innerText(), /Sensor launch interest does not prove recurring customer demand/);
  await historyRecord.selectOption(`comparison:${revisedComparison.id}`);
  await evidence.getByText(/Comparison of the revised component-supply reasoning/).waitFor();
  assert.match(await main.innerText(), /Component supply must remain reliable/);
  assert.doesNotMatch(await main.innerText(), /Sensor launch interest does not prove recurring customer demand/);
  // A portable record keeps the explicitly selected revision/comparison.
  const downloadPromise = page.waitForEvent('download');
  await main.getByRole('button', {name: 'Download research record', exact: true}).click();
  const download = await downloadPromise;
  assert.match(download.suggestedFilename(), /thesis-.*-r2-.*\.html/);
  const exportPath = '/private/tmp/thesis-export-browser.html';
  await download.saveAs(exportPath);
  const exported = require('node:fs').readFileSync(exportPath, 'utf8');
  assert.match(exported, /Component supply must remain reliable/);
  assert.match(exported, /Comparison of the revised component-supply reasoning/);
  assert.doesNotMatch(exported, /First qualitative comparison before the later development/);
  assert.match(exported, /Private research record/);
  assert.match(exported, /Historical source register/);
  const reportPage = await browser.newPage({viewport: {width: 1440, height: 1000}});
  const reportRequests = [];
  reportPage.on('request', r => { if (r.url().startsWith('http')) reportRequests.push(r.url()); });
  await reportPage.goto('file://' + exportPath);
  await reportPage.getByRole('heading', {name: 'Saved AI interpretation'}).waitFor();
  await reportPage.screenshot({path: '/private/tmp/thesis-export-desktop.png', fullPage: true});
  await reportPage.setViewportSize({width: 390, height: 844});
  assert.ok(await reportPage.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await reportPage.screenshot({path: '/private/tmp/thesis-export-phone.png', fullPage: true});
  assert.deepEqual(reportRequests, [], 'Export is usable offline without external resources');
  await reportPage.close();
  await page.route('**/review-export?*', route => route.fulfill({status: 503, contentType: 'application/json', body: JSON.stringify({result: {errors: [{error_message: 'Synthetic download failure'}]}})}), {times: 1});
  await main.getByRole('button', {name: 'Download research record', exact: true}).click();
  await main.getByRole('alert').getByText('Synthetic download failure', {exact: true}).waitFor();
  assert.equal(await historyRecord.inputValue(), `comparison:${revisedComparison.id}`);
  for (const width of [320, 390, 1440]) {
    await page.setViewportSize({width, height: 1000});
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `Qualitative history overflow at ${width}`);
    if (width !== 320) await page.screenshot({path: `/private/tmp/thesis-qualitative-history-${width}.png`, fullPage: true});
  }
  assert.deepEqual(errors, []);
  assert.deepEqual(external, []);
  assert.deepEqual(modelRequests, [], 'Opening, filtering, historical review and drafts make no model calls');
  console.log('Idea browser passed: exact corrected-source review, original historical interpretation and source, unchanged numeric results, qualitative draft and comparison history across snapshots/revision/archive, blank threshold approval, category filters, keyboard tabs and source/focus restoration, 320/390/1440 layouts; no external or model calls.');
})().catch(async e => {
  console.error(e);
  if (page) console.error((await page.locator('body').innerText()).slice(-12000));
  process.exitCode = 1;
}).finally(async () => { if (browser) await browser.close(); });
