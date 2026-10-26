// Authored session and readings. Every API method used here is a fake.
import React from "react";
import { createRoot } from "react-dom/client";
import App from "../../frontend/src/App";
import BeginnerSummary from "../../frontend/src/components/BeginnerSummary";
import { ResearchSectionHeader } from "../../frontend/src/components/ResearchNavigation";
import { ProfileContext } from "../../frontend/src/lib/profile";
import { api } from "../../frontend/src/api/client";
import "../../frontend/src/styles/tokens.css";
import "../../frontend/src/styles/app.css";
import "../../frontend/src/components/ContentFirstLayout.css";
import "../../frontend/src/components/ReadingFlow.css";
import "../../frontend/src/styles/mobile.css";
import "../../frontend/src/styles/header.css";
import "../../frontend/src/components/ResearchNavigation.css";
import "../../frontend/src/components/NewsDiscussionLayout.css";
localStorage.setItem("fledge:has-account", "1");
window.actions = [];
const log = (kind, extra = {}) => window.actions.push({ kind, ...extra });
let authenticated = true,
  hasCode = false,
  mode = "data";
const profile = () => ({
  completed: true,
  investor_type: "long_term",
  detail_mode: mode,
});
api.session = async () => {
  log("session");
  return {
    authenticated,
    account_id: "authored-account",
    mode: "password",
    username: "exampleuser",
    has_recovery_code: hasCode,
    terms: { accepted: true },
  };
};
api.home = async () => {
  log("home");
  return { profile: profile(), detail_mode: mode };
};
api.saveDetailMode = async (next) => {
  log("mode", { value: next });
  mode = next;
  return profile();
};
api.workspace = () => {
  log("workspace");
  return new Promise(() => {});
};
api.telegram = async () => ({
  configured: false,
  linked: false,
  deliveries: [],
  watches: 0,
});
api.logout = async () => {
  log("logout");
  authenticated = false;
};
api.changePassword = async () => {
  log("password");
};
api.newRecoveryCode = async () => {
  log("recovery");
  hasCode = true;
  return { recovery_code: "AUTHORED-EXAMPLE-CODE" };
};
const stamp = "2026-10-25T08:00:00Z";
const sources = ["news", "social"].flatMap((kind) =>
  ["positive", "negative", "mixed", "neutral"].map((tone) => ({
    id: `${kind}-${tone}`,
    kind,
    platform: kind === "social" ? "reddit" : null,
    title: `Example ${kind} ${tone} headline`,
    body: "Exact authored text for layout review.",
    source: "Example publisher",
    published_at: stamp,
  })),
);
const data = {
  instrument: { id: "example", name: "Example Company", symbol: "EXMP" },
  market: {
    quote: {
      quote: { price: "100", change_percent: "-0.5", quoted_at: stamp },
    },
  },
  sentiment: {
    sources,
    items: sources.map((s) => ({
      source_id: s.id,
      relevance: "relevant",
      sentiment: s.id.split("-")[1],
    })),
  },
};
api.worldNews = async () => {
  log("world-read");
  return {
    ai: { available: false },
    articles: [
      {
        id: "world-1",
        headline: "Example world headline",
        publisher: "Example publisher",
        published_at: stamp,
        url: "https://example.test/world",
        links: [
          {
            company_id: "example",
            effect: "could_help",
            reason: "Authored possible effect.",
          },
        ],
      },
    ],
  };
};
const root = createRoot(document.getElementById("root"));
window.showSummary = () =>
  root.render(
    <ProfileContext.Provider value={{ mode: "data" }}>
      <div className="app-shell" style={{ display: "block", padding: 16 }}>
        <main
          className="research-content"
          style={{ maxWidth: 1180, margin: "auto", padding: 0 }}
        >
          <ResearchSectionHeader selected="summary" />
          <BeginnerSummary
            data={data}
            instrumentId="example"
            visible
            onSource={() => log("source")}
          />
        </main>
      </div>
    </ProfileContext.Provider>,
  );
root.render(<App />);
