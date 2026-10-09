// Read-only owner workspace plus authored four-source, theme and access-state fixtures.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const base = process.env.THESIS_TEST_URL || "http://127.0.0.1:8841";
const evidence =
  process.env.THESIS_FILTERS_EVIDENCE || "/private/tmp/thesis-source-filters";
const labels = {
  all: "All sources",
  news: "Company news",
  reddit: "Reddit discussion",
  hackernews: "Hacker News",
  x: "X / Twitter",
};
const scopeOf = (source) =>
  source.kind === "news" ? "news" : source.platform || "reddit";
const sorted = (sources) =>
  sources
    .filter(
      (source) =>
        !source.comparison_only && ["news", "social"].includes(source.kind),
    )
    .slice()
    .sort(
      (left, right) =>
        Date.parse(right.published_at) - Date.parse(left.published_at) ||
        left.id.localeCompare(right.id),
    );
const fixtureSources = ["news", "reddit", "hackernews", "x"].map(
  (scope, index) => ({
    id: `11112222-3333-4444-8888-${String(index).padStart(12, "0")}`,
    kind: scope === "news" ? "news" : "social",
    platform: scope === "news" || scope === "reddit" ? undefined : scope,
    source: `Authored ${labels[scope]} source`,
    title: `Authored ${scope} selected title`,
    body: `Original authored ${scope} body, preserved verbatim.`,
    published_at: `2026-10-08T${["10", "10", "09", "11"][index]}:00:00Z`,
    available_at: "2026-10-08T12:00:00Z",
    timestamp_basis: scope === "reddit" ? "feed_updated" : undefined,
    url: "https://example.test/authored-" + scope,
  }),
);
const comparison = {
  ...fixtureSources[0],
  id: "11112222-3333-4444-8888-999999999999",
  title: "Comparison-only report excluded",
  comparison_only: true,
  published_at: "2026-10-09T12:00:00Z",
};
const fixtureAnalysis = {
  id: "authored-source-filter-sample",
  created_at: "2026-10-08T12:00:00Z",
  cutoff: "2026-10-08T12:00:00Z",
  social_lookback_days: 7,
  sources: [...fixtureSources, comparison],
  items: fixtureSources.map((source, index) => ({
    id: `item-${index}`,
    source_id: source.id,
    channel: source.kind,
    relevance: index === 2 ? "unrelated" : "relevant",
    sentiment: ["positive", "negative", "neutral", "mixed"][index],
    statement: "opinion",
    explanation: `Authored label explanation for ${source.title}.`,
    citations: [{ quote: source.body }],
  })),
  summary: {
    news: {
      selected: 1,
      relevant: 1,
      tone: "thin sample",
      counts: { positive: 1, negative: 0, mixed: 0, neutral: 0, unclear: 0 },
    },
    social_platforms: Object.fromEntries(
      ["reddit", "hackernews", "x"].map((scope, index) => [
        scope,
        {
          selected: 1,
          relevant: index === 1 ? 0 : 1,
          tone: "thin sample",
          counts: {
            positive: 0,
            negative: index === 0 ? 1 : 0,
            mixed: index === 2 ? 1 : 0,
            neutral: 0,
            unclear: 0,
          },
        },
      ]),
    ),
  },
  coverage: {
    available_news: 3,
    available_social: 9,
    social_platforms: { reddit: 3, hackernews: 3, x: 3 },
    platform_authors: { reddit: 1, hackernews: 1, x: 1 },
    selected_social_authors: 3,
    comparison_news: 1,
    parent_contexts: 0,
  },
  coverage_links: [],
};
const themeReading = {
  id: "authored-theme-reading",
  analysis_id: fixtureAnalysis.id,
  created_at: fixtureAnalysis.created_at,
  cutoff: fixtureAnalysis.cutoff,
  coverage: { by_scope: { news: 1, reddit: 1, hackernews: 1, x: 1 } },
  sources: fixtureSources,
  result: {
    limitation: "Authored saved reading for UI verification.",
    gaps: [],
    themes: fixtureSources.map((source) => ({
      scope: scopeOf(source),
      title: `Authored ${scopeOf(source)} theme`,
      source_count: 1,
      reading: {
        claims: [
          {
            text: source.body,
            source_id: source.id,
            citations: [
              { source_id: source.id, passage_id: "p1", quote: source.body },
            ],
          },
        ],
      },
      unknown: "Unknown beyond this authored source.",
    })),
  },
};
let browser;
(async () => {
  const { sourceHeadline } = await import(
    "../frontend/src/lib/sourceHeadline.js"
  );
  fs.mkdirSync(evidence, { recursive: true });
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_PATH,
  });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1100 },
    reducedMotion: "reduce",
  });
  const errors = [],
    external = [],
    writes = [],
    layouts = [];
  let mode = "actual",
    actual = null,
    mockLoads = 0;
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route("**/*", async (route) => {
    const request = route.request(),
      url = new URL(request.url());
    if (
      url.hostname === "financialmodelingprep.com" &&
      request.resourceType() === "image"
    )
      return route.fulfill({ status: 404, body: "" });
    if (!["127.0.0.1", "localhost"].includes(url.hostname)) {
      external.push(url.hostname);
      return route.abort();
    }
    if (/\/companies\/[^/]+\/loading$/.test(url.pathname)) {
      mockLoads++;
      return route.fulfill({ json: { result: { active: false, steps: [] } } });
    }
    if (request.method() !== "GET") {
      writes.push(url.pathname);
      return route.abort();
    }
    if (
      mode !== "actual" &&
      /\/companies\/[^/]+\/discussion-themes$/.test(url.pathname)
    )
      return route.fulfill({
        json: {
          result: {
            current: themeReading,
            items: [themeReading],
            next_cursor: null,
          },
        },
      });
    if (url.pathname === "/api/v1/workspace") {
      const response = await route.fetch(),
        packet = await response.json();
      if (mode === "actual") actual = packet.result.sentiment;
      else {
        packet.result.sentiment =
          mode === "no-analysis"
            ? null
            : { ...fixtureAnalysis, withheld: mode === "withheld" };
        packet.result.sentiment_inputs = {
          status: mode === "no-analysis" ? "no_saved_reading" : "same",
          sources: fixtureSources,
          as_of: fixtureAnalysis.cutoff,
          scopes: Object.fromEntries(
            ["news", "reddit", "hackernews", "x"].map((scope) => [
              scope,
              {
                selected: 1,
                available: 3,
                added: 0,
                no_longer_selected: 0,
                retained: 1,
              },
            ]),
          ),
        };
      }
      return route.fulfill({ response, json: packet });
    }
    return route.continue();
  });
  await page.goto(base + "/?view=workspace");
  await page
    .locator(".company-row .watch-item")
    .filter({
      has: page.locator(
        `strong[title="${process.env.THESIS_FILTERS_SYMBOL || "AVGO"}"]`,
      ),
    })
    .click();
  await page.locator('.main-workspace[aria-busy="false"]').waitFor();
  const panel = page.getByRole("region", {
    name: "News and social sentiment",
    exact: true,
  });
  const filters = panel.getByRole("group", {
    name: "Sentiment source type",
    exact: true,
  });
  await filters
    .getByRole("button", { name: "All sources", exact: true })
    .waitFor();
  assert.ok(actual?.items.length, "actual saved reading is available");
  assert.equal(
    await filters
      .getByRole("button", { name: "All sources", exact: true })
      .getAttribute("aria-pressed"),
    "true",
  );
  const actualSelected = sorted(actual.sources),
    actualIds = new Set(actual.items.map((item) => item.source_id));
  assert.deepEqual(
    await panel.locator(".sentiment-items article h3").allTextContents(),
    actualSelected
      .filter((source) => actualIds.has(source.id))
      .map(sourceHeadline)
      .filter(Boolean),
  );
  await filters.screenshot({
    path: path.join(evidence, "actual-icons-1440.png"),
  });
  await panel
    .locator(".all-source-summary")
    .screenshot({ path: path.join(evidence, "actual-all-summary-1440.png") });
  await panel
    .getByRole("button", { name: "Original sources", exact: true })
    .click();
  const original = panel.getByRole("region", {
    name: "Original selected sources",
    exact: true,
  });
  assert.deepEqual(
    await original.locator(".original-source-text").allTextContents(),
    actualSelected.map((source) => source.body),
  );
  await original
    .getByRole("button", { name: "Inspect original source ↗", exact: true })
    .first()
    .click();
  await page.getByRole("dialog").waitFor();
  await page.keyboard.press("Escape");
  mode = "fixture";
  await page.reload();
  await filters.waitFor();
  const expected = sorted(fixtureSources);
  for (const [scope, label] of Object.entries(labels)) {
    const button = filters.getByRole("button", { name: label, exact: true });
    assert.equal(await button.getAttribute("title"), label);
    const box = await button.boundingBox();
    assert.ok(box.width >= 44 && box.height >= 44);
    if (scope !== "all") assert.equal((await button.textContent()).trim(), "");
    await button.focus();
    await button.press("Enter");
    assert.equal(await button.getAttribute("aria-pressed"), "true");
    assert.deepEqual(
      await panel.locator(".sentiment-items article h3").allTextContents(),
      scope === "all"
        ? expected.map(sourceHeadline).filter(Boolean)
        : fixtureSources
            .filter((source) => scopeOf(source) === scope)
            .map(sourceHeadline)
            .filter(Boolean),
    );
  }
  await filters
    .getByRole("button", { name: "All sources", exact: true })
    .click();
  assert.equal(
    await panel
      .locator(".all-source-summary .source-summary-list > div")
      .count(),
    4,
  );
  assert.equal(
    await panel.locator(".sentiment-counts").count(),
    0,
    "All does not invent a pooled tone count",
  );
  assert.match(
    await panel.locator(".sentiment-items").innerText(),
    /Not about this company/,
  );
  assert.doesNotMatch(
    await panel.locator(".sentiment-items").innerText(),
    /Comparison-only report excluded/,
  );
  await panel.getByText("What are people discussing?", { exact: true }).click();
  const themes = panel.getByRole("region", {
    name: "Discussion themes",
    exact: true,
  });
  await themes.locator(".theme-card").first().waitFor();
  assert.equal(await themes.locator(".theme-card").count(), 4);
  assert.equal(
    await themes.locator(".theme-card > .source-attribution").count(),
    4,
  );
  await filters
    .getByRole("button", { name: "Company news", exact: true })
    .click();
  assert.equal(await themes.locator(".theme-card").count(), 1);
  await filters
    .getByRole("button", { name: "All sources", exact: true })
    .click();
  await panel.getByText("What are people discussing?", { exact: true }).click();
  const preview = panel.getByRole("region", {
    name: "Current sentiment inputs",
    exact: true,
  });
  await preview.getByText(/^Read current sources ·/).click();
  const previewFilters = preview.getByRole("group", {
    name: "Current source type",
    exact: true,
  });
  assert.equal(
    await previewFilters
      .getByRole("button", { name: "All sources", exact: true })
      .getAttribute("aria-pressed"),
    "true",
  );
  assert.deepEqual(
    await preview.locator(".original-source-text").allTextContents(),
    expected.map((source) => source.body),
  );
  assert.match(await preview.innerText(), /4 selected from 12 available/);
  for (const [scope, label] of Object.entries(labels)) {
    await previewFilters
      .getByRole("button", { name: label, exact: true })
      .click();
    assert.equal(
      await preview.locator("article").count(),
      scope === "all" ? 4 : 1,
    );
  }
  await previewFilters
    .getByRole("button", { name: "All sources", exact: true })
    .click();
  await preview.getByText(/^Read current sources ·/).click();
  for (const width of [1920, 1440, 1024, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 1100 });
    for (const reading of [false, true]) {
      await panel
        .getByRole("button", {
          name: reading ? "Original sources" : "AI interpretation",
          exact: true,
        })
        .click();
      const geometry = await page.evaluate(() => ({
        width: innerWidth,
        document: document.documentElement.scrollWidth,
        main: document.querySelector(".main-workspace").scrollWidth,
        mainClient: document.querySelector(".main-workspace").clientWidth,
      }));
      assert.ok(
        geometry.document <= width && geometry.main <= geometry.mainClient + 1,
      );
      if (reading) {
        assert.deepEqual(
          await original.locator(".original-source-text").allTextContents(),
          expected.map((source) => source.body),
        );
        assert.equal(
          await original.locator(".sentiment-tag,.sentiment-counts").count(),
          0,
        );
        assert.match(await original.innerText(), /Feed updated/);
      }
      layouts.push({ reading, ...geometry });
    }
    if ([1440, 390, 320].includes(width))
      await filters.screenshot({
        path: path.join(evidence, `icons-${width}.png`),
      });
    if ([1440, 390].includes(width))
      await original.screenshot({
        path: path.join(evidence, `all-original-${width}.png`),
      });
  }
  mode = "withheld";
  await page.reload();
  await panel
    .getByText("This analysis is withheld because source access changed.", {
      exact: true,
    })
    .waitFor();
  assert.equal(
    await panel
      .getByRole("button", { name: "Original sources", exact: true })
      .count(),
    0,
  );
  assert.equal(
    await panel.locator(".sentiment-items,.all-source-summary").count(),
    0,
  );
  mode = "no-analysis";
  await page.reload();
  await filters.waitFor();
  assert.equal(
    await panel
      .getByRole("button", { name: "Original sources", exact: true })
      .count(),
    0,
  );
  await preview.getByText(/^Read current sources ·/).click();
  assert.equal(await preview.locator("article").count(), 4);
  assert.deepEqual(errors, []);
  assert.deepEqual(external, []);
  assert.deepEqual(writes, []);
  fs.writeFileSync(
    path.join(evidence, "verification.json"),
    JSON.stringify(
      {
        actualSelected: actualSelected.length,
        actualScopes: [...new Set(actualSelected.map(scopeOf))],
        layouts,
        mockLoads,
        errors,
        external,
        writes,
      },
      null,
      2,
    ),
  );
  console.log(
    "Saved All reading/source inspection, icon keyboard filters, four-platform controlled combined/original/current views, source ordering, unrelated/comparison boundaries, scoped themes, withheld/no-analysis states and six responsive widths passed. Loading and authored fixtures are intercepted; no app writes or external requests.",
  );
})()
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  })
  .finally(async () => {
    await browser?.close();
  });
