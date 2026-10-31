import { useEffect, useState } from "react";
import { Button } from "./ui";
import { api } from "../api/client";
import TermHelp from "./TermHelp";
import { companyName } from "../lib/companyIdentity";
import {
  reportedRow,
  peRows,
  comparisonExclusion,
} from "../lib/sectorPosition";
import {
  compareVerdicts,
  formatGrowth,
  formatMargin,
  formatPe,
} from "../lib/plainTabs";
import "./PlainTabs.css";

function Bold({ text }) {
  return text
    .split("**")
    .map((part, i) => (i % 2 ? <b key={i}>{part}</b> : part));
}

// "Amazon.com, Inc." -> "Amazon", "MICROSOFT CORP" -> "Microsoft".
export function shortName(name, symbol) {
  let n = (name || symbol || "").replace(
    /,?\s+(inc|corp|corporation|co|ltd|plc|holdings|group|n\.?v|s\.?a)\.?$/i,
    "",
  );
  n = n.replace(/\.com$/i, "").trim();
  if (n === n.toUpperCase() && /[A-Z]{3}/.test(n))
    n = n.toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
  return n || symbol;
}

// Saved peer figures turned into a few plain sentences and a small table.
export function compareRows(data) {
  const members = data?.members || [];
  const pick = (key) => {
    const rows = members.map((m) => reportedRow(m, key));
    const own = rows.find((r) => r.symbol === data.symbol);
    return Object.fromEntries(
      rows.map((r) => [r.symbol, comparisonExclusion(r, own) ? null : r.value]),
    );
  };
  const growth = pick("revenue_growth"),
    margin = pick("operating_margin");
  const pe = Object.fromEntries(
    peRows(members, data?.references || []).map((r) => [
      r.symbol,
      comparisonExclusion(r, null) ? null : r.value,
    ]),
  );
  const ordered = [
    ...members.filter((m) => m.symbol === data.symbol),
    ...members.filter((m) => m.symbol !== data.symbol),
  ];
  return ordered.map((m) => ({
    symbol: m.symbol,
    name: shortName(companyName({ symbol: m.symbol, name: m.name }), m.symbol),
    growth: growth[m.symbol] ?? null,
    margin: margin[m.symbol] ?? null,
    pe: pe[m.symbol] ?? null,
  }));
}

export default function PlainCompare({
  instrumentId,
  name,
  visible,
  onChoosePeers,
}) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!visible) return;
    let live = true;
    Promise.all([
      api.sectorPosition(instrumentId),
      api
        .valuationContext(instrumentId)
        .then((v) => v.references || [])
        .catch(() => []),
    ])
      .then(([position, references]) => {
        if (live) {
          setData({ ...position, references });
          setError("");
        }
      })
      .catch((failure) => live && setError(failure.message));
    return () => {
      live = false;
    };
  }, [instrumentId, visible]);
  const rows = data ? compareRows(data) : [];
  const peers = rows.slice(1);
  const verdicts = compareVerdicts(rows);
  const hasFigures = peers.some(
    (r) => r.growth != null || r.margin != null || r.pe != null,
  );
  return (
    <section className="plain-tab" aria-label="Comparison in plain English">
      <p className="plain-intro">
        <strong>How {name} stacks up</strong> against similar companies, so the
        numbers mean something.
      </p>
      {error && <p role="alert">{error}</p>}
      {!data && !error && (
        <p className="plain-empty">Loading similar companies…</p>
      )}
      {data && !peers.length && (
        <div className="plain-empty">
          <p>No similar companies picked yet.</p>
          <Button variant="primary" onClick={onChoosePeers}>
            Pick companies to compare
          </Button>
        </div>
      )}
      {data && peers.length > 0 && !hasFigures && (
        <div className="plain-empty">
          <p>
            Figures for {peers.map((p) => p.name).join(", ")} aren’t saved yet.
          </p>
          <Button variant="primary" onClick={onChoosePeers}>
            Get their figures
          </Button>
        </div>
      )}
      {verdicts.map((v) => (
        <p className={`plain-verdict tone-${v.tone}`} key={v.key}>
          <Bold text={v.text} />
          {v.key === "pe" && <TermHelp term="pe" />}
        </p>
      ))}
      {hasFigures && (
        <div className="plain-table-wrap">
          <table className="plain-table">
            <thead>
              <tr>
                <th scope="col">Company</th>
                <th scope="col">Sales growth</th>
                <th scope="col">Profit per $1</th>
                <th scope="col">
                  Price vs profit <TermHelp term="pe" />
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={r.symbol} className={i === 0 ? "me" : ""}>
                  <th scope="row">{r.name}</th>
                  <td>{formatGrowth(r.growth)}</td>
                  <td>{formatMargin(r.margin)}</td>
                  <td>{formatPe(r.pe)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {verdicts.some((v) => v.key === "pe") && (
        <p className="plain-note">
          “Pricier” isn’t good or bad: it shows how much other investors already
          expect.
        </p>
      )}
      {peers.length > 0 && (
        <button
          type="button"
          className="source-link plain-change"
          onClick={onChoosePeers}
        >
          Change companies →
        </button>
      )}
    </section>
  );
}
