import { useEffect, useState } from "react";
import CompanyDialog from "./CompanyDialog";
import TelegramSettings from "./TelegramSettings";
import { companionPromise } from "../lib/companion";
import { useProfile } from "../lib/profile";
import { api } from "../api/client";


export default function EmptyWorkspace({ view, onChoose }) {
  const [adding, setAdding] = useState(false);
  const [notice, setNotice] = useState("");
  const { home } = useProfile();
  useEffect(() => {
    const openAdd = () => setAdding(true);
    if (window.fledgeOpenAddCompany) {
      window.fledgeOpenAddCompany = false;
      openAdd();
    }
    addEventListener("fledge:open-add-company", openAdd);
    return () => removeEventListener("fledge:open-add-company", openAdd);
  }, []);
  const personal = home?.profile?.completed ? home : null;
  const copy = {
    workspace: ["Start with a company you’re curious about", companionPromise],
    ideas: [
      "Your investment ideas start here",
      "Add a company, explore the evidence, then save the reasoning you want to test.",
    ],
    updates: [
      "No updates yet",
      "Add a company and set up a watch when you’re ready. Relevant changes will appear here.",
    ],
    history: [
      "A clean research history",
      "Your saved questions, analysis and idea revisions will appear here as you explore.",
    ],
  };
  const [title, description] =
    personal && (view === "workspace" || !copy[view])
      ? [personal.headline, personal.next_step.label]
      : copy[view] || copy.workspace;
  return (
    <div className="app-shell all-companies-view empty-app">
      <header className="topbar">
        <a className="brand" href="/">
          fledge<span>↗</span>
        </a>
        <nav aria-label="Workspace navigation">
          {[
            ["workspace", "Home"],
            ["ideas", "My views"],
            ["updates", "Updates"],
          ].map(([id, label]) => (
            <button
              key={id}
              className={view === id ? "active" : ""}
              aria-current={view === id ? "page" : undefined}
              onClick={() => onChoose("", id)}
            >
              {label}
            </button>
          ))}
        </nav>
        <TelegramSettings />
      </header>
      <main className="empty-workspace">
        <span className="section-label">YOUR RESEARCH WORKSPACE</span>
        <h1>{title}</h1>
        <p>{description}</p>
        <p className="fine">
          Pick a company you own or want to understand. You don’t need a
          position to start.
        </p>
        {personal?.interests?.length > 0 && (
          <p className="fine personal-interests">
            You told us you’re interested in{" "}
            {personal.interests.map((item) => item.label).join(", ")}. Search
            for a company in these areas, or anything else you’re curious
            about.
          </p>
        )}
        {personal && (
          <p className="fine">
            Your watchlist: {personal.watchlist.count} of{" "}
            {personal.watchlist.limit} companies.
          </p>
        )}
        {notice && (
          <p className="watchlist-notice" role="alert">
            {notice}
          </p>
        )}
        <button className="primary" onClick={() => setAdding(true)}>
          Add your first company <span aria-hidden="true">＋</span>
        </button>
        <div className="empty-journey">
          <div>
            <strong>01 · Explore the evidence</strong>
            <p>
              Read news and filings. Keep reported facts separate from
              expectations.
            </p>
          </div>
          <div>
            <strong>02 · Write your idea</strong>
            <p>Save your reasoning and what would change your mind.</p>
          </div>
          <div>
            <strong>03 · Follow what changes</strong>
            <p>Review new sources and alerts against your original idea.</p>
          </div>
        </div>
      </main>
      <CompanyDialog
        open={adding}
        onClose={() => setAdding(false)}
        onAdded={async (id) => {
          // Save the first company to the watchlist before opening it.
          try {
            await api.addToWatchlist(id);
            setNotice("");
          } catch (failure) {
            setNotice(failure.message);
          }
          dispatchEvent(new Event("fledge:home-changed"));
          setAdding(false);
          onChoose(id);
        }}
      />
    </div>
  );
}
