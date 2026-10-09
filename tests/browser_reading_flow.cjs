// Authored layout/navigation cases over the disposable financials fixture.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const assert = require("node:assert/strict"),
  fs = require("node:fs"),
  path = require("node:path");
let browser;
(async () => {
  const base = process.env.THESIS_TEST_URL,
    iid = "c767e09f-35ea-5eaf-a626-ff5d3aa4709b";
  const folder =
    process.env.THESIS_READING_FLOW_EVIDENCE ||
    "/private/tmp/thesis-reading-flow";
  fs.mkdirSync(folder, { recursive: true });
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_PATH,
  });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1050 },
    reducedMotion: "reduce",
  });
  const errors = [],
    writes = [],
    external = [],
    layouts = [];
  let withheld = false;
  const source = {
    id: "authored-alert-source",
    kind: "news",
    title: "Factory opening moves to September",
    body: "The company moved the opening from June to September after a construction delay.",
    source: "Authored news",
    published_at: "2026-05-02T12:00:00Z",
    url: "https://example.invalid/article",
  };
  const item = {
    id: "item_1",
    source_id: source.id,
    sentiment: "negative",
    statement: "reported_development",
    explanation:
      "AI reading: a favourable or adverse outcome stated in the source.",
    citations: [{ source_id: source.id, quote: source.body }],
  };
  const alert = {
    id: "authored-alert",
    instrument_id: iid,
    symbol: "MSFT",
    name: "Microsoft",
    created_at: "2026-05-03T12:00:00Z",
    review_action: null,
    sources: [source],
    previous_items: [],
    previous_sources: [],
    payload: {
      title: "New adverse or mixed company reporting",
      reason: "An authored source change.",
      items: [item],
      shifts: [],
    },
  };
  page.on("pageerror", (e) => errors.push(e.message));
  await page.route("**/*", async (route) => {
    const r = route.request(),
      u = new URL(r.url());
    if (
      u.hostname === "financialmodelingprep.com" &&
      r.resourceType() === "image"
    )
      return route.fulfill({ status: 404, body: "Authored unavailable logo" });
    if (!r.url().startsWith(base)) {
      external.push(r.url());
      return route.abort();
    }
    if (u.pathname.endsWith("/loading"))
      return route.fulfill({ json: { result: { active: false, steps: [] } } });
    if (r.method() !== "GET") {
      writes.push(u.pathname);
      return route.abort();
    }
    if (u.pathname === "/api/v1/research-review")
      return route.fulfill({
        json: {
          result: {
            instrument_id: u.searchParams.get("instrument_id"),
            review: u.searchParams.get("review"),
            page: 0,
            cutoff: "2026-05-03T12:00:00Z",
            page_size: 20,
            total: 1,
            totals: { pending_count: 1, unresolved_count: 0, new_count: 1 },
            companies: [
              {
                id: iid,
                symbol: "MSFT",
                name: "Microsoft",
                mode: "live",
                coverage: {
                  concerns: [],
                  watch: { enabled: true, interval_minutes: 60 },
                },
              },
            ],
            records: [
              {
                id: alert.id,
                kind: "company",
                created_at: alert.created_at,
                title: alert.payload.title,
                review_action: null,
                detail: { ...alert, withheld },
              },
            ],
          },
        },
      });
    if (u.pathname === "/api/v1/workspace") {
      const response = await route.fetch(),
        packet = await response.json();
      packet.result.versions = [];
      packet.result.idea_alerts = [];
      packet.result.catalogue = packet.result.catalogue.map((c) => ({
        ...c,
        status: null,
        revision: null,
        unread: 0,
      }));
      return route.fulfill({ response, json: packet });
    }
    return route.continue();
  });
  await page.addInitScript(() =>
    localStorage.setItem(
      "thesis.layout",
      JSON.stringify({
        companiesHidden: false,
        ideaHidden: true,
        progressHidden: true,
      }),
    ),
  );
  await page.goto(base + `/?company=${iid}&view=workspace`);
  await page.getByRole("heading", { name: "Overview", exact: true }).waitFor();
  await page.evaluate(() => document.fonts.ready);
  const top = page.getByRole("navigation", { name: "Workspace navigation" });
  const sections = page.getByRole("tablist", { name: "Research views" });
  assert.equal(await sections.getAttribute("aria-orientation"), "horizontal");
  assert.equal(
    await page
      .locator(".research-rail,.rail-research,.my-research-button")
      .count(),
    0,
  );
  assert.equal(
    await page.getByRole("button", { name: "Notebook", exact: true }).count(),
    1,
  );
  await sections.getByRole("tab", { name: "Overview", exact: true }).focus();
  await page.keyboard.press("ArrowRight");
  await page
    .getByRole("region", {
      name: "Earnings and cash-flow history",
      exact: true,
    })
    .waitFor();
  const performance = page.getByRole("region", {
    name: "Earnings and cash-flow history",
    exact: true,
  });
  const chapters = page.getByRole("tablist", {
    name: "Financial sections",
    exact: true,
  });
  assert.equal(
    await page.locator(".financials-story .sector-position").count(),
    0,
  );
  assert.equal(
    await performance
      .getByRole("button", { name: "Evidence", exact: true })
      .count(),
    0,
  );
  assert.equal(
    await performance
      .getByRole("button", { name: "Figures & calculations", exact: true })
      .count(),
    1,
  );
  assert.equal(
    await page.locator("#financial-view-reports").isVisible(),
    false,
  );
  assert.equal(
    await page.locator("#financial-view-position").isVisible(),
    false,
  );
  await performance
    .getByRole("button", { name: "Annual reports", exact: true })
    .click();
  await performance
    .getByRole("button", { name: "Figures & calculations", exact: true })
    .click();
  const evidence = page.getByRole("dialog", {
    name: "Performance · figures & calculations",
    exact: true,
  });
  await evidence.waitFor();
  assert.match(await evidence.innerText(), /64000000000 USD/);
  assert.match(await evidence.innerText(), /52000000000 USD/);
  await page.keyboard.press("Escape");
  await chapters
    .getByRole("tab", { name: "Financial position", exact: true })
    .click();
  await page
    .getByRole("region", { name: "Borrowing and equity history", exact: true })
    .waitFor();
  assert.equal(
    await page.locator("#financial-view-performance").isVisible(),
    false,
  );
  await chapters
    .getByRole("tab", { name: "Financial position", exact: true })
    .press("ArrowRight");
  assert.equal(await page.locator("#financial-view-reports").isVisible(), true);
  await page.getByText("All reported figures", { exact: true }).click();
  await page
    .getByRole("region", { name: "Financial performance", exact: true })
    .waitFor();
  await chapters.getByRole("tab", { name: "Performance", exact: true }).click();
  assert.equal(
    await performance
      .getByRole("button", { name: "Annual reports", exact: true })
      .getAttribute("aria-pressed"),
    "true",
  );
  // Only one entry point; opening and closing keeps the question draft intact.
  await page.getByRole("button", { name: "Notebook", exact: true }).click();
  const notebook = page.getByRole("dialog", { name: "Notebook", exact: true });
  await notebook
    .getByRole("button", { name: "Edit question", exact: true })
    .click();
  await notebook
    .locator("#specific-question")
    .fill("What would change my view of this company?");
  await page.keyboard.press("Escape");
  await sections.getByRole("tab", { name: "Outlook", exact: true }).click();
  await page.getByRole("button", { name: "Notebook", exact: true }).click();
  assert.equal(
    await notebook.locator("#specific-question").inputValue(),
    "What would change my view of this company?",
  );
  await page.keyboard.press("Escape");
  for (const width of [1440, 1920, 980, 390, 320]) {
    await page.setViewportSize({ width, height: width < 600 ? 844 : 1050 });
    await top.getByRole("button", { name: "Workspace", exact: true }).click();
    await sections
      .getByRole("tab", { name: "Financials", exact: true })
      .click();
    await chapters
      .getByRole("tab", { name: "Performance", exact: true })
      .click();
    await page.evaluate(() => {
      document.querySelector(".main-workspace").scrollTop = 0;
      window.scrollTo(0, 0);
    });
    const geometry = await page.locator(".research-content").evaluate((el) => ({
      width: innerWidth,
      content: el.getBoundingClientRect().width,
      page: document.documentElement.scrollWidth,
    }));
    assert.ok(geometry.page <= width, `financial page overflow ${width}`);
    if (width === 1440)
      assert.ok(
        geometry.content > 1050,
        `chart column uses released rail space: ${geometry.content}`,
      );
    layouts.push(geometry);
    await page.screenshot({
      path: path.join(folder, `financials-${width}.png`),
      animations: "disabled",
    });
    const reportEdges = await page.locator(".research-content").boundingBox();
    for (const view of ["My ideas", "History", "Updates"]) {
      await top.getByRole("button", { name: view, exact: true }).click();
      assert.equal(await page.locator(".periodic-review-entry").count(), 0);
      assert.equal(
        await page
          .getByRole("button", { name: "Notebook", exact: true })
          .count(),
        0,
      );
      assert.ok(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
        `${view} overflow ${width}`,
      );
      const frame = await page.locator(".workspace-page").evaluate((el) => ({
        rect: el.getBoundingClientRect().toJSON(),
        padding: parseFloat(getComputedStyle(el).paddingLeft),
      }));
      assert.ok(
        Math.abs(frame.rect.x + frame.padding - reportEdges.x) < 2,
        `${view} left alignment ${width}`,
      );
      assert.ok(
        Math.abs(frame.rect.width - frame.padding * 2 - reportEdges.width) < 2,
        `${view} reading width ${width}`,
      );
      if (view === "History") {
        await page.getByText("No saved history yet", { exact: true }).waitFor();
        assert.equal(await page.locator(".history-empty").count(), 1);
        assert.equal(
          await page.locator(".idea-alert-checks:visible").count(),
          0,
        );
      }
      if (view === "Updates") {
        const card = page.locator(".inbox-record > summary");
        await card.waitFor();
        assert.equal(await card.locator("h3").innerText(), source.title);
        assert.equal(
          await card.locator(".inbox-preview").first().innerText(),
          source.body,
        );
        assert.doesNotMatch(await card.innerText(), /AI reading:/);
        assert.equal(
          await page
            .getByRole("button", { name: "Weekly review", exact: true })
            .count(),
          1,
        );
      }
      await page.evaluate(() => {
        document.querySelector(".main-workspace").scrollTop = 0;
        window.scrollTo(0, 0);
      });
      await page.screenshot({
        path: path.join(
          folder,
          `${view.replaceAll(" ", "-").toLowerCase()}-${width}.png`,
        ),
        animations: "disabled",
      });
    }
  }
  // Opening evidence retains the old classification and the exact source.
  const card = page.locator(".inbox-record > summary");
  await card.focus();
  await page.keyboard.press("Enter");
  assert.match(await page.locator(".inbox-detail").innerText(), /AI reading:/);
  withheld = true;
  await page
    .getByRole("button", { name: "Refresh inbox", exact: true })
    .click();
  await page
    .getByRole("heading", { name: "Source access changed", exact: true })
    .waitFor();
  assert.doesNotMatch(
    await page.locator(".inbox-record").innerText(),
    /Factory opening|construction delay/,
  );
  assert.deepEqual(errors, []);
  assert.deepEqual(writes, []);
  assert.deepEqual(external, []);
  const result = {
    authoredData: true,
    layouts,
    oneNotebookEntry: true,
    retainedQuestionDraft: true,
    horizontalKeyboardNavigation: true,
    threeFinancialChapters: true,
    groupedEvidence: true,
    exactSourcePreview: true,
    withholding: true,
    oneHistoryEmptyState: true,
    weeklyOnlyUpdates: true,
    sharedPageWidth: true,
    errors,
    writes,
    external,
  };
  fs.writeFileSync(
    path.join(folder, "browser.json"),
    JSON.stringify(result, null, 2),
  );
  console.log(JSON.stringify(result));
})()
  .catch((e) => {
    console.error(e);
    process.exitCode = 1;
  })
  .finally(async () => browser?.close());
