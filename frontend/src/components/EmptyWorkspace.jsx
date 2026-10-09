import { useState } from "react";
import CompanyDialog from "./CompanyDialog";
import TelegramSettings from "./TelegramSettings";

export default function EmptyWorkspace({ view, onChoose }) {
  const [adding, setAdding] = useState(false);
  const copy = {
    workspace: [
      "Start with a company you’re curious about",
      "Bring its news, financials and market expectations into one research workspace.",
    ],
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
  const [title, description] = copy[view] || copy.workspace;
  return (
    <div className="app-shell all-companies-view empty-app">
      <header className="topbar">
        <a className="brand" href="/">
          thesis<span>↗</span>
        </a>
        <nav aria-label="Workspace navigation">
          {[
            ["workspace", "Workspace"],
            ["ideas", "My ideas"],
            ["updates", "Updates"],
            ["history", "History"],
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
        onAdded={(id) => {
          setAdding(false);
          onChoose(id);
        }}
      />
    </div>
  );
}
