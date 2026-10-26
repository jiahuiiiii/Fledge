import TermHelp from "./TermHelp";
import { plainSales, plainMargin, plainCash, plainForecast } from "../lib/plainTabs";
import "./PlainTabs.css";

// The first thing anyone sees on the Financials tab: a few figures in plain
// English. The charts and filings stay behind "Show full details".
export default function PlainFinancials({ name, active, previous, management, annual }) {
  const span = annual ? "last financial year" : "last 12 months";
  const sales = plainSales(active, previous, name);
  const cards = [
    sales && {
      ...sales,
      label: `Sales (revenue), ${span}`,
      term: "revenue",
    },
    plainMargin(active, name) && {
      ...plainMargin(active, name),
      label: "Profit kept from each $1 of sales",
      term: "operating_margin",
    },
    plainCash(active, name) && {
      ...plainCash(active, name),
      label: `Cash left over, ${span}`,
      term: "free_cash_flow",
    },
    plainForecast(management) && {
      ...plainForecast(management),
      label: "What the company expects next",
      term: "guidance",
    },
  ].filter(Boolean);
  return (
    <section className="plain-tab" aria-label="Financials in plain English">
      <p className="plain-intro">
        <strong>How the business is doing</strong>, from the reports {name} must
        file with US regulators. Tap <span className="plain-q">?</span> to see
        what a word means.
      </p>
      {cards.length === 0 && (
        <p className="plain-empty">
          No figures saved yet. Use Update at the top of the page to collect them.
        </p>
      )}
      {cards.map((card) => (
        <article className="plain-figure" key={card.key}>
          <p className="plain-label">
            {card.label} <TermHelp term={card.term} />
          </p>
          <p className={`plain-value${card.key === "forecast" ? " small" : ""}`}>
            {card.value}
            {card.change != null && Math.abs(card.change) >= 1 && (
              <span className={card.change > 0 ? "plain-up" : "plain-down"}>
                {" "}
                {card.change > 0 ? "▲" : "▼"} {Math.abs(card.change).toFixed(0)}%
              </span>
            )}
          </p>
          {card.period && <p className="plain-period">{card.period}</p>}
          <p className="plain-text">{card.text}</p>
        </article>
      ))}
      <p className="plain-note">
        This explains the business; it isn’t a reason to buy or sell.
      </p>
    </section>
  );
}
