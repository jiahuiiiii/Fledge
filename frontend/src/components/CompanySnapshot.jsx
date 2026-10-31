import { formatTimestamp } from "../lib/dateTime";
import { day, snapshot } from "../lib/companySnapshot";
import "./CompanySnapshot.css";
import TermHelp from "./TermHelp";
import OverviewSections from "./OverviewSections";
import LatestActivity from "./LatestActivity";
import { companyName } from "../lib/companyIdentity";
import { Button, Card, Disclosure, SectionHeader } from "./ui";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import { latestPriceQuote, quoteMovement } from "../lib/priceRefresh";
import {
  countLabel,
  countMood,
  groupByTone,
  newsMeaning,
  peopleMeaning,
  priceLine,
  worldForCompany,
  worldLight,
} from "../lib/beginnerSummary";
import {
  PriceMoveLine,
  SignalLights,
  ToneHeadlineGroups,
  YourViewCard,
  WorldSignalCard,
} from "./OverviewShared";
import "./BeginnerSummary.css";
import {
  currentGuidance,
  overviewNews,
  revenueComparisons,
} from "../lib/overviewSections";

const when = (value) => formatTimestamp(value, { fallback: "Not checked" });

// Collection status is separate from the dates and limits of each conclusion.
function Freshness({ data }) {
  const checks = (data?.source_checks || []).filter((c) => c.checked_at);
  if (!checks.length) return null;
  const latest = checks
    .map((c) => c.checked_at)
    .sort((a, b) => Date.parse(b) - Date.parse(a))[0];
  const states = (data.source_checks || []).map((c) => c.state);
  return (
    <p className="glance-freshness">
      <span>
        Data freshness · latest source check {when(latest)}
        {states.includes("stale") && " · some coverage is over 24 hours old"}
        {states.some(
          (state) => !["fresh", "stale", "unknown"].includes(state),
        ) && " · some source checks did not finish successfully"}
        {states.includes("unknown") && " · some coverage is unknown"}
      </span>
    </p>
  );
}

