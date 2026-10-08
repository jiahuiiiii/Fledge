const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");
let browser;
(async () => {
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
    paid = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.route("**/*", (r) => {
    const u = new URL(r.request().url());
    if (!["127.0.0.1", "localhost"].includes(u.hostname)) {
      external.push(u.href);
      return r.abort();
    }
    if (
      /\/(sentiment|refresh|generate|event-review|evidence-review|brief|idea-alert-check)$/.test(
        u.pathname,
      )
    )
      paid.push(u.href);
    return r.continue();
  });
  const base = process.env.THESIS_TEST_URL,
    iid = "c767e09f-35ea-5eaf-a626-ff5d3aa4709b";
  await page.goto(base + "/?company=" + iid + "&view=workspace");
  const panel = page.getByRole("region", {
    name: "News and social sentiment",
    exact: true,
  });
  const watch = panel.getByRole("checkbox", {
    name: "Watch news + social changes",
    exact: true,
  });
  await watch.waitFor();
  await watch.click();
  await panel.getByLabel("Alert focus").waitFor();
  await panel.getByLabel("Alert focus").selectOption("idea");
  await page.waitForFunction(
    () =>
      document.querySelector('select[aria-label="Alert focus"]')?.value ===
      "idea",
  );
  await panel.getByText(/Reasoning checks look for support/).waitFor();
  let state = (
    await (
      await page.request.get(base + "/api/v1/workspace?instrument_id=" + iid)
    ).json()
  ).result;
  assert.equal(state.news_watch.match_idea, true);
  assert.equal(state.idea_watch_state.status, "baseline");
  assert.equal(state.news_watch.idea_purpose, "reasoning");
  await panel.getByLabel("Alert focus").selectOption("question");
  await panel
    .getByText(/Question-focused checks look for concrete answers/)
    .waitFor();
  state = (
    await (
      await page.request.get(base + "/api/v1/workspace?instrument_id=" + iid)
    ).json()
  ).result;
  assert.equal(state.news_watch.idea_purpose, "question");
  assert.equal(state.idea_watch_state.status, "baseline");
  await panel.getByLabel("Watch frequency").selectOption("240");
  state = (
    await (
      await page.request.get(base + "/api/v1/workspace?instrument_id=" + iid)
    ).json()
  ).result;
  assert.equal(state.news_watch.idea_purpose, "question");
  await panel.getByText("Check against my idea", { exact: true }).click();
  await panel.getByLabel("Private check focus").selectOption("question");
  assert.match(
    await panel.innerText(),
    /Does adoption justify the product story/,
  );
  assert.match(await panel.innerText(), /Related background stays quiet/);
  // Choice itself must not dispatch any paid check; API purpose dispatch is tested separately.
  for (const width of [320, 390, 1440]) {
    await page.setViewportSize({ width, height: 1100 });
    await panel.getByLabel("Private check focus").scrollIntoViewIfNeeded();
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      `Focus controls overflow at ${width}`,
    );
    await page.screenshot({
      path: `/private/tmp/thesis-check-focus-${width}.png`,
    });
  }
  await watch.click();
  await panel.getByLabel("Alert focus").waitFor({ state: "hidden" });
  await page.getByRole("button", { name: "Updates", exact: true }).click();
  let checks = page.getByRole("region", {
    name: "Research update inbox",
    exact: true,
  });
  await checks.waitFor();
  const expand = async () => {
    for (const summary of await checks
      .locator(".inbox-record > summary")
      .all()) {
      if (await summary.evaluate((e) => !e.parentElement.open))
        await summary.click();
    }
  };
  await checks.locator(".inbox-record").first().waitFor();
  await expand();
  assert.equal(await checks.locator(".idea-alert-card").count(), 2);
  assert.match(await checks.innerText(), /Evidence toward your question/);
  assert.match(await checks.innerText(), /YOUR SAVED QUESTION/);
  assert.match(await checks.innerText(), /Your research stays open/);
  assert.match(await checks.innerText(), /reasoning revision 1/);
  assert.match(await checks.innerText(), /Risk to investigate/);
  assert.match(await checks.innerText(), /Answers to saved question/);
  assert.match(await checks.innerText(), /Connections to saved reasoning/);
  assert.match(
    await checks.innerText(),
    /Company-sentiment relevance labels did not filter this check/,
  );
  assert.match(
    await checks.innerText(),
    /This earlier selection filtered by company relevance/,
  );
  assert.match(await checks.innerText(), /has since changed or been archived/);
  assert.match(
    await checks.innerText(),
    /I want durable margins before relying on growth/,
  );
  await checks
    .getByText("Inspect the source evidence", { exact: true })
    .first()
    .click();
  await checks
    .getByRole("button", { name: "Open cited source ↗", exact: true })
    .first()
    .click();
  await page.getByRole("dialog").waitFor();
  assert.match(
    await page.getByRole("dialog").innerText(),
    /Microsoft has not confirmed|Synthetic Microsoft/,
  );
  await page.keyboard.press("Escape");
  const downloadEvent = page.waitForEvent("download");
  await checks
    .getByRole("link", { name: "Download this check", exact: true })
    .first()
    .click();
  const download = await downloadEvent;
  const html = fs.readFileSync(await download.path(), "utf8");
  assert.match(html, /Private research record/);
  assert.match(html, /Check focus: Answers to saved question/);
  assert.match(html, /What does the report say about Microsoft margins/);
  assert.match(html, /Evidence toward your question/);
  assert.match(
    html,
    /Company-sentiment relevance labels did not filter this check/,
  );
  assert.doesNotMatch(html, /<script/);
  for (const width of [320, 390, 1440]) {
    await page.setViewportSize({ width, height: 1100 });
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      `Overflow at ${width}`,
    );
    await page.screenshot({
      path: `/private/tmp/thesis-idea-alert-${width}.png`,
      fullPage: true,
    });
  }
  await checks
    .getByRole("button", { name: "Mark idea alert reviewed", exact: true })
    .first()
    .click();
  await page.waitForFunction(
    () => document.querySelectorAll(".idea-alert-card").length === 1,
  );
  await expand();
  await checks
    .getByRole("button", { name: "Mark idea alert reviewed", exact: true })
    .click();
  await page.waitForFunction(
    () => document.querySelectorAll(".idea-alert-card").length === 0,
  );
  await page.getByRole("button", { name: "History", exact: true }).click();
  checks = page.getByRole("region", {
    name: "Evidence linked to saved reasoning",
    exact: true,
  });
  await checks.waitFor();
  assert.equal(await checks.locator(".idea-alert-card").count(), 3);
  assert.match(
    await checks.innerText(),
    /No direct support, challenge, answer or specific risk identified/,
  );
  assert.match(await checks.innerText(), /Possible connection · not an alert/);
  assert.match(await checks.innerText(), /What would establish the link/);
  assert.match(await checks.innerText(), /These did not trigger an alert/);
  for (const width of [320, 390, 1440]) {
    await page.setViewportSize({ width, height: 1100 });
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    );
    await checks
      .locator(".idea-match.possible_link")
      .first()
      .screenshot({ path: `/private/tmp/thesis-possible-link-${width}.png` });
  }
  assert.match(await checks.innerText(), /Reviewed · recorded separately/);
  // Archive the current idea and preserve both private checks in the history.
  state = (
    await (
      await page.request.get(base + "/api/v1/workspace?instrument_id=" + iid)
    ).json()
  ).result;
  const v = state.versions[0];
  const archived = await page.request.post(base + "/api/v1/idea", {
    headers: { "X-Thesis-Request": "local-ui" },
    data: {
      instrument_id: iid,
      expected_revision: v.revision,
      question: v.question,
      reasoning: v.reasoning,
      status: "archived",
      conditions: [],
      events: [],
    },
  });
  assert.ok(archived.ok());
  await page.reload();
  await checks.waitFor();
  assert.equal(await checks.locator(".idea-alert-card").count(), 3);
  assert.equal(
    await checks
      .getByText(
        "Your idea has since changed or been archived. This check describes the earlier reasoning shown here.",
        { exact: true },
      )
      .count(),
    3,
  );
  assert.deepEqual(errors, []);
  assert.deepEqual(external, []);
  assert.deepEqual(paid, []);
  console.log(
    "Private alert browser passed: explicit watch scope, exact earlier reasoning/question/source, private inert export, review acknowledgement, quiet check history, edit/archive persistence, 320/390/1440 layouts, no automatic external or paid requests.",
  );
  await browser.close();
})().catch(async (e) => {
  console.error(e);
  if (browser) await browser.close();
  process.exit(1);
});
