// Pro UI cleanup: flat Updates evidence, weekly review modal, Overview, News,
// Financials trend tiles and the Compare & value combobox. Authored mocks stand
// in for the inbox and weekly-review endpoints; nothing external is called.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const assert = require("node:assert/strict");
let browser;
(async () => {
  browser = await chromium.launch({
    headless: true,
    ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}),
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 }, reducedMotion: "reduce" });
  const errors = [], external = [], writes = [], rated = [];
  global.__errors = errors;
  page.on("pageerror", (e) => errors.push(e.message));
  const source = {
    id: "s1", kind: "news", title: "Example Co expands", source: "Example Wire", url: "https://example.test/story",
    body: "Example Co announced an expansion into two new markets.", published_at: "2026-10-24T10:00:00Z",
  };
  const company = {
    kind: "company", id: "a1", title: "Tone changed", created_at: "2026-10-24T11:00:00Z", review_action: null,
    feedback_enabled: true, feedback: null,
    detail: {
      id: "a1", symbol: "MSFT", instrument_id: "c767e09f-35ea-5eaf-a626-ff5d3aa4709b", published: true, sources: [source],
      payload: { title: "Tone changed", reason: "More positive.", items: [{ source_id: "s1", citations: [{ source_id: "s1", quote: "announced an expansion" }] }] },
      model: "test-model", prompt_version: "p1", created_at: "2026-10-24T11:00:00Z",
    },
  };
  const review = {
    result: {
      records: [company], total: 1, page: 0, page_size: 20, cutoff: "2026-10-25T00:00:00Z", review: "pending", instrument_id: "",
      companies: [], daily_reports_enabled: false,
    },
  };
  const weeklyItems = [{ id: "w1", scheduled_at: "2026-10-19T00:00:00Z", total: 2, seen_at: null, skipped_occurrences: 0 }];
  const settings = { enabled: true, weekday: 0, minute_of_day: 420, time_zone: "Asia/Singapore", next_due_at: "2026-10-26T00:00:00Z" };
  await page.route("**/*", (route) => {
    const request = route.request(), url = request.url();
    if (url.startsWith(process.env.THESIS_TEST_URL)) {
      const path = new URL(url).pathname;
      if (request.method() === "POST" && path.endsWith("/rating")) { rated.push(request.postData()); return route.fulfill({ json: { result: { value: "useful" } } }); }
      if (path.endsWith("/loading")) return route.fulfill({ json: { result: null } });
      if (request.method() !== "GET") { writes.push(path); return route.fulfill({ status: 403, json: { result: { error: "blocked" } } }); }
      if (path === "/api/v1/telegram") return route.fulfill({ json: { result: { configured: true, linked: false, enabled: false } } });
      if (path === "/api/v1/research-review") return route.fulfill({ json: review });
      if (path === "/api/v1/scheduled-reviews") return route.fulfill({ json: { result: { settings, items: weeklyItems, next_before: null } } });
      if (path === "/api/v1/scheduled-reviews/w1")
        return route.fulfill({
          json: { result: { total: 2, page: 0, page_size: 20, records: [
            company,
            { kind: "move", id: "m1", title: "MSFT rose 4%", created_at: "2026-10-23T10:00:00Z", detail: { symbol: "MSFT", instrument_id: "x" } },
          ] } },
        });
      if (path.endsWith("/loading")) return route.fulfill({ json: { result: null } });
      return route.continue();
    }
    if (url.startsWith("https://financialmodelingprep.com/image-stock/")) return route.fulfill({ status: 404, body: "" });
    external.push(url);
    return route.abort();
  });
  const base = process.env.THESIS_TEST_URL;
  const shot = (name) => process.env.THESIS_SHOTS && page.screenshot({ path: `${process.env.THESIS_SHOTS}/${name}.png`, animations: "disabled" });
  async function open(url) {
    await page.goto(url);
    const skip = page.getByRole("button", { name: /Skip, show me the app/ });
    if (await skip.waitFor({ timeout: 3000 }).then(() => true, () => false)) await skip.click();
  }

  // ---- Updates: flat evidence + weekly review modal
  await open(base + "/?view=updates");
  const inbox = page.getByRole("region", { name: "Research update inbox", exact: true });
  await inbox.getByRole("heading", { name: "Example Co expands" }).waitFor();
  assert.equal(await inbox.locator("details.inbox-record").count(), 0, "records are cards, not nested disclosures");
  await inbox.getByRole("button", { name: "Inspect evidence" }).click();
  const dialog = page.locator("dialog[open]");
  await dialog.getByText("Example Co expands").waitFor();
  assert.equal(await dialog.locator('a[href="https://example.test/story"]').count(), 1);
  assert.match(await dialog.innerText(), /announced an expansion/);
  await shot("updates-evidence");
  assert.equal(await dialog.getByRole("button", { name: "Useful", exact: true }).isVisible(), true);
  assert.equal(await dialog.getByRole("button", { name: "Not useful" }).isVisible(), true);
  assert.equal(await dialog.locator("details:not(.ui-evidence__details)").count(), 0, "no nested disclosures in the evidence dialog");
  assert.equal(await dialog.locator(".ui-evidence__details").evaluate((el) => el.open), false, "provenance stays closed");
  await dialog.getByRole("button", { name: "Useful", exact: true }).click();
  await page.waitForFunction(() => document.querySelector("dialog[open] [aria-pressed=true]"));
  assert.equal(rated.length, 1);
  await page.keyboard.press("Escape");
  await inbox.getByRole("button", { name: /^Weekly review/ }).click();
  const weekly = page.locator("dialog[open]");
  await weekly.getByLabel("Weekly review day").waitFor({ state: "attached" });
  await weekly.getByText("Week ending").waitFor();
  assert.match(await weekly.innerText(), /Good news|Other updates|News/);
  assert.match(await weekly.innerText(), /Price moves/);
  await shot("weekly-review");
  assert.equal(await weekly.locator("details").count(), 0, "weekly review has no collapses");
  assert.ok((await page.evaluate(() => document.documentElement.scrollWidth)) <= 1440);
  await page.keyboard.press("Escape");

  // ---- Company tabs (Pro)
  await open(base);
  await page.locator(".watch-item").filter({ hasText: "MSFT" }).click();
  const pro = page.getByRole("button", { name: "Turn on Pro tools" });
  if (await pro.waitFor({ timeout: 8000 }).then(() => true, () => false)) await pro.click();
  await page.getByRole("tab", { name: "Overview", exact: true }).waitFor();
  assert.deepEqual(await page.getByRole("tab").allInnerTexts(), ["Overview", "News & discussion", "Financials", "Compare & value"]);
  const main = page.getByRole("tabpanel");
  await main.getByRole("heading", { name: "The business" }).waitFor();
  // Overview shows the same News / People online cards as Beginner, with the world card right after.
  assert.equal(await main.getByRole("heading", { name: "What's being said" }).count(), 1);
  assert.equal(await main.locator("#bs-news, #bs-people, #bs-world").count(), 3);
  assert.equal(await main.getByRole("button", { name: "View evidence" }).count(), 0);
  assert.equal(await main.getByText("The business in four reads").count(), 0);
  assert.equal(await main.getByRole("group", { name: "Business topic" }).getByRole("button").count(), 4);
  assert.equal(await main.locator("details[open]").count(), 0, "everything optional starts closed on Overview");

  await page.getByRole("tab", { name: "News & discussion", exact: true }).click();
  const news = page.getByRole("tabpanel");
  await news.getByRole("heading", { name: /What’s the tone/ }).waitFor();
  for (const gone of ["Expectations reported in the news", "More headlines", "Read saved sources again", "Read analysed sources"])
    assert.equal(await news.getByText(gone).count(), 0, gone);
  assert.equal(await news.getByText(/newest first in All/).count(), 0);
  await shot("news");

  // Turning a watch on asks to connect Telegram first when no chat is linked.
  await news.getByRole("button", { name: /^Watch/ }).first().click();
  await page.getByRole("dialog", { name: "News & discussion · watch" }).getByLabel(/Watch news \+ social changes/).click();
  const ask = page.getByRole("dialog", { name: "Connect Telegram first" });
  await ask.waitFor();
  assert.equal(await ask.getByRole("button", { name: "Connect Telegram", exact: true }).isVisible(), true);
  assert.equal(await ask.getByRole("button", { name: "Turn on without Telegram" }).isVisible(), true);
  await ask.getByRole("button", { name: "Cancel" }).click();
  await page.keyboard.press("Escape");
  await page.getByRole("tab", { name: "Financials", exact: true }).click();
  const fin = page.getByRole("tabpanel");
  const tiles = fin.getByRole("group", { name: "Financial trends" }).locator(".ui-trend-tile");
  await tiles.first().waitFor();
  assert.equal(await tiles.count(), 3);
  assert.equal(await fin.getByText("View all figures").count(), 0);
  assert.equal(await fin.locator(".financial-more-detail").count(), 0);
  await shot("financials");
  await tiles.first().click();
  const figure = page.locator("dialog[open]");
  await figure.getByText(/Revenue growth/).first().waitFor();
  assert.equal(await figure.locator("details:not(.ui-evidence__details)").count(), 0);
  await page.keyboard.press("Escape");

  await page.getByRole("tab", { name: "Compare & value", exact: true }).click();
  const compare = page.getByRole("tabpanel");
  const peer = compare.getByRole("combobox", { name: "Peer ticker or company" });
  await peer.waitFor();
  assert.equal(await compare.getByText("Other comparison measures").count(), 0);
  const before = await compare.locator(".position-group").boundingBox();
  await peer.fill("zzzz");
  await page.waitForTimeout(600);
  const after = await compare.locator(".position-group").boundingBox();
  assert.equal(Math.round(after.height), Math.round(before.height), "typing a peer never resizes its card");

  assert.deepEqual(errors, []);
  assert.deepEqual(external, []);
  assert.deepEqual(writes, []);
  console.log(JSON.stringify({ proCleanup: true }));
  await browser.close();
})().catch(async (e) => {
  console.error(e);
  try {
    const page = browser?.contexts()[0]?.pages()[0];
    console.error("PAGE ERRORS", global.__errors, "\n", (await page?.locator("body").innerText())?.slice(0, 600));
  } catch {}
  await browser?.close();
  process.exit(1);
});