export default function CompanySnapshot({
  data,
  instrumentId,
  onView,
  onUpdates,
  chart = null,
  visible,
  onSource,
  businessPanel,
  focusTopic,
  savedView,
  onSaveView,
  financialError,
  onRetryFinancials,
  priceHistory,
  onWorld,
  detailsOnly = false,
}) {
  const { sentences, growth } = snapshot(data);
  const { latestQuarter } = revenueComparisons(
    data,
    currentGuidance(data?.management_outlook),
  );
  const [world, setWorld] = useState(null);
  const [briefOpen, setBriefOpen] = useState(false);
  useEffect(() => {
    if (focusTopic) setBriefOpen(true);
  }, [focusTopic]);
  useEffect(() => {
    if (!visible) return;
    let active = true;
    api
      .worldNews()
      .then((page) => {
        if (active) setWorld(page);
      })
      .catch(() => {
        if (active) setWorld({ articles: [] });
      });
    return () => {
      active = false;
    };
  }, [visible, instrumentId]);
  const name = companyName(data.instrument);
  const latest = latestPriceQuote(data.market, priceHistory);
  const live = latest && quoteMovement(data.market, priceHistory);
  const price = live
    ? priceLine({ price: Number(latest.price), change_percent: live.percent })
    : priceLine(data.market?.quote?.quote);
  const reading = data.sentiment?.withheld ? null : data.sentiment;
  const items = overviewNews(data);
  const analysedNews = items.filter((item) => item.kind === "news");
  const news = analysedNews.length
    ? analysedNews
    : (data.documents || [])
        .filter((d) => d.title)
        .map((d) => ({ ...d, headline: d.title }))
        .sort(
          (a, b) => Date.parse(b.published_at) - Date.parse(a.published_at),
        );
  const newsGroups = groupByTone(news);
  const postGroups = groupByTone(
    items.filter((item) => item.kind === "social"),
  );
  const { linked } = worldForCompany(world, instrumentId, 2);
  const links = linked.filter((item) => item.link);
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
  return (
    <section className="glance pro-overview" aria-label="Company overview">
      {!detailsOnly && <PriceMoveLine price={price} pro />}
      <SectionHeader level="section" as="h2" title="At a glance" />
      {data.financials_pending ? (
        <p className="glance-summary muted" role="status">
          {financialError || "Loading saved financials…"}
          {financialError && (
            <Button variant="tertiary" onClick={onRetryFinancials}>
              Try again
            </Button>
          )}
        </p>
      ) : sentences.length ? (
        <p className="glance-summary">
          {latestQuarter ? (
            <span className="glance-growth">
              <span className="glance-growth-title">
                <strong>
                  Revenue {latestQuarter.growth >= 0 ? "up" : "down"}{" "}
                  {Math.abs(latestQuarter.growth).toFixed(1)}% · latest quarter
                  vs a year earlier
                </strong>
                <TermHelp term="revenue_growth" />
              </span>
              <small>
                Quarter to {day(latestQuarter.current.end)} vs quarter to{" "}
                {day(latestQuarter.previous.end)}
                {growth &&
                  ` · fiscal year to ${day(growth.periodEnd)}: ${growth.growth >= 0 ? "+" : "−"}${Math.abs(growth.growth).toFixed(1)}%`}
              </small>
            </span>
          ) : (
            growth && (
              <span className="glance-growth">
                <span className="glance-growth-title">
                  <strong>
                    Revenue {growth.growth >= 0 ? "grew" : "fell"}{" "}
                    {Math.abs(growth.growth).toFixed(1)}% · last fiscal year
                  </strong>
                  <TermHelp term="revenue_growth" />
                </span>
                <small>
                  Year ended {day(growth.periodEnd)} vs year ended{" "}
                  {day(growth.previousEnd)}
                </small>
              </span>
            )
          )}
          {sentences.slice(growth ? 1 : 0).join(" ")}
        </p>
      ) : (
        <p className="glance-summary muted">
          A short summary appears once filings and news are loaded. Use Update
          to load them.
        </p>
      )}
      <Freshness data={data} />
      {!detailsOnly && (
        <SignalLights
          name={name}
          lights={lights}
          pointer={pointer?.replace(/\s*Read (?:why|both sides) below\.?$/, "")}
          pointerLink={
            pointer
              ? {
                  target: worldState.hurt ? "bs-world" : "bs-news",
                  label: worldState.hurt ? "Read why" : "Read both sides",
                }
              : null
          }
        />
      )}
      {!detailsOnly && (
        <>
          <SectionHeader
            level="section"
            as="h2"
            title="What's being said"
            actions={
              <Button
                variant="tertiary"
                size="sm"
                onClick={() => onView("evidence")}
              >
                All news and posts →
              </Button>
            }
          />
          <div className="pro-overview-headlines">
            <Card id="bs-news" tabIndex={-1} aria-labelledby="bs-news-title">
              <SectionHeader
                level="card"
                as="h3"
                id="bs-news-title"
                title="News"
              />
              <p className="bs-meaning">{newsMeaning(newsGroups)}</p>
              <ToneHeadlineGroups
                groups={newsGroups}
                onSource={onSource}
                reading={reading}
                includeUnrated
              />
            </Card>
            <Card
              id="bs-people"
              tabIndex={-1}
              aria-labelledby="bs-people-title"
            >
              <SectionHeader
                level="card"
                as="h3"
                id="bs-people-title"
                title="People online"
              />
              <p className="bs-meaning">{peopleMeaning(postGroups)}</p>
              <ToneHeadlineGroups
                groups={postGroups}
                onSource={onSource}
                reading={reading}
                social
                includeUnrated
              />
            </Card>
          </div>
          <WorldSignalCard
            links={links}
            worldState={worldState}
            onWorld={onWorld}
            limit={2}
          />
          <YourViewCard
            savedView={savedView}
            name={name}
            onSaveView={onSaveView}
          />
        </>
      )}
      <LatestActivity
        data={data}
        instrumentId={instrumentId}
        onUpdates={onUpdates}
        onView={onView}
        onSource={onSource}
      />
      {!data.financials_pending && (
        <OverviewSections
          data={data}
          instrumentId={instrumentId}
          visible={visible}
          onView={onView}
          businessPanel={businessPanel}
          briefOpen={briefOpen}
          onBriefToggle={setBriefOpen}
        />
      )}
      <Disclosure
        title="Price chart · past year"
        description="Saved prices; choose Refresh prices inside for a newer check"
      >
        {chart}
      </Disclosure>
      <p className="bs-note">
        These readings help investigate the business, not whether to buy or
        sell.
      </p>
    </section>
  );
}
