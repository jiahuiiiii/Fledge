// Navigation and drafting over authored, disposable company research.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs"),
  path = require("node:path");
let browser, page;
(async () => {
  const base = process.env.THESIS_TEST_URL;
  const iid = "c767e09f-35ea-5eaf-a626-ff5d3aa4709b";
  const folder =
    process.env.THESIS_COMPANION_EVIDENCE || "/private/tmp/thesis-companion";
  fs.mkdirSync(folder, { recursive: true });
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_PATH,
  });
  page = await browser.newPage({
    viewport: { width: 1440, height: 1050 },
    reducedMotion: "reduce",
  });
  const errors = [],
    writes = [],
    external = [];
  let withheld = false,
    saved = null,
    empty = false;
  page.on("pageerror", (error) => {
    errors.push(error.message);
    console.error("Browser error:", error.message);
  });
  await page.route("**/*", async (route) => {
    const request = route.request(),
      url = new URL(request.url());
    if (
      url.hostname === "financialmodelingprep.com" &&
      request.resourceType() === "image"
    )
      return route.fulfill({ status: 404, body: "Authored missing logo" });
    if (url.origin !== new URL(base).origin) {
      external.push(request.url());
      return route.abort();
    }
    if (url.pathname.endsWith("/loading"))
      return route.fulfill({ json: { result: { active: false, steps: [] } } });
    if (request.method() !== "GET") {
      writes.push(url.pathname);
      return route.abort();
    }
    if (url.pathname === "/api/v1/workspace") {
      const response = await route.fetch(),
        packet = await response.json();
      packet.result.versions = saved ? [saved] : [];
      packet.result.idea_alerts = [];
      packet.result.question_library = {
        items: [],
        selected_question: "My original question?",
      };
      if (empty) {
        packet.result.catalogue = [];
        packet.result.empty = true;
      }
      return route.fulfill({ response, json: packet });
    }
    if (url.pathname.endsWith("/business") && withheld) {
      const response = await route.fetch(),
        packet = await response.json();
      for (const reading of [
        packet.result.current,
        packet.result.latest,
        ...(packet.result.items || []),
      ])
        if (reading) reading.withheld = true;
      return route.fulfill({ response, json: packet });
    }
    return route.continue();
  });
  await page.goto(`${base}/?company=${iid}&view=workspace`);
  const start = page.getByRole("button", {
    name: "Start with a question",
    exact: true,
  });
  const guide = page.getByRole("dialog", {
    name: "Start with a question",
    exact: true,
  });
  const entry = page.getByRole("button", {
    name: "Ask a question",
    exact: true,
  });
  async function openGuide() {
    if (!(await start.isVisible())) await entry.click();
    await start.click();
    await guide.waitFor();
  }
  const prompt = page.getByRole("complementary", {
    name: "Your starting question",
  });
  await entry.waitFor();
  await entry.click();
  await start.waitFor();
  const before = (
    await (
      await page.request.get(`${base}/api/v1/workspace?instrument_id=${iid}`)
    ).json()
  ).result;
  await start.focus();
  await page.keyboard.press("Enter");
  await guide.waitFor();
  assert.equal(await guide.locator(".companion-questions > button").count(), 4);
  await page.keyboard.press("Escape");
  assert.equal(
    await start.evaluate((el) => document.activeElement === el),
    true,
  );
  await page.keyboard.press("Escape");
  for (const title of ["Revenue growth", "Operating margin", "Revenue"]) {
    const control = page
      .getByRole("button", { name: `Explain ${title}`, exact: true })
      .first();
    await control.click();
    await page.getByRole("dialog", { name: title, exact: true }).waitFor();
    await page.keyboard.press("Escape");
    assert.equal(
      await control.evaluate((el) => document.activeElement === el),
      true,
    );
  }
  // Responsive, keyboard-accessible choice panel, without a compulsory wizard.
  for (const width of [1440, 980, 390, 320]) {
    await page.setViewportSize({ width, height: width < 600 ? 812 : 1050 });
    await openGuide();
    await guide.waitFor();
    const bounds = await guide.boundingBox();
    assert.ok(bounds.x >= 0 && bounds.x + bounds.width <= width + 1);
    assert.ok(await guide.evaluate((el) => el.scrollWidth <= el.clientWidth));
    for (const choice of await guide
      .locator(".companion-questions > button")
      .all())
      assert.ok((await choice.boundingBox()).height >= 44);
    await page.screenshot({
      path: path.join(folder, `guide-${width}.png`),
      animations: "disabled",
    });
    await page.keyboard.press("Escape");
  }
  await page.setViewportSize({ width: 1440, height: 1050 });
  async function choose(question) {
    await openGuide();
    await guide.getByRole("button", { name: new RegExp(question) }).click();
    await prompt.waitFor();
  }
  await choose("How does this company make money");
  const business = page.getByRole("region", {
    name: "Understand the business",
    exact: true,
  });
  const revenue = business.locator('[data-topic="revenue_model"]');
  await revenue
    .getByText(
      "The company says it sells subscription software to business customers.",
      { exact: true },
    )
    .waitFor();
  await page.waitForFunction(
    () => document.activeElement?.textContent === "How it makes money",
  );
  await revenue
    .getByRole("button", { name: "View source", exact: true })
    .click();
  await page
    .getByRole("dialog", { name: "Original evidence", exact: true })
    .waitFor();
  await page.keyboard.press("Escape");
  await choose("What could go wrong");
  await page.waitForFunction(
    () => document.activeElement?.textContent === "Key risks",
  );
  assert.match(
    await business.locator('[data-topic="risks"]').innerText(),
    /Not covered/,
  );
  // A starter is a reading prompt; it never silently replaces a library selection.
  await prompt
    .getByRole("button", { name: "Save my reasoning", exact: true })
    .click();
  const editor = page.getByRole("dialog", {
    name: "Save your reasoning",
    exact: true,
  });
  await editor.waitFor();
  assert.equal(
    await editor
      .getByRole("textbox", { name: "Research question", exact: true })
      .inputValue(),
    "What could go wrong?",
  );
  assert.equal(
    await editor
      .getByRole("textbox", { name: "My reasoning", exact: true })
      .inputValue(),
    "",
  );
  await editor
    .getByRole("textbox", { name: "My reasoning", exact: true })
    .fill("I am unsure about customer concentration. <literal text>");
  assert.match(
    await editor.innerText(),
    /save a draft without a monitoring rule/,
  );
  await page.keyboard.press("Escape");
  await choose("Is it growing");
  assert.equal(
    await page
      .getByRole("tab", { name: "Financials", exact: true })
      .getAttribute("aria-selected"),
    "true",
  );
  await page
    .getByRole("region", {
      name: "Earnings and cash-flow history",
      exact: true,
    })
    .waitFor();
  const cashHelp = page
    .getByRole("button", { name: "Explain Free cash flow", exact: true })
    .first();
  await cashHelp.click();
  const term = page.getByRole("dialog", {
    name: "Free cash flow",
    exact: true,
  });
  await term.waitFor();
  assert.match(await term.innerText(), /minus cash capital spending/);
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 812 });
    assert.ok(await term.evaluate((el) => el.scrollWidth <= el.clientWidth));
    await page.screenshot({
      path: path.join(folder, `term-${width}.png`),
      animations: "disabled",
    });
  }
  await page.keyboard.press("Escape");
  assert.equal(
    await cashHelp.evaluate((el) => document.activeElement === el),
    true,
  );
  assert.ok((await cashHelp.boundingBox()).height >= 44);
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );
  await prompt.scrollIntoViewIfNeeded();
  await page.screenshot({
    path: path.join(folder, "prompt-320.png"),
    animations: "disabled",
  });
  await choose("What do analysts and management expect");
  assert.equal(
    await page
      .getByRole("tab", { name: "Outlook", exact: true })
      .getAttribute("aria-selected"),
    "true",
  );
  // Custom questions retain their original explicit save/answer flow.
  await openGuide();
  await guide
    .getByRole("button", { name: "Ask my own question", exact: true })
    .click();
  const notebook = page.getByRole("dialog").filter({
    has: page.getByRole("region", {
      name: "Question-focused research",
      exact: true,
    }),
  });
  await notebook.waitFor();
  assert.match(await notebook.innerText(), /Research question/);
  await page.keyboard.press("Escape");
  await prompt
    .getByRole("button", { name: "Close guide", exact: true })
    .click();
  assert.equal(await prompt.count(), 0);
  // Existing private reasoning must survive using any starter.
  saved = {
    id: "authored-idea",
    revision: 2,
    status: "draft",
    question: "My saved question?",
    reasoning: "My exact original reasoning <unchanged>.",
    conditions: [],
    events: [],
    evaluations: [],
    evidence_reviews: [],
    event_reviews: [],
  };
  await page.reload();
  await entry.waitFor();
  await choose("What could go wrong");
  await prompt
    .getByRole("button", { name: "Save my reasoning", exact: true })
    .click();
  const edit = page.getByRole("dialog", {
    name: "Edit your idea",
    exact: true,
  });
  await edit.waitFor();
  assert.equal(
    await edit
      .getByRole("textbox", { name: "Research question", exact: true })
      .inputValue(),
    saved.question,
  );
  assert.equal(
    await edit
      .getByRole("textbox", { name: "My reasoning", exact: true })
      .inputValue(),
    saved.reasoning,
  );
  await page.keyboard.press("Escape");
  // Missing/restricted research stays missing even with retained raw result fields.
  withheld = true;
  await page.reload();
  await entry.waitFor();
  await choose("How does this company make money");
  await business
    .getByText("Source access changed. This saved explanation is withheld.", {
      exact: true,
    })
    .waitFor();
  assert.equal(
    await business
      .getByText(
        "The company says it sells subscription software to business customers.",
        { exact: true },
      )
      .count(),
    0,
  );
  assert.equal(
    await business.locator('[data-topic="revenue_model"]').count(),
    0,
  );
  // Company navigation clears the reading prompt; it cannot leak into the next company.
  await page.evaluate(() => {
    history.replaceState(null, "", "?company=&view=workspace");
    dispatchEvent(new PopStateEvent("popstate"));
  });
  await page.getByRole("heading", { name: /All companies/ }).waitFor();
  assert.equal(await prompt.count(), 0);
  saved = null;
  const recorded = before.catalogue.find((item) => item.mode === "recorded");
  if (recorded) {
    await page.goto(`${base}/?company=${recorded.id}&view=workspace`);
    await openGuide();
    await guide.waitFor();
    assert.equal(
      await guide.locator(".companion-questions > button").count(),
      3,
    );
    assert.match(await guide.innerText(), /Fictional scenario/);
    await page.keyboard.press("Escape");
  }
  empty = true;
  await page.goto(base);
  await page
    .getByRole("button", { name: "Add your first company", exact: false })
    .waitFor();
  assert.match(await page.locator("main").innerText(), /keep your reasoning/);
  assert.match(await page.locator("main").innerText(), /don’t need a position/);
  const after = (
    await (
      await page.request.get(`${base}/api/v1/workspace?instrument_id=${iid}`)
    ).json()
  ).result;
  for (const key of ["versions", "question_library", "news_watch"])
    assert.deepEqual(after[key], before[key]);
  assert.deepEqual(writes, []);
  assert.deepEqual(external, []);
  assert.deepEqual(errors, []);
  fs.writeFileSync(
    path.join(folder, "result.json"),
    JSON.stringify(
      { passed: true, widths: [1440, 980, 390, 320], writes, external, errors },
      null,
      2,
    ),
  );
  await page.waitForFunction(
    () => !document.querySelector('.company-overview-grid[aria-busy="true"]'),
  );
  await browser.close();
  browser = null;
  console.log(
    "Companion passed: four routes, exact focus/source, missing and withheld data, unsaved/cancelled and existing drafts, term explanations, no implicit writes, responsive layouts.",
  );
})().catch(async (error) => {
  console.error(error);
  if (page)
    console.error(
      "Page at failure:",
      await page
        .locator("body")
        .innerText()
        .catch(() => "unavailable"),
    );
  if (browser) await browser.close();
  process.exitCode = 1;
});
