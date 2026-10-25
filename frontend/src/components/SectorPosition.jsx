import { Combobox } from "./ui";
import { formatTimestamp } from "../lib/dateTime";
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
  chartRows,
  differentYearEnd,
  comparisonExclusion,
  reportedRow,
  forecastRow,
  yearsFor,
  position,
  scale,
  managementRows,
  peerStatus,
} from "../lib/sectorPosition";
import "./SectorPosition.css";
const stamp = (value) =>
  formatTimestamp(value, { fallback: "Not established" });
const display = (value, unit) =>
  value == null
    ? "Unavailable"
    : unit === "USD"
      ? money(value)
      : unit === "multiple"
        ? `${value.toLocaleString("en-GB", { maximumFractionDigits: 1 })}×`
        : percent(value);
const rowValue = (row) =>
  row.value == null
    ? {
        loading: "Fetching…",
        not_collected: "Not collected",
        failed: "Fetch failed",
        no_report: "No annual report",
        unavailable: "Source unavailable",
      }[row.dataStatus?.status] || "Not reported"
    : display(row.value, row.unit);
const rowPeriod = (row, expected) =>
  row.unit === "multiple"
    ? `Saved ${stamp(row.observed)}`
    : !row.end
      ? row.dataStatus?.message || "Period not available"
      : expected
        ? `Forecast year ends ${day(row.end)}`
        : row.start
          ? `${day(row.start)} – ${day(row.end)}${row.basisLabel ? ` · ${row.basisLabel}` : ""}`
          : `Year ended ${day(row.end)}`;
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
  const plotted = chartRows(rows, symbol),
    own = rows.find((row) => row.symbol === symbol),
    range = scale(plotted),
    average = peerAverage(rows, symbol),
    multiple = rows[0]?.unit === "multiple",
    available = plotted.filter((row) => row.value != null),
    references = plotted.filter((row) => differentYearEnd(row, own)),
    unplotted = average.missing.filter((row) => !plotted.includes(row)),
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
  const averageExplanation = `Average of ${average.peers.length} of ${Math.max(0, rows.length - 1)} peers${multiple ? "; saved dates may differ." : "; fiscal year ends within 120 days."}`;
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
              : "Peer average and ranking use year-ends within 120 days."}
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
                No comparable peer average
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
              {plotted.map((row) => (
                <button
                  type="button"
                  key={row.symbol}
                  className={`position-comparison-row${row.symbol === symbol ? " is-company" : ""}${differentYearEnd(row, own) ? " is-different-year-end" : ""}`}
                  aria-label={`${row.symbol}: ${rowValue(row)}. ${rowPeriod(row, expected)}. ${differentYearEnd(row, own) ? "Different year-end; outside peer average and ranking. " : ""}${row.value == null ? row.reason + " " : ""}Open comparison evidence.`}
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
                      {rowValue(row)}
                    </strong>
                    <span>
                      <b>{row.symbol}</b> {companyName(row)}
                    </span>
                    {!multiple && row.end && (
                      <small className="position-row-period">
                        {expected ? "Year ending" : "Year ended"} {day(row.end)}
                      </small>
                    )}
                    {differentYearEnd(row, own) && (
                      <small className="position-period-badge">
                        Different year-end
                      </small>
                    )}
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
      {references.length > 0 && (
        <p className="position-period-note">
          Dashed bars have different year-ends and are outside the peer average
          and ranking.
        </p>
      )}
      <p className="position-chart-hint">Select a row for evidence.</p>
      {unplotted.length > 0 && (
        <details
          className="position-excluded"
          aria-label="Not included in this comparison"
        >
          <summary>
            {unplotted.length} {unplotted.length === 1 ? "peer" : "peers"} not
            plotted · evidence
          </summary>
          {unplotted.map((row) => (
            <button
              type="button"
              key={row.symbol}
              className="position-excluded-row"
              aria-haspopup="dialog"
              onClick={() => setEvidence({ symbol: row.symbol })}
            >
              <span>
                <b>
                  {row.symbol} · {companyName(row)}
                </b>
                <strong>{rowValue(row)}</strong>
              </span>
              <span>{rowPeriod(row, expected)}</span>
              <span>{comparisonExclusion(row, own)} Open evidence.</span>
            </button>
          ))}
        </details>
      )}
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
                .map((row) => `${row.symbol} (${rowValue(row)})`)
                .join(", ")}
              . The average uses unrounded values.
            </p>
          )}
          {average.missing.length > 0 && (
            <p>
              Outside the average and ranking:{" "}
              {average.missing.map((row) => row.symbol).join(", ")}. Dates and
              reasons are listed below.
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
                <strong>{rowValue(row)}</strong>
              </summary>
              <div className="position-evidence-content">
                {average.missing.includes(row) && (
                  <p>
                    {differentYearEnd(row, own)
                      ? "Shown for context; outside the peer average and ranking."
                      : "Not plotted."}{" "}
                    {comparisonExclusion(row, own)}
                  </p>
                )}
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
  const viewport = useRef(null);
  const [width, setWidth] = useState(660);
  useEffect(() => {
    const element = viewport.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => {
      setWidth(Math.max(260, Math.round(entry.contentRect.width)));
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, [members]);
  const rows = members.map((member) => ({
    growth: reportedRow(member, "revenue_growth"),
    margin: reportedRow(member, "operating_margin"),
  }));
  const plotted = chartRows(
    rows.map((r) => r.growth),
    symbol,
  );
  const valid = rows.filter(
    (r) =>
      plotted.includes(r.growth) &&
      r.growth.value != null &&
      r.margin.value != null &&
      r.growth.start === r.margin.start &&
      r.growth.end === r.margin.end,
  );
  const own = rows.find((r) => r.growth.symbol === symbol)?.growth,
    references = valid.filter((r) => differentYearEnd(r.growth, own)),
    xs = scale(valid.map((r) => r.growth)),
    ys = scale(valid.map((r) => r.margin));
  const plotWidth = width - 116;
  const x = (v) => 72 + ((v - xs.low) / xs.span) * plotWidth,
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
            ref={viewport}
            tabIndex={0}
            role="region"
            aria-label="Growth and profitability map"
          >
            <svg
              viewBox={`0 0 ${width} 320`}
              width={width}
              height={320}
              role="img"
              aria-label="Fiscal-year revenue growth against reported operating margin for the chosen competitors"
            >
              {[0, 0.5, 1].map((f) => (
                <g key={f} className="position-grid">
                  <line
                    x1="72"
                    x2={width - 44}
                    y1={52 + 218 * f}
                    y2={52 + 218 * f}
                  />
                  <text x="62" y={56 + 218 * f} textAnchor="end">
                    {percent(ys.high - ys.span * f)}
                  </text>
                  <line
                    x1={72 + plotWidth * f}
                    x2={72 + plotWidth * f}
                    y1="52"
                    y2="270"
                  />
                  <text x={72 + plotWidth * f} y="292" textAnchor="middle">
                    {percent(xs.low + xs.span * f)}
                  </text>
                </g>
              ))}
              <text
                className="position-axis"
                x={72 + plotWidth / 2}
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
                  className={`position-dot${r.growth.symbol === symbol ? " selected" : ""}${differentYearEnd(r.growth, own) ? " is-different-year-end" : ""}`}
                >
                  <title>
                    {r.growth.symbol}: growth {percent(r.growth.value)},
                    operating margin {percent(r.margin.value)}, year ending{" "}
                    {r.growth.end}
                    {differentYearEnd(r.growth, own)
                      ? "; different year-end, outside peer average and ranking"
                      : ""}
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
            {valid.length} of {members.length} companies shown.
            {references.length > 0 && (
              <>
                {" "}
                Hollow markers have different year-ends:{" "}
                {references
                  .map((r) => `${r.growth.symbol} (${day(r.growth.end)})`)
                  .join(", ")}
                . They are outside the peer average and ranking.
              </>
            )}{" "}
            Dates and sources are in the comparison below.
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
  const [savedData, setData] = useState(null),
    [draft, setDraft] = useState(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [phase, setPhase] = useState(""),
    [notice, setNotice] = useState(""),
    [fetchStates, setFetchStates] = useState({}),
    [measure, setMeasure] = useState("revenue_growth"),
    [view, setView] = useState("reported"),
    [year, setYear] = useState(""),
    [search, setSearch] = useState(""),
    [searchResults, setSearchResults] = useState([]),
    [searched, setSearched] = useState(""),
    [searchError, setSearchError] = useState(""),
    [reasons, setReasons] = useState({}),
    [known, setKnown] = useState({});
  const data = savedData?.loadedFor === instrumentId ? savedData : null;
  const version = useRef(0),
    mounted = useRef(true),
    dirty = useRef(false),
    searchVersion = useRef(0),
    acting = useRef(null),
    readVersion = useRef(0),
    company = useRef(instrumentId);
  const active = (token) => mounted.current && token === version.current;
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      version.current++;
    };
  }, []);
  async function load(replaceDraft = false) {
    const token = version.current,
      read = ++readVersion.current;
    try {
      const [next, valuation] = await Promise.all([
        api.sectorPosition(instrumentId),
        api
          .valuationContext(instrumentId)
          .then((value) => ({ references: value.references || [] }))
          .catch((failure) => ({ references: [], error: failure.message })),
      ]);
      if (!active(token) || read !== readVersion.current) return null;
      setData({
        ...next,
        loadedFor: instrumentId,
        references: valuation.references,
        referenceError: valuation.error,
      });
      if (replaceDraft || !dirty.current) {
        setDraft(next.peers);
        setReasons(
          Object.fromEntries(
            next.members
              .filter((m) => m.symbol !== next.symbol)
              .map((m) => [
                m.symbol,
                m.rationale || "Selected by the owner for comparison.",
              ]),
          ),
        );
        dirty.current = false;
      }
      setError("");
      return next;
    } catch (failure) {
      if (active(token) && read === readVersion.current)
        setError(failure.message);
      return null;
    }
  }
  useEffect(() => {
    if (company.current !== instrumentId) {
      company.current = instrumentId;
      dirty.current = false;
      acting.current = null;
      setData(null);
      setDraft(null);
      setSearch("");
      setSearchResults([]);
      setSearched("");
      setReasons({});
      setKnown({});
      setFetchStates({});
      setNotice("");
      setBusy(false);
      setPhase("");
      searchVersion.current++;
    }
    if (visible) load();
    return () => {
      version.current++;
      searchVersion.current++;
      acting.current = null;
      setFetchStates({});
      setBusy(false);
      setPhase("");
    };
  }, [instrumentId, visible]);
  const waiting = data?.members.some(
    (m) => m.filing_status?.status === "loading",
  );
  useEffect(() => {
    if (!visible || !waiting || busy) return;
    let canceled = false,
      timer;
    async function poll() {
      await load();
      if (!canceled) timer = setTimeout(poll, 3000);
    }
    timer = setTimeout(poll, 3000);
    return () => {
      canceled = true;
      clearTimeout(timer);
    };
  }, [instrumentId, visible, waiting, busy]);
  async function searchPeers(value) {
    setSearch(value);
    setSearchError("");
    const token = ++searchVersion.current,
      scope = version.current;
    if (!value.trim()) {
      setSearchResults([]);
      setSearched("");
      return;
    }
    try {
      const result = await api.companyDirectory(value);
      if (active(scope) && token === searchVersion.current) {
        setSearchResults(
          result.companies.filter(
            (c) => c.available && c.symbol !== data?.symbol,
          ),
        );
        setSearched(value);
      }
    } catch (failure) {
      if (active(scope) && token === searchVersion.current) {
        setSearchResults([]);
        setSearched(value);
        setSearchError(failure.message);
      }
    }
  }
  function changePeers(next) {
    dirty.current = true;
    setDraft(next);
    setNotice("Unsaved changes");
  }
  function addPeer(symbol) {
    if (busy || draft?.includes(symbol) || (draft || []).length >= 8) return;
    const found = searchResults.find((c) => c.symbol === symbol);
    if (found) setKnown((old) => ({ ...old, [symbol]: found }));
    changePeers([...(draft || []), symbol]);
    setSearch("");
    setSearchResults([]);
    setSearched("");
    searchVersion.current++;
  }
  async function save() {
    if (acting.current) return;
    let selected = [...(draft || [])];
    if (search.trim()) {
      const choices =
        searched === search
          ? searchResults.filter((c) => !selected.includes(c.symbol))
          : [];
      const chosen =
        choices.find((c) => c.symbol === search.trim().toUpperCase()) ||
        (choices.length === 1 ? choices[0] : null);
      if (!chosen || selected.length >= 8) {
        setError("Choose a matching company before saving.");
        return;
      }
      selected.push(chosen.symbol);
      dirty.current = true;
      setNotice("Unsaved changes");
      setDraft(selected);
      setKnown((old) => ({ ...old, [chosen.symbol]: chosen }));
      setSearch("");
      setSearchResults([]);
      setSearched("");
      searchVersion.current++;
    }
    const operation = {},
      token = version.current;
    acting.current = operation;
    readVersion.current++;
    setBusy(true);
    setPhase("saving");
    setError("");
    try {
      await api.savePeers(
        instrumentId,
        selected.map((symbol) => ({
          symbol,
          rationale: reasons[symbol] || "Selected by the owner for comparison.",
        })),
      );
      if (!active(token)) return;
      setNotice("Saved");
      dirty.current = false;
      setFetchStates({});
      let next = await load(true);
      if (!next || !active(token)) return;
      const needsDocuments = (member) =>
        Object.values(member.performance?.reports || {}).some(
          (report) => report?.amendment_resolution?.needs_documents,
        );
      const pending = next.members.filter(
        (m) =>
          m.filing_status?.status !== "loading" &&
          (m.filing_status?.can_fetch || needsDocuments(m)),
      );
      setFetchStates(
        Object.fromEntries(
          pending.map((m) => [
            m.symbol,
            { status: "loading", message: "Waiting to fetch financial data…" },
          ]),
        ),
      );
      // Apply the saved group first. Each completed source updates the chart;
      // navigation stops later dispatches, and no AI route is involved.
      for (const planned of pending) {
        if (!active(token)) break;
        const member =
          next?.members.find((m) => m.symbol === planned.symbol) || planned;
        if (
          member.filing_status?.status === "loading" ||
          (!member.filing_status?.can_fetch && !needsDocuments(member))
        ) {
          setFetchStates((old) => {
            const rest = { ...old };
            delete rest[member.symbol];
            return rest;
          });
          continue;
        }
        setPhase("fetching");
        setFetchStates((old) => ({
          ...old,
          [member.symbol]: {
            status: "loading",
            message: "Fetching financial data…",
          },
        }));
        let completed = false;
        try {
          const id =
            member.instrument_id ||
            (await api.addSecCompany(member.symbol)).instrument_id;
          if (!active(token)) break;
          if (member.filing_status?.can_fetch) await api.refreshSec(id);
          if (!active(token)) break;
          const saved = await api.sectorPosition(id, []);
          if (!active(token)) break;
          if (needsDocuments(saved.members[0])) {
            setFetchStates((old) => ({
              ...old,
              [member.symbol]: {
                status: "loading",
                message: "Reading original filings…",
              },
            }));
            const originals = await api.refreshDisclosures(id);
            if (originals.coverage?.some((item) => item.status === "failed"))
              throw new Error(originals.message);
          }
          if (!active(token)) break;
          completed = true;
        } catch (failure) {
          if (!active(token)) break;
          setFetchStates((old) => ({
            ...old,
            [member.symbol]: { status: "failed", message: failure.message },
          }));
        }
        if (active(token)) {
          next = await load();
          if (completed && active(token))
            setFetchStates((old) => {
              const rest = { ...old };
              if (next) delete rest[member.symbol];
              else
                rest[member.symbol] = {
                  status: "failed",
                  message:
                    "Data was checked, but the saved results could not be loaded. Save & compare to try again.",
                };
              return rest;
            });
        }
      }
    } catch (failure) {
      if (active(token)) setError(failure.message);
    } finally {
      if (acting.current === operation) acting.current = null;
      if (active(token)) {
        setBusy(false);
        setPhase("");
      }
    }
  }
  const candidates = [
    ...(data?.candidates || []),
    ...Object.values(known),
    ...searchResults,
  ].filter(
    (c, i, all) => all.findIndex((other) => other.symbol === c.symbol) === i,
  );
  const now = new Date().toISOString().slice(0, 10),
    years = yearsFor(data?.members || [], now),
    chosenYear = years.includes(year)
      ? year
      : years[0] || String(new Date().getFullYear() + 1);
  const expected = view === "expected",
    current = measures.find((m) => m.key === measure),
    rows = (
      !expected && measure === "pe"
        ? peRows(data?.members || [], data?.references || [])
        : (data?.members || []).map((m) =>
            expected
              ? forecastRow(m, chosenYear, now)
              : reportedRow(m, measure),
          )
    ).map((row) =>
      !expected &&
      measure !== "pe" &&
      row.value == null &&
      fetchStates[row.symbol]
        ? {
            ...row,
            dataStatus: fetchStates[row.symbol],
            reason: fetchStates[row.symbol].message,
          }
        : row,
    ),
    reading = position(rows, data?.symbol),
    ownRow = rows.find((row) => row.symbol === data?.symbol),
    hasReferencePeers = rows.some((row) => differentYearEnd(row, ownRow)),
    fetching =
      Object.values(fetchStates).some((s) => s.status === "loading") || waiting;
  return (
    <section className="sector-position" aria-label="Competitor position">
      <header className="outlook-section-heading">
        <h2>Where {data?.symbol || "the company"} stands among competitors</h2>
        <p>Compare saved growth, profitability and scale.</p>
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
          <div className="position-group">
            <h3>Peers</h3>
            <div className="position-search">
              <span>Add a peer</span>
              <Combobox
                label="Peer ticker or company"
                placeholder="Type a ticker or company name"
                disabled={busy || (draft || []).length >= 8}
                filter={false}
                onQueryChange={searchPeers}
                options={searchResults
                  .filter((c) => !draft?.includes(c.symbol))
                  .map((c) => ({ value: c.symbol, label: `${c.symbol} · ${companyName(c)}` }))}
                emptyText={
                  searchError ||
                  (searched !== search
                    ? "Searching…"
                    : searchResults.length
                      ? "Already selected"
                      : "No matching company")
                }
                onSelect={addPeer}
              />
            </div>
            <ul
              className="position-peer-list"
              aria-label="Selected peers"
              aria-live="polite"
            >
              {(draft || []).map((symbol) => {
                const member = data.members.find((m) => m.symbol === symbol),
                  row = rows.find((r) => r.symbol === symbol),
                  status = peerStatus(
                    member &&
                      (expected || measure === "pe"
                        ? { ...member, filing_status: null }
                        : member),
                    row,
                    rows.find((r) => r.symbol === data.symbol),
                    !expected && measure !== "pe" ? fetchStates[symbol] : null,
                  );
                return (
                  <li key={symbol}>
                    <div>
                      <strong>
                        {symbol}{" "}
                        <span>
                          {companyName(
                            member ||
                              candidates.find((c) => c.symbol === symbol) || {
                                symbol,
                              },
                          )}
                        </span>
                      </strong>
                      <small>{status.message}</small>
                    </div>
                    <span
                      className={`position-peer-status is-${status.status}`}
                    >
                      {status.label}
                    </span>
                    <button
                      type="button"
                      className="secondary"
                      disabled={busy}
                      aria-label={`Remove ${symbol}`}
                      onClick={() =>
                        changePeers(draft.filter((s) => s !== symbol))
                      }
                    >
                      ×
                    </button>
                  </li>
                );
              })}
            </ul>
            <div className="position-save-row">
              <button disabled={busy} onClick={save}>
                {phase === "saving"
                  ? "Saving…"
                  : phase === "fetching"
                    ? "Fetching data…"
                    : "Save & compare"}
              </button>
              <span role="status">
                {notice}
                {(draft || []).length >= 8 ? " · 8-peer limit" : ""}
              </span>
            </div>
            {!draft?.length && data.suggestion_source && (
              <p className="position-caption">
                Saving with no peers restores the suggested group.
              </p>
            )}
          </div>
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
            <strong>
              {fetching && !reading.coverage
                ? "Fetching financial data…"
                : !reading.coverage &&
                    ownRow?.value != null &&
                    hasReferencePeers
                  ? "Different year-ends: figures shown for context."
                  : reading.text}
            </strong>
            {reading.coverage > 0 && (
              <p>
                Average and ranking: {reading.coverage} of {data.peers.length}{" "}
                peers.
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
                : "Annual growth compares each company with its own prior year. Operating margin uses reported operating income and revenue in one currency and accounting basis, separate from management’s adjusted targets."}
          </p>
        </>
      )}
    </section>
  );
}
