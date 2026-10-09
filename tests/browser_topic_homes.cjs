// Authored layout/navigation cases over the disposable financials fixture.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const assert = require("node:assert/strict"),
  fs = require("node:fs"),
  path = require("node:path");
let browser, page;
(async () => {
  const base = process.env.THESIS_TEST_URL,
    iid = "c767e09f-35ea-5eaf-a626-ff5d3aa4709b";
  const folder =
    process.env.THESIS_TOPIC_HOMES_EVIDENCE ||
    "/private/tmp/thesis-topic-homes";
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
  page.on("pageerror", (e) => { errors.push(e.message); console.log("Page error:", e.message); });
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
    if (u.pathname === "/api/v1/model-status") { const response=await route.fetch(), packet=await response.json(); packet.result.briefing_enabled=true;packet.result.budget={...packet.result.budget,needs_attention:1,unresolved:1,running:0};return route.fulfill({response,json:packet}); }
    if (u.pathname === "/api/v1/workspace") {
      const response = await route.fetch(),
        packet = await response.json();
      packet.result.versions = [];
      packet.result.provider_status=Array.from({length:12},(_,i)=>({provider:`feed${i}`,label:`Feed ${i}`,channel:"news",status:i<2?"failed":"ready",message:i<2?"Authored unavailable feed":"Ready",checked_at:"2026-05-03T13:14:00Z"}));
      packet.result.market ||= {}; packet.result.market.status={completed_at:"2026-05-03T13:13:00Z",news_error:null};
      packet.result.social_status=[];
      packet.result.news_watch={enabled:true,last_check_at:"2026-05-03T13:14:00Z",error:"The scheduled source check did not complete.",next_check_at:"2026-05-03T14:14:00Z",interval_minutes:60};
      packet.result.sentiment={id:"authored-counts",created_at:"2026-05-03T13:14:00Z",social_lookback_days:7,summary_policy:"sentiment-coverage-9",items:[],sources:[],coverage_links:[],summary:{news:{tone:"mixed / balanced",selected:65,relevant:30,counted_groups:20,counts:{positive:8,neutral:6,mixed:2,negative:4,unclear:0}}},coverage:{available_news:65,selected_news:65,selection:{policy:"sentiment-all-eligible-1"}}};
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
  await page.goto(base + `/?company=${iid}&view=workspace`);
  await page.getByRole("heading", {name:"Overview",exact:true}).waitFor();await page.evaluate(()=>document.fonts.ready);
  const top=page.getByRole("navigation",{name:"Workspace navigation"}), sections=page.getByRole("tablist",{name:"Research views"});
  assert.equal(await top.getByRole("button",{name:"History",exact:true}).count(),0);
  assert.equal(await page.locator('.watchlist').getAttribute('data-collapsed'),'true');
  assert.equal(await page.getByRole('button',{name:'Notebook',exact:true}).count(),0);
  await page.getByRole('button',{name:'Expand company sidebar',exact:true}).click();await page.locator('.sidebar-research').waitFor();assert.equal(await page.locator('.sidebar-research').getByRole('heading',{name:'Your research',exact:true}).count(),1);
  await page.getByRole('button',{name:'Collapse company sidebar',exact:true}).click();
  await page.getByRole('button',{name:'Ask a question',exact:true}).click();const notebook=page.getByRole('dialog',{name:'Your research',exact:true});await notebook.getByRole('button',{name:'Start with a question',exact:true}).click();await page.getByRole('dialog',{name:'Start with a question',exact:true}).waitFor();await page.keyboard.press('Escape');assert.equal(await notebook.isVisible(),true);await notebook.getByRole('button',{name:'Edit question',exact:true}).click();await notebook.locator('#specific-question').fill('What would change my view?');await page.keyboard.press('Escape');
  await sections.getByRole('tab',{name:'Financials',exact:true}).click();const story=page.locator('.financials-story'), history=page.getByRole('region',{name:'Earnings and cash-flow history',exact:true}), more=page.locator('.financial-more-detail');
  await history.locator('.story-selected-values').getByText('US$64bn',{exact:true}).waitFor();
  assert.equal(await story.locator(':scope > .financial-story-section:visible').count(),3);assert.equal(await story.locator('.sector-position').count(),0);assert.equal(await story.getByRole('button',{name:'Evidence',exact:true}).count(),0);assert.equal(await page.locator('.financial-reports-panel').isVisible(),false);
  const growth=page.locator('.financial-summary-row article').first().getByRole('button');await growth.focus();await page.keyboard.press('Enter');const evidence=page.getByRole('dialog',{name:'Revenue growth · past 12 months',exact:true});assert.match(await evidence.innerText(),/US\$64 bil/);assert.match(await evidence.innerText(),/US\$52 bil/);await page.keyboard.press('Escape');assert.equal(await growth.evaluate(el=>el===document.activeElement),true);
  await more.locator(':scope > summary').click();assert.equal(await page.locator('.financial-reports-panel').isVisible(),true);await page.getByRole('region',{name:'Borrowing and equity history',exact:true}).waitFor();assert.match(await more.innerText(),/US\$30bn surplus/);await more.locator(':scope > summary').click();
  await story.getByRole('button',{name:'Fiscal year',exact:true}).click();await page.getByRole('button',{name:'Ask a question',exact:true}).click();assert.equal(await notebook.locator('#specific-question').inputValue(),'What would change my view?');await page.keyboard.press('Escape');
  for(const width of [1440,1920,980,390,320]) {
    await page.setViewportSize({width,height:width<600?844:1050});await top.getByRole('button',{name:'Workspace',exact:true}).click();await sections.getByRole('tab',{name:'Financials',exact:true}).click();assert.equal(await story.getByRole('button',{name:'Fiscal year',exact:true}).getAttribute('aria-pressed'),'true');
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));layouts.push({width,readingWidth:await page.locator('.research-content').evaluate(el=>el.getBoundingClientRect().width)});await page.evaluate(()=>{document.querySelector('.main-workspace').scrollTop=0;window.scrollTo(0,0)});await page.screenshot({path:path.join(folder,`financials-${width}.png`),animations:'disabled'});
    await sections.getByRole('tab',{name:'Outlook',exact:true}).click();await page.getByRole('heading',{name:'Management outlook',exact:true}).waitFor();await page.getByRole('heading',{name:'Analyst forecasts',exact:true}).waitFor();assert.equal(await page.locator('.outlook-page .sector-position').count(),0);assert.equal(await page.locator('.management-outlook').isVisible(),true);assert.equal(await page.locator('.outlook-analysts').isVisible(),true);await page.screenshot({path:path.join(folder,`outlook-${width}.png`),animations:'disabled'});
    await sections.getByRole('tab',{name:'Compare & value',exact:true}).click();await page.locator('.sector-position:visible .position-group').waitFor();assert.equal(await page.locator('.sector-position').count(),1);assert.equal(await page.getByRole('heading',{name:'Choose useful comparisons',exact:true}).count(),0);
    await sections.getByRole('tab',{name:'News & discussion',exact:true}).click();const tone=page.getByRole('region',{name:'News and social sentiment',exact:true});await tone.waitFor();assert.match(await tone.locator('.sample-reconciliation').innerText(),/65 stories → 30 relevant → 20 distinct developments/);assert.match(await tone.locator('.news-section-status > summary').innerText(),/11 of 13 news feeds checked successfully · 2 need attention/);assert.equal(await tone.getByRole('button',{name:'Refresh & analyse',exact:true}).isDisabled(),true);await tone.locator('.sentiment-reading-settings > summary').click();assert.equal(await tone.getByLabel('Discussion window',{exact:true}).isVisible(),true);await tone.locator('.sentiment-reading-settings > summary').click();assert.match(await tone.locator('#sentiment-disabled-reason').innerText(),/paused/);assert.equal(await tone.locator(':scope > .warning, :scope > .coverage-inline-notice').count(),0);await tone.locator('.market-section-head').evaluate(el=>el.scrollIntoView({block:'start'}));await page.evaluate(()=>{const main=document.querySelector('.main-workspace');if(getComputedStyle(main).overflowY==='auto')main.scrollTop-=100;else window.scrollBy(0,-105)});await page.screenshot({path:path.join(folder,`news-${width}.png`),animations:'disabled'});
    await tone.locator('.news-section-status > summary').click();assert.match(await tone.locator('.news-status-details').innerText(),/scheduled source check/);await tone.locator('.news-section-status > summary').click();
    await top.getByRole('button',{name:'My ideas',exact:true}).click();assert.equal(await page.locator('.periodic-review-entry').count(),0);assert.equal(await page.locator('.ideas-empty').count(),1);
    await top.getByRole('button',{name:'Updates',exact:true}).click();const card=page.locator('.inbox-record > summary').first();await card.waitFor();assert.equal(await card.locator('h3').innerText(),source.title);assert.match(await card.innerText(),/June to September/);assert.equal(await page.getByRole('button',{name:/Weekly review/}).count(),1);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(folder,`updates-${width}.png`),animations:'disabled'});
  }
  await page.goto(base+`/?company=${iid}&view=history`);await page.locator('.idea-history[open]').waitFor();await page.getByText('No saved history yet',{exact:true}).waitFor();assert.equal(await top.getByRole('button',{name:'History',exact:true}).count(),0);
  await page.setViewportSize({width:1440,height:1050});await page.getByRole('button',{name:'All companies',exact:true}).click();await page.locator('.company-overview-grid[aria-busy="false"]').waitFor();assert.ok(await page.locator('.company-overview-tone').count()>0);await page.screenshot({path:path.join(folder,'all-companies-1440.png'),animations:'disabled'});
  assert.deepEqual(errors,[]);assert.deepEqual(writes,[]);assert.deepEqual(external,[]);
  console.log(JSON.stringify({layouts,threeMainCharts:true,figureEvidence:true,onePeerHome:true,expandedOutlook:true,countsReconcile:true,oneNewsStatus:true,disabledReason:true,ideaHistory:true,compactDefault:true,companyTone:true,questionDraft:true,errors,writes,external}));
})().catch(async error=>{console.error(error);if(page){console.log((await page.locator("body").innerText()).slice(0,9000));await page.screenshot({path:"/private/tmp/topic-homes-failure.png"});}process.exitCode=1;}).finally(async()=>{await browser?.close();});
