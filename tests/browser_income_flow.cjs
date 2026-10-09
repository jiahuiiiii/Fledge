const assert = require('node:assert/strict');

module.exports = async function checkIncomeFlow(page) {
  const flow = page.locator('.revenue-flow:visible');
  await flow.getByRole('heading', {name:'Revenue & expenses', exact:true}).waitFor();
  const svg = flow.locator('.flow-svg');
  await svg.waitFor();
  assert.equal(await flow.locator('.flow-all-figures').getAttribute('open'),null);
  assert.equal(await svg.locator('.flow-link').count(), 8);
  assert.match(await flow.locator('.flow-meta').innerText(), /1 Oct.*2024.*30 Sep.*2025/s);
  await flow.getByRole('button',{name:'Gross profit: US$40bn. Inspect evidence',exact:true}).focus();
  await page.keyboard.press('Enter');
  const evidence = page.getByRole('dialog',{name:'Gross profit · evidence',exact:true});
  await evidence.waitFor();
  assert.match(await evidence.innerText(), /40000000000 USD/);
  assert.match(await evidence.getByRole('link').first().getAttribute('href'), /^https:\/\/www.sec.gov\/Archives\//);
  await page.keyboard.press('Escape');
  assert.equal(await flow.getByRole('button',{name:'Gross profit: US$40bn. Inspect evidence',exact:true}).evaluate(el=>el===document.activeElement),true);
  await flow.getByLabel('Revenue sources').selectOption({label:'Products and services'});
  assert.match(await svg.textContent(), /Software/);
  await flow.getByRole('button',{name:/2021.*revenue/}).click();
  assert.equal(await svg.count(),0);
  assert.match(await flow.locator('.flow-gap').innerText(), /missing/);
  assert.match(await flow.locator('.flow-figures').innerText(), /US\$27bn/);
  await flow.getByRole('button',{name:/2025.*revenue/}).click();
  await svg.waitFor();
  await flow.locator('.flow-expenses summary').click();
  assert.match(await flow.locator('.flow-expense-list').innerText(), /Remaining operating expenses \*\s*US\$2bn/);
  await flow.locator('.flow-expense-list button').last().click();
  await page.getByRole('dialog').waitFor();
  assert.match(await page.getByRole('dialog').innerText(), /2000000000 USD/);
  assert.match(await page.getByRole('dialog').innerText(), /Operating expenses − Research & development \+ selling, general & administrative/);
  await page.keyboard.press('Escape');
  await flow.locator('.flow-expenses summary').click();
  for (const [width,height] of [[1440,1100],[980,1000],[390,844],[320,740]]) {
    await page.setViewportSize({width,height});
    await flow.scrollIntoViewIfNeeded();
    await flow.locator('.flow-viewport').evaluate(el=>el.scrollLeft=0);
    await page.mouse.move(1,1);
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth), `no page overflow at ${width}`);
    const bounds=await flow.boundingBox();
    assert.ok(bounds.x>=0 && bounds.x+bounds.width<=width);
    assert.ok(await flow.locator('.flow-viewport').evaluate(el=>el.scrollWidth>=el.clientWidth));
    // Fixed application chrome overlaps element screenshots when the card is
    // taller than the viewport. Hide only that chrome for this capture.
    await flow.screenshot({path:`/private/tmp/thesis-income-flow-${width}.png`,animations:'disabled',style:'.topbar, .research-navigation, .research-loading, .company-header { visibility: hidden !important; }'});
    if(width<=390) {
      await flow.locator('.flow-viewport').evaluate(el=>el.scrollLeft=el.scrollWidth);
      await flow.getByRole('button',{name:'Net result including non-controlling interests: US$20bn. Inspect evidence',exact:true}).click();
      const dialog=page.getByRole('dialog');
      await dialog.waitFor();
      assert.match(await dialog.innerText(), /ProfitLoss: 20000000000 USD/);
      assert.ok(await dialog.evaluate(el=>el.scrollWidth<=el.clientWidth));
      await page.keyboard.press('Escape');
    }
  }
  await page.emulateMedia({reducedMotion:'reduce'});
  assert.equal(await flow.locator('.flow-link').first().evaluate(el=>getComputedStyle(el).animationName),'none');
  await page.emulateMedia({reducedMotion:'no-preference'});
  await page.setViewportSize({width:1440,height:1000});
};
