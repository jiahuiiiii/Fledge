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
  plainTone,
  priceLine,
  socialTones,
  worldForCompany,
  worldLight,
} from "../lib/beginnerSummary";
import { Button, Card, ChevronRightIcon, SectionHeader } from "./ui";
import {
  PriceMoveLine,
  SignalLights,
  ToneHeadlineGroups,
  WorldSignalCard,
  YourViewCard,
} from "./OverviewShared";
import "./BeginnerSummary.css";

// Beginner summary, "Signals" layout: the price, three lights (News, People
// online, World) readable in seconds, one-line reasons, a merged list of what
// happened, and the user's own view. No charts. Everything rewords saved
// readings; Fledge never says buy or sell.
// One automatic world check per company per page load of the app.
const worldChecked = new Set();

export default function BeginnerSummary({
  data,
  instrumentId,
  visible,
  savedView,
  onSaveView,
  onView,
  onSource,
  onWorld,
  onUpdate,
  onRate,
  rating = false,
  priceHistory = null,
  practice = false,
}) {
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
          .sort((a, b) => Date.parse(b.published_at) - Date.parse(a.published_at))
  ).slice(0, 5);
  const { linked } = worldForCompany(world, instrumentId);
  const allPosts = items.filter((s) => s.kind === "social");
  const newsGroups = groupByTone(news.length ? (analysedNews.length ? analysedNews : news) : []);
  const postGroups = groupByTone(allPosts);
  const links = linked.filter((x) => x.link);
  const worldState = worldLight(linked, name);
  const lights = [
    { key: "news", title: "News", mood: countMood(newsGroups), status: countLabel(newsGroups) },
    {
      key: "people",
      title: "People online",
      mood: countMood(postGroups),
      status: countLabel(postGroups, { good: "upbeat", bad: "worried", neutral: "neutral" }),
    },
    { key: "world", title: "World", mood: worldState.mood, status: worldState.status },
  ];
  const pointer = worldState.hurt
    ? worldState.reason
    : newsGroups.bad.length > newsGroups.good.length
      ? "There has been more bad news than good recently. Read both sides below."
      : null;

  return (
    <div className="beginner-summary signals">
      {practice && (
        <p className="bs-practice">
          <strong>Practice company, not real.</strong> Sample news and posts
          that show how Fledge works.
        </p>
      )}
      {price?.move && <PriceMoveLine price={price} />}
      <SignalLights name={name} lights={lights} pointer={pointer} />

      <Card id="bs-news" tabIndex={-1} aria-labelledby="bs-news-title">
        <SectionHeader level="card" as="h4" id="bs-news-title" title="News: what happened" />
        <p className="bs-meaning">{newsMeaning(newsGroups)}</p>
        {onRate && !reading && (newsGroups.unrated.length > 0 || postGroups.unrated.length > 0) && (
          <div className="bs-rate">
            <Button variant="primary" onClick={onRate} disabled={!!rating}>
              {rating === "running"
                ? "Rating… about a minute"
                : rating
                  ? "Getting the latest posts first…"
                  : "Rate with AI"}
            </Button>
            <small>Fledge reads the news and posts and marks each good, bad or mixed.</small>
          </div>
        )}
        <ToneHeadlineGroups groups={newsGroups} onSource={onSource} reading={reading} />
        {!news.length && onUpdate && (
          <p>
            <Button variant="tertiary" size="inline" onClick={onUpdate}>
              Get the latest news
            </Button>
          </p>
        )}
        <div className="bs-actions">
          <Button
            variant="tertiary"
            size="sm"
            iconEnd={<ChevronRightIcon />}
            onClick={() => onView?.("evidence")}
          >
            All news & posts
          </Button>
          {!practice && onRate && (
            <Button
              variant="tertiary"
              size="sm"
              iconEnd={<ChevronRightIcon />}
              onClick={() => onView?.("evidence")}
            >
              Turn on news alerts
            </Button>
          )}
        </div>
      </Card>

      <Card id="bs-people" tabIndex={-1} aria-labelledby="bs-people-title">
        <SectionHeader
          level="card"
          as="h4"
          id="bs-people-title"
          title="What people online are saying"
        />
        <p className="bs-meaning">{peopleMeaning(postGroups)}</p>
        {social.length > 0 && (
          <p className="bs-muted bs-platforms">
            {social
              .map((s) => `${s.platform}: ${plainTone(s.tone).toLowerCase()}`)
              .join(" · ")}
          </p>
        )}
        <ToneHeadlineGroups groups={postGroups} onSource={onSource} reading={reading} social />
      </Card>

      <WorldSignalCard links={links} worldState={worldState} onWorld={onWorld} />
      <YourViewCard savedView={savedView} name={name} onSaveView={onSaveView} />

      <p className="bs-note">
        The News, Financials and Compare tabs go deeper.
      </p>
    </div>
  );
}
