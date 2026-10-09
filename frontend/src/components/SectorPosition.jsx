import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import Select from "./Select";
import EvidenceButton from "./EvidenceButton";
import LoadingSkeleton from "./LoadingSkeleton";
import { money, percent, day } from "../lib/financialStory";
import {
  measures,
  reportedRow,
  forecastRow,
  yearsFor,
  position,
  scale,
  managementRows,
} from "../lib/sectorPosition";
import "./SectorPosition.css";
const stamp = (value) =>
  value ? new Date(value).toLocaleString("en-GB") : "Not established";
const display = (value, unit) =>
  value == null
    ? "Unavailable"
    : unit === "USD"
      ? money(value)
      : percent(value);
function Evidence({ row, expected }) {
  return (
    <EvidenceButton
      title={`${row.symbol} · ${expected ? "forecast growth" : row.row?.label || "reported figure"}`}
    >
      {expected ? (
        <>
          <p>
            FMP annual revenue averages: {row.current?.average ?? "Unavailable"}{" "}
            USD for year ending {row.end || "unknown"}, versus{" "}
            {row.baseline?.average ?? "Unavailable"} USD for year ending{" "}
            {row.priorEnd || "unknown"}.
          </p>
          <p>
            Calculation: (current forecast average / preceding forecast average
            − 1) × 100. Both inputs are forecasts from the same saved response.
          </p>
          <p>
            Source snapshot {row.sourceId || "unavailable"} · first observed{" "}
            {stamp(row.observed)}. Underlying forecast vintage is unknown.
          </p>
        </>
      ) : (
        <>
          <p>
            {row.row?.formula || "Reported revenue, without a new calculation."}
          </p>
          <p>
            Exact value: {row.exact ?? "Unavailable"} {row.unit}. Annual period{" "}
            {day(row.start)} – {day(row.end)}.
          </p>
          {row.inputs.map((input, i) => (
            <p key={i}>
              {input.namespace}:{input.concept} · exact {input.value}{" "}
              {input.unit} · {day(input.start)} – {day(input.end)} · filing{" "}
              {input.accession}.
            </p>
          ))}
          {row.report?.filing_url && (
            <a href={row.report.filing_url} target="_blank" rel="noreferrer">
              Original annual filing ↗
            </a>
          )}
        </>
      )}
      {row.reason && <p>{row.reason}</p>}
    </EvidenceButton>
  );
}
function Bars({ rows, symbol, expected }) {
  const range = scale(rows);
  return (
    <div className="position-bars">
      {rows.map((row) => (
        <article
          key={row.symbol}
          className={`position-bar-row ${row.symbol === symbol ? "is-company" : ""}`}
        >
          <div className="position-bar-heading">
            <div>
              <strong>{row.symbol}</strong>
              <small>
                {row.symbol === symbol
                  ? "Company you’re researching"
                  : row.name}
              </small>
            </div>
            <strong>{display(row.value, row.unit)}</strong>
          </div>
          {row.value != null ? (
            <div
              className="position-track"
              role="img"
              aria-label={`${row.symbol}: ${display(row.value, row.unit)}`}
            >
              <i style={{ left: `${(-range.low / range.span) * 100}%` }} />
              <span
                style={{
                  left: `${((Math.min(0, row.value) - range.low) / range.span) * 100}%`,
                  width: `${(Math.abs(row.value) / range.span) * 100}%`,
                }}
              />
            </div>
          ) : (
            <p className="position-gap">{row.reason}</p>
          )}
          <div className="position-bar-foot">
            <small>
              {expected
                ? `Forecast year ends ${day(row.end)}`
                : `${day(row.start)} – ${day(row.end)}`}
            </small>
            <Evidence row={row} expected={expected} />
          </div>
        </article>
      ))}
    </div>
  );
}
function Map({ members, symbol }) {
  const rows = members.map((member) => ({
    growth: reportedRow(member, "revenue_growth"),
    margin: reportedRow(member, "operating_margin"),
  }));
  const valid = rows.filter(
    (r) =>
      r.growth.value != null &&
      r.margin.value != null &&
      r.growth.start === r.margin.start &&
      r.growth.end === r.margin.end,
  );
  const xs = scale(valid.map((r) => r.growth)),
    ys = scale(valid.map((r) => r.margin));
  const x = (v) => 72 + ((v - xs.low) / xs.span) * 530,
    y = (v) => 270 - ((v - ys.low) / ys.span) * 218;
  return (
    <div className="position-map-wrap">
      <h3>Growth and profitability together</h3>
      <p>
        Further right means faster annual sales growth. Higher means a larger
        reported operating margin.
      </p>
      {valid.length >= 2 ? (
        <>
          <div
            className="position-map-viewport"
            tabIndex={0}
            role="region"
            aria-label="Growth and profitability map"
          >
            <svg
              viewBox="0 0 660 320"
              role="img"
              aria-label="Annual revenue growth against reported GAAP operating margin for the chosen competitors"
            >
              {[0, 0.5, 1].map((f) => (
                <g key={f} className="position-grid">
                  <line x1="72" x2="602" y1={52 + 218 * f} y2={52 + 218 * f} />
                  <text x="62" y={56 + 218 * f} textAnchor="end">
                    {percent(ys.high - ys.span * f)}
                  </text>
                  <line x1={72 + 530 * f} x2={72 + 530 * f} y1="52" y2="270" />
                  <text x={72 + 530 * f} y="292" textAnchor="middle">
                    {percent(xs.low + xs.span * f)}
                  </text>
                </g>
              ))}
              <text
                className="position-axis"
                x="337"
                y="317"
                textAnchor="middle"
              >
                Annual revenue growth →
              </text>
              <text className="position-axis" x="72" y="24">
                Reported operating margin ↑
              </text>
              {valid.map((r) => (
                <g
                  key={r.growth.symbol}
                  className={
                    r.growth.symbol === symbol
                      ? "position-dot selected"
                      : "position-dot"
                  }
                >
                  <title>
                    {r.growth.symbol}: growth {percent(r.growth.value)},
                    operating margin {percent(r.margin.value)}, year ending{" "}
                    {r.growth.end}
                  </title>
                  <circle
                    cx={x(r.growth.value)}
                    cy={y(r.margin.value)}
                    r={r.growth.symbol === symbol ? 8 : 6}
                  />
                  <text
                    x={x(r.growth.value)}
                    y={y(r.margin.value) - 16}
                    textAnchor="middle"
                  >
                    {r.growth.symbol}
                  </text>
                </g>
              ))}
            </svg>
          </div>
          <p className="position-caption">
            {valid.length} of {members.length} companies have both figures. Each
            uses its own fiscal year; dates and exact sources are in the
            comparisons below.
          </p>
        </>
      ) : (
        <p className="position-gap">
          At least two companies need both annual growth and operating margin to
          plot their positions.
        </p>
      )}
    </div>
  );
}
export default function SectorPosition({
  instrumentId,
  visible,
  financials = false,
}) {
  const [data, setData] = useState(null),
    [draft, setDraft] = useState(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [measure, setMeasure] = useState("revenue_growth"),
    [view, setView] = useState("reported"),
    [year, setYear] = useState(""),
    [search, setSearch] = useState(""),
    [searchResults, setSearchResults] = useState([]),
    [reasons, setReasons] = useState({});
  const version = useRef(0),
    mounted = useRef(true),
    dirty = useRef(false),
    searchVersion = useRef(0),
    acting = useRef(false),
    applied = useRef(undefined);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      version.current++;
    };
  }, []);
  async function load(peers, replaceDraft = false) {
    const token = ++version.current;
    setBusy(true);
    try {
      const next = await api.sectorPosition(instrumentId, peers);
      if (mounted.current && token === version.current) {
        setData(next);
        if (peers !== undefined) applied.current = peers;
        if (replaceDraft || !dirty.current) {
          setDraft(next.peers);
          setReasons(
            Object.fromEntries(
              next.members
                .filter((m) => m.symbol !== next.symbol)
                .map((m) => [
                  m.symbol,
                  m.rationale ||
                    "Compare whole-company growth and profitability; product mix may differ.",
                ]),
            ),
          );
          dirty.current = false;
        }
        setError("");
      }
    } catch (failure) {
      if (mounted.current && token === version.current)
        setError(failure.message);
    } finally {
      if (mounted.current && token === version.current) setBusy(false);
    }
  }
  useEffect(() => {
    if (visible && !acting.current) load(applied.current);
    return () => {
      version.current++;
    };
  }, [instrumentId, visible]);
  async function searchPeers(value) {
    setSearch(value);
    const token = ++searchVersion.current;
    if (!value.trim()) {
      setSearchResults([]);
      return;
    }
    try {
      const result = await api.companyDirectory(value);
      if (mounted.current && token === searchVersion.current)
        setSearchResults(
          result.companies.filter(
            (c) => c.available && c.symbol !== data.symbol,
          ),
        );
    } catch (failure) {
      if (mounted.current && token === searchVersion.current)
        setError(failure.message);
    }
  }
  async function save() {
    if (acting.current) return;
    acting.current = true;
    const token = ++version.current;
    setBusy(true);
    try {
      await api.savePeers(
        instrumentId,
        (draft || []).filter(Boolean).map((symbol) => ({
          symbol,
          rationale:
            reasons[symbol] ||
            "Compare whole-company growth and profitability; product mix may differ.",
        })),
      );
      if (mounted.current && token === version.current) {
        dirty.current = false;
        applied.current = undefined;
        await load(undefined, true);
      }
    } catch (failure) {
      if (mounted.current && token === version.current)
        setError(failure.message);
    } finally {
      acting.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  async function checkReported() {
    if (acting.current) return;
    acting.current = true;
    const token = ++version.current;
    setBusy(true);
    const failures = [];
    try {
      for (const member of data.members) {
        if (!mounted.current || token !== version.current) break;
        try {
          const company = await api.addSecCompany(member.symbol);
          await api.refreshSec(company.instrument_id);
        } catch (failure) {
          failures.push(`${member.symbol}: ${failure.message}`);
        }
      }
      if (mounted.current && token === version.current) {
        await load(data.peers);
        if (failures.length) setError(failures.join(" "));
      }
    } finally {
      acting.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  const candidates = [...(data?.candidates || []), ...searchResults].filter(
    (c, i, all) => all.findIndex((other) => other.symbol === c.symbol) === i,
  );
  const now = new Date().toISOString().slice(0, 10),
    years = yearsFor(data?.members || [], now),
    chosenYear = years.includes(year)
      ? year
      : years[0] || String(new Date().getFullYear() + 1);
  const expected = view === "expected",
    current = measures.find((m) => m.key === measure),
    rows = (data?.members || []).map((m) =>
      expected ? forecastRow(m, chosenYear, now) : reportedRow(m, measure),
    ),
    reading = position(rows, data?.symbol);
  return (
    <section className="sector-position" aria-label="Competitor position">
      <header className="outlook-section-heading">
        <h2>Where {data?.symbol || "the company"} stands among competitors</h2>
        <p>
          Compare growth, profitability and scale. The highlighted company is
          the one you’re researching.
        </p>
      </header>
      {error && (
        <p role="alert" className="warning">
          {error}
        </p>
      )}
      {!data && !error && (
        <LoadingSkeleton
          variant="panel"
          rows={3}
          label="Loading saved competitor comparisons…"
        />
      )}
      {data && (
        <>
          <details className="position-group">
            <summary>
              Comparison group · {data.symbol}
              {data.peers.length
                ? `, ${data.peers.join(", ")}`
                : " · choose peers"}
            </summary>
            <p>
              {data.basis === "suggested"
                ? "Default semiconductor comparison group. Broadcom’s software business and the peers’ different product mixes need context."
                : data.basis === "saved"
                  ? "Using your saved comparison companies."
                  : "Using the comparison group chosen for this view."}{" "}
              This is a selected group, not an average for the entire sector.
            </p>
            {data.suggestion_source && (
              <a href={data.suggestion_source} target="_blank" rel="noreferrer">
                Background: Broadcom’s disclosed semiconductor competitors ·
                2024 annual report ↗
              </a>
            )}
            <label className="position-search">
              Find another peer
              <input
                value={search}
                placeholder="Ticker or company name"
                onChange={(event) => searchPeers(event.target.value)}
              />
            </label>
            <div className="position-peer-editor">
              {Array.from(
                { length: Math.max(1, draft?.length || 0) },
                (_, i) => i,
              ).map((index) => (
                <label key={index}>
                  Competitor {index + 1}
                  <Select
                    aria-label={`Sector competitor ${index + 1}`}
                    value={draft?.[index] || ""}
                    disabled={busy}
                    onChange={(event) => {
                      dirty.current = true;
                      setDraft((old) => {
                        const next = [...(old || [])];
                        next[index] = event.target.value;
                        return next;
                      });
                    }}
                  >
                    <option value="">None</option>
                    {candidates
                      .filter(
                        (c) =>
                          c.symbol === draft?.[index] ||
                          !draft?.includes(c.symbol),
                      )
                      .map((c) => (
                        <option key={c.symbol} value={c.symbol}>
                          {c.symbol} · {c.name}
                        </option>
                      ))}
                  </Select>
                  {draft?.[index] && (
                    <textarea
                      aria-label={`Why compare ${draft[index]}`}
                      value={
                        reasons[draft[index]] ||
                        "Compare whole-company growth and profitability; product mix may differ."
                      }
                      minLength={8}
                      maxLength={600}
                      onChange={(event) => {
                        dirty.current = true;
                        setReasons((old) => ({
                          ...old,
                          [draft[index]]: event.target.value,
                        }));
                      }}
                    />
                  )}
                </label>
              ))}
            </div>
            <button
              disabled={busy}
              onClick={() => load((draft || []).filter(Boolean), true)}
            >
              {busy ? "Loading…" : "Apply comparison group"}
            </button>
            <button
              disabled={busy || (draft?.length || 0) >= 8}
              onClick={() => {
                dirty.current = true;
                setDraft((old) => [...(old || []), ""]);
              }}
            >
              Add peer
            </button>
            <button
              disabled={
                busy ||
                (draft || [])
                  .filter(Boolean)
                  .some(
                    (symbol) =>
                      (
                        reasons[symbol] ||
                        "Compare whole-company growth and profitability; product mix may differ."
                      ).trim().length < 8,
                  )
              }
              onClick={save}
            >
              {(draft || []).some(Boolean)
                ? "Save peers for this company"
                : "Restore default peer group"}
            </button>
            <p className="position-caption">
              Choose None to remove a peer. Apply previews saved data; Save
              keeps this peer group and the reasons shown above for this
              company. Clearing saved peers restores the default group.
            </p>
          </details>
          {!financials && (
            <div
              className="position-view"
              role="group"
              aria-label="Comparison time"
            >
              <button
                aria-pressed={!expected}
                onClick={() => setView("reported")}
              >
                Reported position
              </button>
              <button
                aria-pressed={expected}
                onClick={() => setView("expected")}
              >
                Expected growth
              </button>
            </div>
          )}
          {!expected && <Map members={data.members} symbol={data.symbol} />}
          <div className="position-measure">
            <h3>
              {expected
                ? "Whose sales are expected to grow faster?"
                : current.question}
            </h3>
            <label>
              {expected ? "Forecast year ending in" : "Compare"}
              <Select
                aria-label={
                  expected ? "Competitor forecast year" : "Competitor measure"
                }
                value={expected ? chosenYear : measure}
                onChange={(event) =>
                  expected
                    ? setYear(event.target.value)
                    : setMeasure(event.target.value)
                }
              >
                {expected
                  ? (years.length ? years : [chosenYear]).map((y) => (
                      <option key={y} value={y}>
                        {y}
                      </option>
                    ))
                  : measures.map((m) => (
                      <option key={m.key} value={m.key}>
                        {m.label} · annual SEC
                      </option>
                    ))}
              </Select>
            </label>
          </div>
          <div
            className={`position-reading ${reading.coverage ? "has-comparison" : "has-gap"}`}
          >
            <strong>{reading.text}</strong>
            {reading.coverage > 0 && (
              <p>
                Based on {reading.coverage} of {data.peers.length} peers with
                usable figures and fiscal ends within 120 days.
                {reading.median != null &&
                  (expected || current.unit === "percent") && (
                    <>
                      {" "}
                      Peer median {percent(reading.median)}; difference{" "}
                      {reading.difference > 0 ? "+" : ""}
                      {reading.difference.toFixed(1)} percentage points.
                    </>
                  )}
              </p>
            )}
          </div>
          {expected && (
            <p className="position-caption">
              FMP annual revenue growth uses two consecutive annual forecast
              averages from the same saved USD response. This is
              forecast-to-forecast growth, not a comparison with actual sales.
              Company fiscal calendars differ.
            </p>
          )}
          <Bars rows={rows} symbol={data.symbol} expected={expected} />
          {!expected && (
            <button
              className="position-check"
              disabled={busy}
              onClick={checkReported}
            >
              {busy ? "Checking…" : "Check reported data for these companies"}
            </button>
          )}
          {expected && (
            <>
              <details className="position-forward-details">
                <summary>
                  Management operating-margin targets · separate definitions
                </summary>
                <p>
                  The targets below retain their own accounting basis. Adjusted
                  company definitions differ, so they do not establish a sector
                  margin ranking.
                </p>
                <div className="position-table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Company</th>
                        <th>Target</th>
                        <th>Basis</th>
                        <th>Quarter ending</th>
                      </tr>
                    </thead>
                    <tbody>
                      {managementRows(data.members).map((r) => (
                        <tr key={r.symbol}>
                          <th>{r.symbol}</th>
                          <td>
                            {r.margin
                              ? `${r.margin.approximate ? "≈ " : ""}${r.margin.low}${r.margin.low !== r.margin.high ? `–${r.margin.high}` : ""}%`
                              : "Unavailable"}
                          </td>
                          <td>{r.margin?.basis || "Not established"}</td>
                          <td>{day(r.section?.period_end)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
              <p className="position-caption">
                Public forecast tables are available in the source details
                below. Their unspecified currency prevents a shared revenue
                scale. Missing competitors or forecast years remain unavailable.
              </p>
            </>
          )}
          <p className="position-caption">
            Whole-company figures include different products, acquisitions and
            fiscal weeks. A company’s position here is relative to these peers;
            it is not an investment score.{" "}
            {expected
              ? ""
              : "Annual growth compares each company with its own prior year. Operating margin uses reported GAAP operating income and revenue, separate from management’s adjusted targets."}
          </p>
        </>
      )}
    </section>
  );
}
