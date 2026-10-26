// Shared interactions with the current workspace; never change application state
// except through the same disclosure controls a reader uses.
async function disclosure(page, title, open = true) {
  const summary = page.locator('summary').filter({ hasText: title }).first();
  await summary.waitFor();
  const details = summary.locator('..');
  if (await details.evaluate(el => el.open) !== open) await summary.click();
  return details;
}
async function financialDetails(page) {
  const result = {};
  for (const [key, title] of Object.entries({
    position: 'Near-term and longer-term obligations',
    debt: 'Borrowing, cash and equity over time',
    balance: 'What makes up the balance sheet',
    readings: 'Reading these figures',
    reports: 'Reported figures and filings',
  })) result[key] = await disclosure(page, title);
  return result;
}
module.exports = { disclosure, financialDetails };
