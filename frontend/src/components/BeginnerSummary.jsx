import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useProfile } from "../lib/profile";
import { latestPriceQuote, quoteMovement } from "../lib/priceRefresh";
import { companyName } from "../lib/companyIdentity";
import { overviewNews } from "../lib/overviewSections";
import { sourceCoverage } from "../lib/sourceCoverage";
import {
  countLabel,
  countMood,
  groupByTone,
  newsMeaning,
  peopleMeaning,
  priceLine,
  socialTones,
  worldForCompany,
  worldLight,
} from "../lib/beginnerSummary";
import { useWorkspace, WorkspaceProvider } from "./workspace/WorkspaceContext";
import WidgetBoard from "./workspace/WidgetBoard";
import "./BeginnerSummary.css";

// Beginner summary, "Signals" layout: the price, three lights (News, People
// online, World) readable in seconds, one-line reasons, a merged list of what
// happened, and the user's own view. No charts. Everything rewords saved
// readings; Fledge never says buy or sell. The blocks are widgets
// (workspace/SummaryWidgets.jsx) the user can arrange; this component builds
// the shared model they read. Inputs and actions come from WorkspaceContext.
// One automatic world check per company per page load of the app.
const worldChecked = new Set();

export default function BeginnerSummary() {
  const workspace = useWorkspace();
  const { data, instrumentId, visible, practice = false } = workspace;
  const priceHistory = workspace.priceHistory ?? null;
  const [world, setWorld] = useState(null);
  const { mode, setDetailMode } = useProfile();
  useEffect(() => {
    if (!visible) return;
    let active = true;
    api
      .worldNews()
      .then(async (page) => {
        if (!active) return;
        setWorld(page);
        // Link world headlines to this company automatically (a small AI
        // check; the same headlines and list reuse the saved answer).
        const covered = page?.check?.company_ids?.includes(instrumentId);
        const fresh =
          page?.check &&
          Date.now() - Date.parse(page.check.checked_at) < 3 * 3600 * 1000;
        if (
          practice ||
          !page?.ai?.available ||
          !page?.articles?.length ||
          (covered && fresh) ||
          worldChecked.has(instrumentId)
        )
          return;
        worldChecked.add(instrumentId);
        const next = await api.checkWorldNews().catch(() => null);
        if (active && next) setWorld(next);
      })
      .catch(() => active && setWorld({ articles: [] }));
    return () => {
      active = false;
    };
  }, [visible, instrumentId]);

  const name = companyName(data.instrument);
  // Same price and change as the header: the newest of Finnhub and Yahoo.
  const latest = latestPriceQuote(data.market, priceHistory);
  const live = latest && quoteMovement(data.market, priceHistory);
  const price = live
    ? priceLine({ price: Number(latest.price), change_percent: live.percent })
    : priceLine(data.market?.quote?.quote);
  const reading = data.sentiment?.withheld ? null : data.sentiment;
  const scopes = sourceCoverage(reading).scopes;
  const newsTone = scopes.find((s) => s.scope === "news");
  const social = socialTones(scopes);
  const items = overviewNews(data);
  const analysedNews = items.filter((s) => s.kind === "news");
  // Without a news reading, show the saved company documents instead (newest
  // first, no tone), so the card is never empty when sources exist.
  const news = (
    analysedNews.length
      ? analysedNews
      : (data.documents || [])
          .filter((d) => d.title)
          .map((d) => ({ ...d, headline: d.title }))
          .sort(
            (a, b) => Date.parse(b.published_at) - Date.parse(a.published_at),
          )
  ).slice(0, 5);
  const { linked } = worldForCompany(world, instrumentId);
  const allPosts = items.filter((s) => s.kind === "social");
  const newsGroups = groupByTone(
    news.length ? (analysedNews.length ? analysedNews : news) : [],
  );
  const postGroups = groupByTone(allPosts);
  const links = linked.filter((x) => x.link);
  const worldState = worldLight(linked, name);
  const lights = [
    {
      key: "news",
      title: "News",
      mood: countMood(newsGroups),
      status: countLabel(newsGroups),
    },
    {
      key: "people",
      title: "People online",
      mood: countMood(postGroups),
      status: countLabel(postGroups, {
        good: "upbeat",
        bad: "worried",
        neutral: "neutral",
      }),
    },
    {
      key: "world",
      title: "World",
      mood: worldState.mood,
      status: worldState.status,
    },
  ];
  const pointer = worldState.hurt
    ? worldState.reason
    : newsGroups.bad.length > newsGroups.good.length
      ? "There has been more bad news than good recently. Read both sides below."
      : null;

  const summary = {
    name,
    price,
    reading,
    social,
    news,
    newsGroups,
    postGroups,
    links,
    worldState,
    lights,
    pointer,
    newsMeaning: newsMeaning(newsGroups),
    peopleMeaning: peopleMeaning(postGroups),
  };

  return (
    <WorkspaceProvider value={{ ...workspace, summary }}>
      <div className="beginner-summary signals">
        {practice && (
          <p className="bs-practice">
            <strong>Practice company, not real.</strong> Sample news and posts
            that show how Fledge works.
          </p>
        )}
        <WidgetBoard page="overview" />
        <p className="bs-note">
          The News, Financials and Compare tabs go deeper.
        </p>
      </div>
    </WorkspaceProvider>
  );
}
