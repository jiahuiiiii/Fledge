import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import Select from "./Select";
import Modal from "./Modal";
import FinancialEvidence, { FinancialEvidenceRow } from "./FinancialEvidence";
import { companyName } from "../lib/companyIdentity";
import LoadingSkeleton from "./LoadingSkeleton";
import { money, percent, day } from "../lib/financialStory";
import {
  measures,
  peRows,
  peerAverage,
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
      : unit === "multiple"
        ? `${value.toLocaleString("en-GB", { maximumFractionDigits: 1 })}×`
        : percent(value);
const rowPeriod = (row, expected) =>
  row.unit === "multiple"
    ? `Saved ${stamp(row.observed)}`
    : expected
      ? `Forecast year ends ${day(row.end)}`
      : `${day(row.start)} – ${day(row.end)}`;
function EvidenceContents({ row, expected }) {
  if (row.unit === "multiple")
    return (
      <>
        <FinancialEvidenceRow
          row={{
            label: "Trailing P/E",
            value: row.exact,
            unit: "multiple",
            explanation: row.basis,
            reason: row.reason,
            period_label: `Finnhub · saved ${stamp(row.observed)}`,
          }}
        />
      </>
    );
  if (expected)
    return (
      <FinancialEvidence
        rows={[
          {
            key: "forecast",
            label: "Forecast revenue",
            value: row.current?.average,
            unit: "USD",
            period_label: `Year ending ${day(row.end)}`,
          },
          {
            key: "forecast",
            label: "Forecast revenue",
            value: row.baseline?.average,
            unit: "USD",
            period_label: `Year ending ${day(row.priorEnd)}`,
          },
        ]}
      >
        <p>Growth compares two annual forecasts from the same FMP response.</p>
        <p>
          Saved {stamp(row.observed)}. The underlying forecast date is unknown.
        </p>
        {row.reason && <p>{row.reason}</p>}
      </FinancialEvidence>
    );
  return (
    <FinancialEvidenceRow
      row={{
        ...row.row,
        label: row.row?.label || "Annual result",
        value: row.exact,
        unit: row.unit,
        start: row.start,
        end: row.end,
        inputs: row.inputs,
        reason: row.reason,
        filing_resolution: row.filingResolution,
      }}
      fallbackUrl={row.report?.filing_url}
    />
  );
}

function Bars({ rows, symbol, expected, label }) {
  const [evidence, setEvidence] = useState(null);
  const range = scale(rows),
    average = peerAverage(rows, symbol),
    multiple = rows[0]?.unit === "multiple",
    available = rows.filter((row) => row.value != null),
    x = (value) => ((value - range.low) / range.span) * 100,
    ticks = !available.length
      ? []
      : available.every((row) => row.value === 0)
        ? [0]
        : [0, range.low, range.high, range.low + range.span / 2].filter(
            (tick, index, values) =>
              values
                .slice(0, index)
                .every((other) => Math.abs(tick - other) / range.span > 0.12),
          );
  const basis = multiple
    ? "Finnhub · trailing 12 months"
    : expected
      ? "annual forecasts"
      : "annual SEC figures";
  const averageExplanation = `Equal-weight mean of ${average.peers.length} of ${Math.max(0, rows.length - 1)} peers. Excludes ${symbol} and unavailable figures${multiple ? "; saved dates may differ." : "; only fiscal ends within 120 days are included."}`;
  const reviewed = rows.filter(
    (row) => row.filingResolution?.status === "retained",
  );
  return (
    <div className="position-comparison">
      <div className="position-chart-toolbar">
        <p>
          {label} · {basis}
          <span>
            {multiple
              ? "Saved observations may be from different dates."
              : "Each company uses its own fiscal year."}
          </span>
        </p>
        <button
          type="button"
          className="secondary"
          aria-haspopup="dialog"
          onClick={() => setEvidence({ symbol: null })}
        >
          Evidence &amp; periods
        </button>
      </div>
      <div
        className="position-bars"
        role="region"
        aria-label={`${label} by company`}
        tabIndex={0}
      >
        <div className="position-bar-chart">
          <div className="position-average-slot">
            {average.value != null ? (
              <span
                className="position-average-flag"
                title={averageExplanation}
                style={{
                  left: `${x(average.value)}%`,
                  transform: `translateX(${x(average.value) > 75 ? "-100%" : x(average.value) < 25 ? "0" : "-50%"})`,
                }}
              >
                Peer avg{" "}
                <strong>{display(average.value, rows[0]?.unit)}</strong>
              </span>
            ) : (
              <span className="position-average-unavailable">
                Peer average unavailable
              </span>
            )}
          </div>
          <div className="position-shared-plot">
            <div className="position-row-guides" aria-hidden="true">
              {ticks.map((tick) => (
                <i
                  key={tick}
                  className={tick === 0 ? "is-zero" : ""}
                  style={{ left: `${x(tick)}%` }}
                />
              ))}
            </div>
            {average.value != null && (
              <i
                className="position-average-line"
                style={{ left: `${x(average.value)}%` }}
                aria-hidden="true"
              />
            )}
            <div className="position-rows">
              {rows.map((row) => (
                <button
                  type="button"
                  key={row.symbol}
                  className={`position-comparison-row${row.symbol === symbol ? " is-company" : ""}`}
                  aria-label={`${row.symbol}: ${display(row.value, row.unit)}. ${row.value == null ? row.reason + " " : ""}Open comparison evidence.`}
                  aria-haspopup="dialog"
                  title={`${companyName(row)} · ${rowPeriod(row, expected)}`}
                  onClick={() => setEvidence({ symbol: row.symbol })}
                >
                  {row.value != null && (
                    <>
                      <span
                        className={`position-row-fill${row.value === 0 ? " is-zero" : ""}`}
                        aria-hidden="true"
                        style={{
                          left: `${x(Math.min(0, row.value))}%`,
                          width: `${(Math.abs(row.value) / range.span) * 100}%`,
                        }}
                      />
                      <span
                        className="position-row-end"
                        style={{ left: `${x(row.value)}%` }}
                        aria-hidden="true"
                      />
                    </>
                  )}
                  <span className="position-row-label" aria-hidden="true">
                    <strong className={row.value == null ? "is-missing" : ""}>
                      {display(row.value, row.unit)}
                    </strong>
                    <span>
                      <b>{row.symbol}</b> {companyName(row)}
                    </span>
                  </span>
                </button>
              ))}
            </div>
          </div>
          <div className="position-scale" aria-hidden="true">
            {ticks.map((tick) => (
              <span
                key={tick}
                style={{
                  left: `${x(tick)}%`,
                  transform: `translateX(${x(tick) > 90 ? "-100%" : x(tick) < 10 ? "0" : "-50%"})`,
                }}
              >
                {display(tick, rows[0]?.unit)}
              </span>
            ))}
          </div>
        </div>
      </div>
      <p className="position-chart-hint">
        {averageExplanation} Select a row for evidence.
      </p>
      {reviewed.length > 0 && (
        <p className="position-chart-note">
          {reviewed.map((row) => row.symbol).join(", ")}: earlier figures
          confirmed unchanged by amendments. See Evidence &amp; periods for the
          supporting filings.
        </p>
      )}
      <Modal
        open={!!evidence}
        onClose={() => setEvidence(null)}
        title="Competitor comparison · evidence"
        className="evidence-dialog position-evidence-dialog"
        initialFocus={evidence?.symbol ? '[data-selected="true"]' : undefined}
      >
        <p className="position-evidence-intro">
          {label} · {basis}. Expand a company for its figures, calculation and
          reports.
        </p>
        <section className="position-average-evidence">
          <h3>Peer average: {display(average.value, rows[0]?.unit)}</h3>
          <p>{averageExplanation}</p>
          {average.peers.length > 0 && (
            <p>
              Included:{" "}
              {average.peers
                .map((row) => `${row.symbol} (${display(row.value, row.unit)})`)
                .join(", ")}
              . The average uses unrounded values.
            </p>
          )}
          {average.missing.length > 0 && (
            <p>
              Excluded: {average.missing.map((row) => row.symbol).join(", ")} ·
              missing or incomparable figures. Dates and reasons are listed
              below.
            </p>
          )}
        </section>
        <div className="position-evidence-list">
          {rows.map((row) => (
            <details
              key={row.symbol}
              open={row.symbol === evidence?.symbol || undefined}
            >
              <summary
                tabIndex={0}
                data-selected={row.symbol === evidence?.symbol}
              >
                <span>
                  <strong>
                    {row.symbol} · {companyName(row)}
                  </strong>
                  <small>{rowPeriod(row, expected)}</small>
                </span>
                <strong>{display(row.value, row.unit)}</strong>
              </summary>
              <div className="position-evidence-content">
                <EvidenceContents row={row} expected={expected} />
              </div>
            </details>
          ))}
        </div>
      </Modal>
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
        Further right means faster fiscal-year sales growth. Higher means a
        larger reported operating margin.
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
              aria-label="Fiscal-year revenue growth against reported GAAP operating margin for the chosen competitors"
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
                Fiscal-year revenue growth →
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
      const [next, valuation] = await Promise.all([
        api.sectorPosition(instrumentId, peers),
        api
          .valuationContext(instrumentId)
          .then((value) => ({ references: value.references || [] }))
          .catch((failure) => ({ references: [], error: failure.message })),
      ]);
      if (mounted.current && token === version.current) {
        setData({
          ...next,
          references: valuation.references,
          referenceError: valuation.error,
        });
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
          if (!mounted.current || token !== version.current) break;
          try {
            await api.refreshSec(company.instrument_id);
          } catch (failure) {
            failures.push(`${member.symbol}: ${failure.message}`);
          }
          if (!mounted.current || token !== version.current) break;
          const saved = await api.sectorPosition(company.instrument_id, []);
          if (
            Object.values(saved.members[0]?.performance?.reports || {}).some(
              (report) => report?.amendment_resolution?.needs_documents,
            )
          ) {
            if (!mounted.current || token !== version.current) break;
            const originals = await api.refreshDisclosures(
              company.instrument_id,
            );
            if (originals.coverage?.some((item) => item.status === "failed")) {
              failures.push(`${member.symbol}: ${originals.message}`);
            }
          }
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
    rows =
      !expected && measure === "pe"
        ? peRows(data?.members || [], data?.references || [])
        : (data?.members || []).map((m) =>
            expected
              ? forecastRow(m, chosenYear, now)
              : reportedRow(m, measure),
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
          {!expected && measure !== "pe" && (
            <Map members={data.members} symbol={data.symbol} />
          )}
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
                        {m.label} · {m.source || "annual SEC"}
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
                usable{" "}
                {current.unit === "multiple" && !expected
                  ? "saved Finnhub P/E figures. A lower P/E does not establish better value."
                  : "figures and fiscal ends within 120 days."}
              </p>
            )}
          </div>
          {!expected && measure === "pe" && data.referenceError && (
            <p className="position-caption" role="status">
              Saved P/E could not be loaded: {data.referenceError}
            </p>
          )}
          {expected && (
            <p className="position-caption">
              FMP annual revenue growth uses two consecutive annual forecast
              averages from the same saved USD response. This is
              forecast-to-forecast growth, not a comparison with actual sales.
              Company fiscal calendars differ.
            </p>
          )}
          <Bars
            key={`${expected ? "expected" : measure}-${expected ? chosenYear : "reported"}`}
            rows={rows}
            symbol={data.symbol}
            expected={expected}
            label={expected ? "Expected revenue growth" : current.label}
          />
          {!expected && measure !== "pe" && (
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
              : measure === "pe"
                ? "P/E uses saved Finnhub trailing-earnings definitions; underlying quote times and GAAP versus adjusted conventions are not established."
                : "Annual growth compares each company with its own prior year. Operating margin uses reported GAAP operating income and revenue, separate from management’s adjusted targets."}
          </p>
        </>
      )}
    </section>
  );
}
