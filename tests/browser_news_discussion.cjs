// Original saved texts lead the UI; browsing must not generate or write.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const assert = require("node:assert/strict"),
  fs = require("node:fs");
let browser;
(async () => {
  const { sourceHeadline } = await import(
    "../frontend/src/lib/sourceHeadline.js"
  );
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_PATH,
  });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1050 },
    reducedMotion: "reduce",
  });
  const base = process.env.THESIS_TEST_URL,
    iid = "c767e09f-35ea-5eaf-a626-ff5d3aa4709b",
    errors = [],
    writes = [],
    external = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.route("**/*", (route) => {
    const request = route.request(),
      url = new URL(request.url());
    if (
      url.hostname === "financialmodelingprep.com" &&
      request.resourceType() === "image"
    )
      return route.fulfill({ status: 404, body: "Authored missing logo" });
    if (!url.href.startsWith(base)) {
      external.push(url.href);
      return route.abort();
    }
    if (url.pathname.endsWith("/loading"))
      return route.fulfill({ json: { result: { active: false, steps: [] } } });
    if (request.method() !== "GET") {
      writes.push(url.pathname);
      return route.abort();
    }
    return route.continue();
  });
  const panel = page.getByRole("region", {
    name: "News and social sentiment",
    exact: true,
  });
  const filters = panel.getByRole("group", {
    name: "Sentiment source type",
    exact: true,
  });
  const open = async () => {
    await page.goto(base + `/?company=${iid}&view=workspace`);
    await page
      .getByRole("tab", { name: "News & discussion", exact: true })
      .click();
    await panel
      .getByRole("heading", { name: "What’s the tone?", exact: true })
      .waitFor();
  };
  await open();
  const saved = (
    await (
      await page.request.get(base + `/api/v1/workspace?instrument_id=${iid}`)
    ).json()
  ).result;
  const news = saved.sentiment.items
    .filter((i) => i.channel === "news")
    .slice(0, 12)
    .map((i) => saved.sentiment.sources.find((s) => s.id === i.source_id));
  assert.deepEqual(
    await panel.locator(".story-source-text").allTextContents(),
    news.map((s) => s.body),
  );
  assert.deepEqual(
    await panel.locator(".source-story > h3").allTextContents(),
    news.map(sourceHeadline).filter(Boolean),
  );
  const names = {
    news: "Company news",
    reddit: "Reddit discussion",
    hackernews: "Hacker News",
    x: "X / Twitter",
    all: "All sources",
  };
  const sources = ["news", "reddit", "hackernews", "hackernews", "x"].map(
    (scope, n) => ({
      id: `source-${n}`,
      kind: scope === "news" ? "news" : "social",
      platform: scope === "news" ? null : scope,
      title: [
        "Authored chipmaker expands production",
        "Is chip demand sustainable?",
        "Hacker News comment",
        "Hacker News comment",
        "X post",
      ][n],
      body: [
        "The chipmaker announced additional production capacity. The supplied report does not state how much demand has changed.",
        "I would like to see customer demand before deciding whether this growth can continue.",
        "I do not think this establishes a lasting advantage for Broadcom. A customer can switch designs, but the software support matters too.",
        "The comment describes a trade-off, not a confirmed result. " +
          "Long authored source text retains the original wording and can be read in full from evidence. ".repeat(
            20,
          ),
        "This is one person’s view about the company. Literal text: <b>unverified claim</b>, not formatted HTML.",
      ][n],
      source:
        scope === "hackernews"
          ? "Hacker News · comments"
          : scope === "reddit"
            ? "r/authored"
            : "Authored " + scope,
      published_at: `2026-10-08T${String(12 - n).padStart(2, "0")}:00:00Z`,
      available_at: "2026-10-08T13:00:00Z",
      timestamp_basis: scope === "reddit" ? "feed_updated" : undefined,
      url: "https://example.test/" + n,
    }),
  );
  const fixture = {
    ...saved.sentiment,
    id: "authored-news-discussion-ui",
    sources,
    coverage_links: [],
    items: sources.map((s, n) => ({
      id: "item-" + n,
      source_id: s.id,
      channel: s.kind,
      relevance: n === 4 ? "unrelated" : "relevant",
      sentiment: n === 2 ? "negative" : "neutral",
      statement: n === 2 ? "opinion" : "reported_development",
      explanation: "Generic authored AI explanation " + n,
      citations: [{ quote: s.body }],
    })),
    summary: {
      news: {
        selected: 1,
        relevant: 1,
        tone: "thin sample",
        counts: { neutral: 1 },
      },
      social_platforms: Object.fromEntries(
        ["reddit", "hackernews", "x"].map((p) => [
          p,
          {
            selected: sources.filter((s) => s.platform === p).length,
            relevant:
              p === "x" ? 0 : sources.filter((s) => s.platform === p).length,
            tone: "thin sample",
            counts: { neutral: 1 },
          },
        ]),
      ),
    },
  };
  let mode = "saved";
  await page.route("**/api/v1/workspace*", async (route) => {
    const response = await route.fetch(),
      body = await response.json();
    body.result.sentiment =
      mode === "none" ? null : { ...fixture, withheld: mode === "withheld" };
    body.result.sentiment_inputs = {
      status:
        mode === "none"
          ? "no_saved_reading"
          : mode === "withheld"
            ? "saved_reading_withheld"
            : "same",
      sources,
      as_of: fixture.cutoff,
      scopes: Object.fromEntries(
        ["news", "reddit", "hackernews", "x"].map((p) => [
          p,
          {
            selected: sources.filter(
              (s) => (s.kind === "news" ? "news" : s.platform) === p,
            ).length,
            available: 3,
            added: 0,
            no_longer_selected: 0,
            retained: 1,
          },
        ]),
      ),
    };
    await route.fulfill({ response, json: body });
  });
  await open();
  for (const scope of ["all", "news", "reddit", "hackernews", "x"]) {
    await filters
      .getByRole("button", { name: names[scope], exact: true })
      .click();
    const selected = sources.filter(
      (s) =>
        scope === "all" || (s.kind === "news" ? "news" : s.platform) === scope,
    );
    assert.deepEqual(
      await panel.locator(".story-source-text").allTextContents(),
      selected.map((s) => s.body),
    );
    assert.deepEqual(
      await panel.locator(".source-story > h3").allTextContents(),
      selected.map(sourceHeadline).filter(Boolean),
    );
    assert.ok(
      !(await panel.locator(".sentiment-items").innerText()).includes(
        "Generic authored AI explanation",
      ),
    );
  }
  await filters
    .getByRole("button", { name: "Hacker News", exact: true })
    .click();
  assert.equal(await panel.locator(".source-story > h3").count(), 0);
  const comment = panel.locator('.source-story[data-source-id="source-3"]');
  await comment
    .getByRole("button", { name: "Inspect evidence", exact: true })
    .focus();
  await page.keyboard.press("Enter");
  const story = page.getByRole("dialog", {
    name: "Story evidence",
    exact: true,
  });
  await story.waitFor();
  assert.equal(
    await story.locator(".story-full-text p").textContent(),
    sources[3].body,
  );
  assert.match(await story.innerText(), /Generic authored AI explanation 3/);
  await page.keyboard.press("Escape");
  await story.waitFor({ state: "hidden" });
  assert.equal(
    await comment
      .getByRole("button", { name: "Inspect evidence", exact: true })
      .evaluate((el) => el === document.activeElement),
    true,
  );
  const snapshot = async (name) => {
    if (process.env.THESIS_NEWS_UI_EVIDENCE)
      await panel.locator(".sentiment-items").screenshot({
        path: `${process.env.THESIS_NEWS_UI_EVIDENCE}/${name}.png`,
        animations: "disabled",
      });
  };
  for (const width of [1440, 980, 390, 320]) {
    await page.setViewportSize({ width, height: 1050 });
    await panel
      .locator(".source-story")
      .first()
      .evaluate((el) => el.scrollIntoView({ block: "start" }));
    await page.evaluate(
      () =>
        new Promise((resolve) =>
          requestAnimationFrame(() => requestAnimationFrame(resolve)),
        ),
    );
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      `discussion overflow ${width}`,
    );
    assert.equal(
      await comment
        .locator(".story-source-text")
        .evaluate((el) => getComputedStyle(el).webkitLineClamp),
      "4",
    );
    assert.equal(
      await panel
        .locator(".source-story")
        .first()
        .evaluate((el) => getComputedStyle(el).display),
      "flex",
    );
    assert.doesNotMatch(
      await panel.locator(".sentiment-items").innerText(),
      /Invalid Date/,
    );
    assert.ok(
      await comment
        .getByRole("button", { name: "Inspect evidence", exact: true })
        .evaluate((el) => el.getBoundingClientRect().height >= 44),
    );
    await snapshot(`comments-${width}`);
  }
  await filters
    .getByRole("button", { name: "All sources", exact: true })
    .click();
  assert.equal(
    await panel
      .locator('.source-story[data-source-id="source-4"] .story-source-text b')
      .count(),
    0,
  );
  assert.match(
    await panel.locator('.source-story[data-source-id="source-4"]').innerText(),
    /Not about this company/,
  );
  await panel.getByRole("button", { name: "Evidence", exact: true }).click();
  const evidence = page.getByRole("dialog", {
    name: "News & discussion · evidence",
    exact: true,
  });
  const original = evidence.getByRole("region", {
    name: "Original selected sources",
    exact: true,
  });
  assert.deepEqual(
    await original.locator(".original-source-text").allTextContents(),
    sources.map((s) => s.body),
  );
  assert.deepEqual(
    await original.locator("article h3").allTextContents(),
    sources.map(sourceHeadline).filter(Boolean),
  );
  assert.equal(await original.locator(".sentiment-tag").count(), 0);
  await evidence
    .getByRole("button", { name: "Current sources", exact: true })
    .click();
  const current = evidence.getByRole("region", {
    name: "Current sentiment inputs",
    exact: true,
  });
  await current
    .getByRole("group", { name: "Current source type", exact: true })
    .getByRole("button", { name: "Hacker News", exact: true })
    .click();
  assert.equal(await current.locator("article h3").count(), 0);
  assert.deepEqual(
    await current.locator(".original-source-text").allTextContents(),
    sources.filter((s) => s.platform === "hackernews").map((s) => s.body),
  );
  await page.keyboard.press("Escape");
  mode = "withheld";
  await open();
  await panel
    .getByText("This analysis is withheld because source access changed.", {
      exact: true,
    })
    .waitFor();
  assert.equal(
    await panel.locator(".story-source-text,.sentiment-items").count(),
    0,
  );
  mode = "none";
  await open();
  assert.equal(await panel.locator(".sentiment-items").count(), 0);
  assert.deepEqual(errors, []);
  assert.deepEqual(writes, []);
  assert.deepEqual(external, []);
  const unchanged = (
    await (
      await page.request.get(base + `/api/v1/workspace?instrument_id=${iid}`)
    ).json()
  ).result;
  assert.deepEqual(unchanged.sentiment, saved.sentiment);
  assert.deepEqual(unchanged.news_watch, saved.news_watch);
  const report = {
    viewports: [1440, 980, 390, 320],
    exactOriginalTexts: true,
    genericHeadingsRemoved: true,
    labelsSecondary: true,
    explanationsInEvidence: true,
    fullOriginalInEvidence: true,
    keyboardFocusReturn: true,
    originalCurrentBodiesPreserved: true,
    withheldNoAnalysis: true,
    unchangedSavedAnalysisWatch: true,
    errors,
    writes,
    external,
  };
  if (process.env.THESIS_NEWS_UI_EVIDENCE)
    fs.writeFileSync(
      `${process.env.THESIS_NEWS_UI_EVIDENCE}/browser.json`,
      JSON.stringify(report, null, 2),
    );
  console.log(JSON.stringify(report));
})()
  .catch((e) => {
    console.error(e);
    process.exitCode = 1;
  })
  .finally(async () => {
    await browser?.close();
  });
