import UiPreview from "../../frontend/src/components/ui/UiPreview";
// Authored page fixtures. API methods below are in-memory fakes only.
import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import WorldNews from "../../frontend/src/components/WorldNews";
import UpdateInbox from "../../frontend/src/components/UpdateInbox";
import Modal from "../../frontend/src/components/Modal";
import { ProfileContext } from "../../frontend/src/lib/profile";
import { api } from "../../frontend/src/api/client";
import "../../frontend/src/styles/tokens.css";
import "../../frontend/src/styles/app.css";
import "../../frontend/src/components/ContentFirstLayout.css";
import "../../frontend/src/components/ReadingFlow.css";
import "../../frontend/src/styles/mobile.css";
import "../../frontend/src/styles/header.css";
import "../../frontend/src/components/NewsDiscussionLayout.css";

window.actions = [];
window.pending = [];
let options = {},
  reviews = {};
const emit = (kind, extra = {}) => window.actions.push({ kind, ...extra });
const stamp = "2026-10-25T08:00:00Z";
const company = {
  id: "c1",
  symbol: "EXMP",
  name: "Example Company",
  mode: "sec",
  coverage: { concerns: [], watch: { enabled: true, interval_minutes: 60 } },
};
const articles = [
  {
    id: "w1",
    headline: "Central bank holds interest rates steady",
    summary:
      "The central bank left its benchmark rate unchanged. Exact supplied text: <script>untrusted</script>.",
    publisher: "Example Wire",
    published_at: stamp,
    themes: ["rates"],
    mentions: ["c1"],
    links: [
      {
        company_id: "c1",
        symbol: "EXMP",
        effect: "mixed_or_unclear",
        reason:
          "Financing costs may stay unchanged; the company’s response is unknown.",
      },
    ],
  },
  {
    id: "w2",
    headline: "New trade rules announced for chip exports",
    summary:
      "The report describes proposed export rules; their company effects are not established.",
    publisher: "Example Business",
    published_at: stamp,
    themes: ["trade"],
    mentions: [],
    links: [],
  },
  {
    id: "w3",
    headline: "Energy prices rise after supply disruption",
    summary: "Supply disruption is reported. Future prices remain uncertain.",
    publisher: "Example Markets",
    published_at: stamp,
    themes: ["energy"],
    mentions: [],
    links: [
      {
        company_id: "c1",
        symbol: "EXMP",
        effect: "could_hurt",
        reason: "Higher energy costs could affect operating costs.",
      },
    ],
  },
].map((a) => ({ ...a, url: `https://example.test/${a.id}` }));
function world() {
  return {
    configured: options.configured !== false,
    can_refresh: true,
    stale: !!options.stale,
    articles: options.empty ? [] : articles,
    companies: [company],
    themes: [
      { id: "rates", label: "Rates" },
      { id: "trade", label: "Trade" },
      { id: "energy", label: "Energy" },
      { id: "regulation", label: "Regulation" },
    ],
    checked_at: stamp,
    ai: { available: !!options.ai },
    check: options.checked ? { checked_at: stamp } : null,
  };
}
api.worldNews = async () => {
  emit("world-read");
  if (options.error) throw new Error("Authored world read failure.");
  return world();
};
api.refreshWorldNews = async () => {
  emit("world-refresh");
  if (options.refreshError) throw new Error("Authored refresh failure.");
  return { ...world(), stale: false };
};
api.checkWorldNews = async () => {
  emit("world-check");
  options.checked = true;
  return world();
};
const source = {
  id: "s1",
  kind: "news",
  source: "Example Wire",
  published_at: stamp,
  title: "Example Company opens a new facility",
  body: "Example Company announced a new facility. <script>Untrusted text stays escaped.</script>",
  url: "https://example.test/s1",
};
function companyRecord(n) {
  const id = `r${n}`,
    action = reviews[id] || null;
  return {
    kind: "company",
    id,
    created_at: stamp,
    title: "Company development",
    review_action: action,
    feedback_enabled: true,
    detail: {
      id,
      instrument_id: "c1",
      symbol: "EXMP",
      created_at: stamp,
      review_action: action,
      previous_items: [],
      previous_sources: [],
      sources: [source],
      payload: {
        title: "Company development",
        reason: "A new report is available.",
        previous_cutoff: stamp,
        items: [
          {
            id: `i${n}`,
            source_id: "s1",
            sentiment: "neutral",
            statement: "reported_development",
            explanation: "Authored interpretation.",
            evidence_policy: "authored",
            citations: [{ source_id: "s1", quote: source.body }],
          },
        ],
      },
    },
  };
}
function records() {
  return [
    companyRecord(1),
    {
      ...companyRecord(2),
      detail: {
        ...companyRecord(2).detail,
        withheld: true,
        sources: [],
        payload: {},
      },
    },
    companyRecord(3),
  ];
}
api.researchReview = async (filters) => {
  emit("inbox-read", { filters });
  if (options.inboxError) throw new Error("Authored inbox read failure.");
  let rows = options.empty ? [] : records();
  if (filters.review !== "all")
    rows = rows.filter((r) =>
      filters.review === "pending"
        ? !r.review_action
        : r.review_action === filters.review,
    );
  const value = {
    instrument_id: filters.instrument_id || null,
    review: filters.review,
    page: filters.page,
    page_size: 2,
    cutoff: stamp,
    total: rows.length,
    records: rows.slice(filters.page * 2, filters.page * 2 + 2),
    companies: [company],
    daily_reports_enabled: true,
  };
  if (options.delay)
    return new Promise((resolve) => window.pending.push(() => resolve(value)));
  return value;
};
api.reviewAlert = async (id, action) => {
  emit("review", { id, action });
  reviews[id] = action;
};
api.rateAlert = async (kind, id, value) => {
  emit("rate", { alertKind: kind, id, value });
  return { value };
};
api.dailyUpdates = async () => {
  emit("daily-read");
  return {
    enabled: true,
    digests: [{ id: "daily1", window_end: stamp, total: 1, preview: false }],
    today_spend: null,
    spending: [],
    notices: [],
  };
};
api.dailyDigest = async (id, page) => {
  emit("daily-open");
  return {
    id,
    page,
    page_size: 20,
    total: 1,
    window_start: stamp,
    window_end: stamp,
    limitation: "Authored saved recap.",
    records: [companyRecord(1)],
  };
};
function Fixture({ view }) {
  const [filters, setFilters] = useState({
    company: "",
    review: "all",
    page: 0,
    cutoff: "",
  });
  const [open, setOpen] = useState(false);
  if (view === "ui") return <UiPreview />;
  return (
    <ProfileContext.Provider
      value={{ mode: options.beginner ? "explain" : "data" }}
    >
      <div className="app-shell" style={{ display: "block" }}>
        {view === "world" ? (
          <WorldNews active onOpenCompany={(id) => emit("navigate", { id })} />
        ) : (
          <div className="workspace-page">
            <UpdateInbox
              filters={filters}
              onFiltersChange={setFilters}
              catalogue={[company]}
              onOpen={(id, view) => emit("navigate", { id, view })}
              onSource={() => setOpen(true)}
              onReviewed={async () => emit("badge-read")}
              onWeeklyReview={() => emit("weekly-open")}
              unseenReviews={2}
            />
          </div>
        )}
        <Modal
          open={open}
          onClose={() => setOpen(false)}
          title="Original source"
        >
          <p>{source.body}</p>
        </Modal>
      </div>
    </ProfileContext.Provider>
  );
}
const root = createRoot(document.getElementById("root"));
let serial = 0;
window.show = (view, next = {}) => {
  options = next;
  reviews = {};
  root.render(<Fixture key={++serial} view={view} />);
};
window.options = (patch) => {
  options = { ...options, ...patch };
};
window.show("world");
