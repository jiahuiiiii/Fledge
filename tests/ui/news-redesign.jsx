// Authored, offline UI fixture. No saved workspace or provider access.
import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import ResearchNavigation, {
  ResearchSectionHeader,
} from "../../frontend/src/components/ResearchNavigation";
import MarketResearch from "../../frontend/src/components/MarketResearch";
import SentimentPanel from "../../frontend/src/components/SentimentPanel";
import RetainedView from "../../frontend/src/components/RetainedView";
import Modal from "../../frontend/src/components/Modal";
import "../../frontend/src/styles/tokens.css";
import "../../frontend/src/styles/app.css";
import "../../frontend/src/components/ContentFirstLayout.css";
import "../../frontend/src/components/ReadingFlow.css";
import "../../frontend/src/styles/mobile.css";
import "../../frontend/src/styles/header.css";
import "../../frontend/src/components/ResearchNavigation.css";
import "../../frontend/src/components/NewsDiscussionLayout.css";

const sources = Array.from({ length: 10 }, (_, n) => ({
  id: `news-${n}`,
  kind: "news",
  source: n % 2 ? "Example Business" : "Example News",
  title:
    [
      "Northstar announces a new manufacturing facility",
      "Northstar reports quarterly revenue growth",
      "Northstar outlines investment plans for next year",
    ][n % 3] + (n > 2 ? ` · report ${n}` : ""),
  body: "Northstar described its latest plans in a company statement. The supplied excerpt does not establish how these plans will affect future earnings. This exact authored text remains available in the evidence dialog.",
  published_at: `2026-10-${String(25 - n).padStart(2, "0")}T08:00:00Z`,
  url: `https://example.test/news/${n}`,
}));
const social = {
  ...sources[0],
  id: "social-0",
  kind: "social",
  platform: "reddit",
  source: "r/example",
  title: "Reddit comment",
  body: "I am worried about the cost of Northstar’s planned expansion. This is one author’s opinion, not a reported result.",
};
const sample = {
  selected: 10,
  relevant: 10,
  tone: "neutral",
  counted_groups: 10,
  counts: { positive: 0, neutral: 6, negative: 4, mixed: 0, unclear: 0 },
};
const base = {
  instrument: {
    id: "authored",
    name: "Northstar",
    symbol: "NSTR",
    mode: "sec",
  },
  documents: sources,
  market_news_ids: sources.map((s) => s.id),
  versions: [],
  provider_status: [
    {
      provider: "finnhub",
      channel: "news",
      label: "Example news provider",
      status: "ready",
      checked_at: "2026-10-25T08:05:00Z",
    },
  ],
  news_watch: { enabled: false },
  sentiment: {
    id: "authored-reading",
    created_at: "2026-10-25T08:10:00Z",
    cutoff: "2026-10-25T08:05:00Z",
    social_lookback_days: 7,
    summary_policy: "sentiment-coverage-1",
    sources: [...sources, social],
    coverage_links: [],
    items: [...sources, social].map((s, n) => ({
      id: `label-${n}`,
      source_id: s.id,
      channel: s.kind,
      relevance: "relevant",
      sentiment: n % 3 === 0 ? "negative" : "neutral",
      statement: s.kind === "news" ? "reported_development" : "opinion",
      explanation: "Authored interpretation; inspect the original wording.",
      citations: [{ quote: s.body }],
    })),
    summary: {
      news: sample,
      social_platforms: {
        reddit: {
          selected: 1,
          relevant: 1,
          tone: "thin sample",
          counts: { negative: 1 },
        },
      },
    },
    coverage: {
      available_news: 10,
      social_platforms: { reddit: 1, hackernews: 0, x: 0 },
      selection: { policy: "sentiment-all-eligible-1" },
    },
  },
};
function Fixture() {
  const [tab, setTab] = useState("evidence"),
    [state, setState] = useState("saved"),
    [source, setSource] = useState(null);
  const data =
    state === "empty"
      ? { ...base, sentiment: null, documents: [], market_news_ids: [] }
      : state === "withheld"
        ? {
            ...base,
            sentiment: {
              ...base.sentiment,
              withheld: true,
              sources: [],
              items: [],
              summary: {},
            },
          }
        : state === "stale"
          ? {
              ...base,
              sentiment: {
                ...base.sentiment,
                stale: true,
                earlier_method: true,
              },
              provider_status: [
                {
                  provider: "finnhub",
                  channel: "news",
                  label: "Example news provider",
                  status: "failed",
                  message: "Authored unavailable source",
                  checked_at: "2026-10-25T08:05:00Z",
                },
              ],
            }
          : base;
  return (
    <div className="app-shell" style={{ display: "block", minHeight: "100vh" }}>
      <main
        className="workspace-page"
        style={{ padding: "24px 16px", margin: "0 auto", maxWidth: 1180 }}
      >
        <label>
          Fixture state{" "}
          <select
            aria-label="Fixture state"
            value={state}
            onChange={(e) => setState(e.target.value)}
          >
            {["saved", "empty", "withheld", "stale"].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </label>
        <div className="research-browser">
          <ResearchNavigation selected={tab} onChange={setTab} />
          <section
            className="research-content"
            role="tabpanel"
            id="research-panel"
            tabIndex={0}
            aria-labelledby={`research-tab-${tab}`}
          >
            <ResearchSectionHeader selected={tab} />
            <RetainedView active={tab === "evidence"}>
              <MarketResearch
                data={data}
                modelStatus={{ briefing_enabled: false }}
                onSource={(id) => setSource(sources.find((s) => s.id === id))}
              />
              <SentimentPanel
                key={state}
                data={data}
                modelStatus={{ briefing_enabled: false }}
                onSource={() => {}}
              />
              <MarketResearch
                data={data}
                headlinesOnly
                onSource={(id) => setSource(sources.find((s) => s.id === id))}
              />
            </RetainedView>
            {tab !== "evidence" && <p>{tab} retained view placeholder</p>}
          </section>
        </div>
        <Modal
          open={!!source}
          onClose={() => setSource(null)}
          title="Original story"
        >
          <p>{source?.body}</p>
        </Modal>
      </main>
    </div>
  );
}
createRoot(document.getElementById("root")).render(<Fixture />);
