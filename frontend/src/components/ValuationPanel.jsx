import Checkbox from "./Checkbox";
import { readableLoad } from "../lib/loading";
import LoadingSkeleton from "./LoadingSkeleton";
import AnalystTargets from "./AnalystTargets";
import Select from "./Select";
import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
const stamp = (v) =>
  v
    ? new Date(v).toLocaleString("en-GB", {
        timeZone: "UTC",
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      }) + " UTC"
    : "Not checked";
const cash = (v) =>
  v == null
    ? "Unavailable"
    : `USD ${(Number(v) / 1e9).toLocaleString("en-GB", { maximumFractionDigits: 2 })}bn`;
const sharePrice = (v) =>
  v == null
    ? "Unavailable"
    : `USD ${Number(v).toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const today = () => new Date().toISOString().slice(0, 10);
const newPriceReference = () => ({
  valuation_date: today(),
  projected_shares_millions: "",
  annual_return_percent: "",
  share_basis: "",
});
const newCase = (i) => ({
  name: `Case ${String.fromCharCode(65 + i)}`,
  growth: "",
  margin: "",
  multiple: "",
  rationale: "",
  reference_id: null,
});

function Results({ record }) {
  if (!record) return null;
  const a = record.assumptions;
  const pricing = record.result?.price_reference;
  return (
    <section className="valuation-results" aria-label="Valuation results">
      <div className="row">
        <h3>{a.title}</h3>
        <span className="status">
          {record.saved ? "Saved record" : "Unsaved calculation"}
        </span>
      </div>
      {record.saved && (
        <p>
          Saved {stamp(record.created_at)} ·{" "}
          <a href={`/api/v1/valuations/${record.id}/export`}>
            Download this scenario
          </a>
        </p>
      )}
      {record.newer_financials_available && (
        <p className="financial-note">
          Newer financials are available. This record keeps its original filing
          and assumptions.
        </p>
      )}
      {record.withheld ? (
        <p className="financial-note">
          Source access is unavailable. The source packet and calculated results
          are withheld; your assumptions remain saved.
        </p>
      ) : (
        <>
          {pricing ? (
            <div className="price-reference-summary">
              <p>
                Scenario horizon{" "}
                <strong>{record.result.target_period_end}</strong>
                {" · "}Entry reference as of{" "}
                <strong>{pricing.valuation_date}</strong>
              </p>
              <p>
                Your {pricing.annual_return_percent}% annual return assumption
                and{" "}
                {Number(pricing.projected_shares_millions).toLocaleString(
                  "en-GB",
                  { maximumFractionDigits: 6 },
                )}{" "}
                million projected diluted shares apply to every case. These are
                conditional prices, not analyst targets or trade
                recommendations.
              </p>
              <details>
                <summary>Share count basis and return calculation</summary>
                <p>{pricing.share_basis}</p>
                <p>
                  Horizon price = projected equity value ÷ projected shares.
                  Entry reference discounts that price at your chosen annual
                  return from the horizon back to {pricing.valuation_date},
                  using actual days ÷ 365.25. Dividends, taxes and costs are
                  excluded. Prices are rounded for display.
                </p>
              </details>
            </div>
          ) : (
            <p>
              Total company equity value for the hypothetical annual period
              ending <strong>{record.result.target_period_end}</strong>. Values
              are undiscounted. Add a share-count and return assumption to
              calculate per-share price references.
            </p>
          )}
          <div className="valuation-cards">
            {record.result.cases.map((c, i) => (
              <article key={c.name}>
                <span className="section-label">{c.name}</span>
                {pricing ? (
                  <dl className="price-reference-values">
                    <div>
                      <dt>Scenario horizon price</dt>
                      <dd>{sharePrice(c.price_reference.horizon_price)}</dd>
                    </div>
                    <div>
                      <dt>
                        Entry reference · {pricing.annual_return_percent}%
                        return
                      </dt>
                      <dd>{sharePrice(c.price_reference.entry_reference)}</dd>
                    </div>
                  </dl>
                ) : (
                  <strong className="valuation-number">
                    {cash(c.equity_value)}
                  </strong>
                )}
                {c.reason && <p className="financial-note">{c.reason}</p>}
                {pricing && !c.reason && c.price_reference.reason && (
                  <p className="financial-note">{c.price_reference.reason}</p>
                )}
                <p>
                  Annual growth {a.cases[i].growth}% ·{" "}
                  {a.method === "earnings"
                    ? `net margin ${a.cases[i].margin}% · P/E`
                    : "P/S"}{" "}
                  {a.cases[i].multiple}×
                </p>
                <p>{a.cases[i].rationale}</p>
                <details>
                  <summary>Inputs, calculation and sensitivity</summary>
                  <p>
                    {pricing && (
                      <>Total equity value: {cash(c.equity_value)} · </>
                    )}
                    Projected annual revenue: {cash(c.revenue)}
                    {c.net_income != null && (
                      <> · projected net income: {cash(c.net_income)}</>
                    )}
                  </p>
                  <p>
                    Hold the horizon and{" "}
                    {a.method === "earnings" ? "P/E" : "other assumptions"}{" "}
                    fixed. Rows vary annual growth; columns vary{" "}
                    {a.method === "earnings" ? "net margin" : "P/S"}. Each cell
                    shows{" "}
                    {pricing
                      ? "scenario horizon price per share in USD, with your share count fixed"
                      : "total equity value in USD billions"}
                    .
                  </p>
                  <div
                    className="sensitivity-scroll"
                    tabIndex={0}
                    aria-label={`${c.name} sensitivity table`}
                  >
                    <table>
                      <caption>
                        {c.name}:{" "}
                        {a.method === "earnings"
                          ? "growth × net margin"
                          : "growth × P/S"}
                      </caption>
                      <thead>
                        <tr>
                          <th scope="col">Growth</th>
                          {c.sensitivity.columns.map((v) => (
                            <th key={v} scope="col">
                              {v}
                              {a.method === "earnings" ? "%" : "×"}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {c.sensitivity.rows.map((row) => (
                          <tr key={row.growth}>
                            <th scope="row">{row.growth}%</th>
                            {row.cells.map((cell, j) => (
                              <td
                                key={j}
                                title={
                                  cell.reason || `${cell.equity_value} USD`
                                }
                              >
                                {pricing
                                  ? sharePrice(
                                      cell.price_reference.horizon_price,
                                    )
                                  : cell.equity_value == null
                                    ? "Undefined"
                                    : (
                                        Number(cell.equity_value) / 1e9
                                      ).toLocaleString("en-GB", {
                                        maximumFractionDigits: 2,
                                      })}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p>
                    Exact equity result: {c.equity_value ?? "Undefined"} USD.
                  </p>
                </details>
              </article>
            ))}
          </div>
          <details className="financial-method">
            <summary>Source base, reference multiples and formulas</summary>
            <p>
              {record.packet.name}: annual revenue USD{" "}
              {record.packet.base.value}, {record.packet.base.start} to{" "}
              {record.packet.base.end}. Filed {record.packet.report.filed_on}.
              Source checked {stamp(record.packet.source_checked_at)}.
            </p>
            <a
              href={record.packet.report.filing_url}
              target="_blank"
              rel="noreferrer"
            >
              Original SEC filing ↗
            </a>
            {record.packet.references.map((ref, i) => (
              <p key={i}>
                {ref.symbol} Finnhub TTM{" "}
                {a.method === "earnings" ? "P/E" : "P/S"}:{" "}
                {ref.metrics[a.method].value}×, retrieved{" "}
                {stamp(ref.retrieved_at)}. The provider gives no precise ratio
                timestamp.
              </p>
            ))}
            <ul>
              {record.result.formulas
                .concat(record.result.limitations)
                .map((s) => (
                  <li key={s}>{s}</li>
                ))}
            </ul>
          </details>
        </>
      )}
    </section>
  );
}

export default function ValuationPanel({
  instrument,
  performance,
  quote,
  visible = true,
  initialRead,
}) {
  const [context, setContext] = useState(initialRead?.data || null);
  const [base, setBase] = useState(null);
  const [title, setTitle] = useState("");
  const [method, setMethod] = useState("earnings");
  const [years, setYears] = useState("1");
  const [growthStep, setGrowthStep] = useState("5");
  const [marginStep, setMarginStep] = useState("5");
  const [cases, setCases] = useState([newCase(0)]);
  const [includePrices, setIncludePrices] = useState(false);
  const [priceReference, setPriceReference] = useState(newPriceReference);
  const [result, setResult] = useState(null);
  const [selected, setSelected] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(initialRead?.error || "");
  const [message, setMessage] = useState("");
  const [requestId, setRequestId] = useState(() => crypto.randomUUID());
  const preloaded = useRef(initialRead);
  useEffect(() => {
    if (!visible) {
      preloaded.current = null;
      return;
    }
    if (preloaded.current) return;
    let active = true;
    readableLoad(api.valuationContext(instrument.id), context ? 0 : 280)
      .then((v) => {
        if (active) {
          setContext(v);
          setError("");
        }
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [instrument.id, visible]);
  useEffect(() => {
    if (!base && performance?.status === "available") setBase(performance);
  }, [performance, base]);
  useEffect(() => {
    if (performance && performance.status !== "available") {
      setResult((old) =>
        old ? { ...old, withheld: true, packet: null, result: null } : old,
      );
    }
  }, [performance?.status]);
  const report = base?.reports?.annual;
  const revenue = report?.metrics.find((m) => m.key === "revenue");
  const sourceChanged = base && performance?.snapshot_id !== base.snapshot_id;
  const clear = () => {
    setResult(null);
    setSelected("");
    setRequestId(crypto.randomUUID());
    setMessage("");
    setError("");
  };
  const updateCase = (index, changes) => {
    clear();
    setCases((old) =>
      old.map((c, i) => (i === index ? { ...c, ...changes } : c)),
    );
  };
  const body = () => ({
    instrument_id: instrument.id,
    performance_id: base.snapshot_id,
    title,
    method,
    years: Number(years),
    growth_step: growthStep,
    margin_step: marginStep,
    ...(includePrices ? { price_reference: priceReference } : {}),
    cases: cases.map((c) => ({
      ...c,
      margin: method === "earnings" ? c.margin : null,
    })),
  });
  const perform = async (fn) => {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await fn();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  const compare = (event) => {
    event.preventDefault();
    perform(async () => {
      setResult(await api.previewValuation(body()));
      setSelected("");
      setMessage("Calculated locally from your assumptions. Not saved yet.");
    });
  };
  const save = () =>
    perform(async () => {
      const saved = await api.saveValuation({
        ...body(),
        request_id: requestId,
      });
      setResult(saved);
      setSelected(saved.id);
      setContext(await api.valuationContext(instrument.id));
      setMessage("Scenario saved with its exact assumptions and source base.");
    });
  const open = (id) => {
    setSelected(id);
    if (!id) {
      setRequestId(crypto.randomUUID());
      setMessage("");
      setResult(null);
      return;
    }
    perform(async () => setResult(await api.valuationRecord(id)));
  };
  const copy = () => {
    const a = result.assumptions;
    clear();
    setTitle(a.title + " — revised");
    setMethod(a.method);
    setYears(String(a.years));
    setGrowthStep(a.growth_step);
    setMarginStep(a.margin_step);
    setCases(a.cases);
    setIncludePrices(Boolean(a.price_reference));
    setPriceReference(
      a.price_reference ? { ...a.price_reference } : newPriceReference(),
    );
    setBase(performance);
    setMessage(
      "Copied assumptions into a new comparison using the currently displayed financial snapshot. Review the base before calculating.",
    );
  };
  const examples = () => {
    clear();
    setTitle("Illustrative sensitivity — not a forecast");
    setYears("1");
    setMethod("earnings");
    setIncludePrices(false);
    setPriceReference(newPriceReference());
    setCases(
      [newCase(0), newCase(1), newCase(2)].map((c, i) => ({
        ...c,
        growth: String(5 + i * 5),
        margin: String(10 + i * 5),
        multiple: String(15 + i * 5),
        rationale:
          "Generic worked example to explore sensitivity; not a company estimate or investment recommendation.",
      })),
    );
  };
  const references = context?.references || [];
  const ready =
    revenue?.value != null &&
    Number(revenue.value) > 0 &&
    performance?.status === "available";
  if (!context && !error)
    return (
      <section className="valuation-panel" aria-label="Valuation scenarios">
        <LoadingSkeleton
          variant="panel"
          rows={3}
          label="Loading valuation references…"
        />
      </section>
    );
  return (
    <section className="valuation-panel" aria-label="Valuation scenarios">
      <AnalystTargets
        value={context?.analyst_targets}
        quote={quote}
        onRefresh={async () => {
          try {
            await api.refreshAnalystTargets(instrument.id);
          } finally {
            setContext(await api.valuationContext(instrument.id));
          }
        }}
      />
      <span className="section-label">WHAT WOULD HAVE TO BE TRUE?</span>
      <h2>Explore the assumptions</h2>
      <p>
        Compare equity-multiple scenarios using reported annual revenue, your
        growth assumptions and your chosen multiple. Every calculation is local
        and uses no AI.
      </p>
      <details className="valuation-references">
        <summary>Compare reference multiples</summary>
        <p>
          Supported companies for context; they are not an automatically
          selected peer group. Finnhub’s trailing-twelve-month (TTM) multiples
          differ from this annual-base projection. Differences in profitability,
          financing and business mix matter.
        </p>
        {references.map((c) => (
          <article key={c.id}>
            <div>
              <strong>{c.symbol}</strong> {c.name}
              <p>
                P/E {c.reference?.metrics.earnings.value ?? "Unavailable"}× ·
                P/S {c.reference?.metrics.sales.value ?? "Unavailable"}×
              </p>
              <small>
                Retrieved {stamp(c.reference?.retrieved_at)}. Precise ratio
                timestamp unavailable.
              </small>
              {c.reference &&
                Date.now() - new Date(c.reference.retrieved_at).getTime() >
                  86400000 && (
                  <p className="financial-note">
                    This reference is more than 24 hours old.
                  </p>
                )}
              {c.refresh?.error && (
                <p className="financial-note">{c.refresh.error}</p>
              )}
              {!c.available && <p>Source access is unavailable.</p>}
            </div>
            <button
              type="button"
              disabled={busy || !c.available}
              onClick={() =>
                perform(async () => {
                  await api.refreshMultiples(c.id);
                  setContext(await api.valuationContext(instrument.id));
                  setMessage(
                    `${c.symbol} reference updated. Your chosen assumptions are unchanged.`,
                  );
                })
              }
            >
              Refresh {c.symbol} reference
            </button>
          </article>
        ))}
        <p>
          Refreshes are manual and one hour apart per company. A missing or
          nonpositive multiple is unavailable, not zero. The form below remains
          your decision.
        </p>
      </details>
      <label className="valuation-history">
        Saved comparisons
        <Select
          aria-label="Saved valuation comparison"
          value={selected}
          disabled={busy}
          onChange={(e) => open(e.target.value)}
        >
          <option value="">New comparison</option>
          {context?.saved.map((s) => (
            <option key={s.id} value={s.id}>
              {s.title} · {stamp(s.created_at)}
            </option>
          ))}
        </Select>
      </label>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {message && <p role="status">{message}</p>}
      {selected && result?.saved ? (
        <>
          <Results record={result} />
          <button type="button" disabled={busy || !ready} onClick={copy}>
            Use these assumptions in a new comparison
          </button>
        </>
      ) : (
        <>
          {!ready && (
            <p className="financial-note">
              A positive reported annual revenue base is required. Refresh
              filings to prepare it; quarterly figures are not annualised.
            </p>
          )}
          {ready && report && (
            <div className="valuation-base">
              <strong>
                Base: {instrument.name} · annual period ended{" "}
                {report.period_end}
              </strong>
              <p>
                Revenue {cash(revenue?.value)} · filed {report.filed_on}.{" "}
                <a href={report.filing_url} target="_blank" rel="noreferrer">
                  Inspect base filing ↗
                </a>
              </p>
              <p>
                Years below are measured after this reporting year, not after
                today. Historical profit can include nonrecurring items; choose
                a forward net margin explicitly.
              </p>
            </div>
          )}
          {sourceChanged && (
            <div className="financial-note">
              <p>
                Financial data changed while you were working. Review the new
                base before calculating.
              </p>
              <button
                type="button"
                disabled={busy}
                onClick={() => {
                  clear();
                  setBase(performance);
                }}
              >
                Use latest financial base
              </button>
            </div>
          )}
          <form onSubmit={compare}>
            <fieldset disabled={busy}>
              <legend>Your scenario assumptions</legend>
              <label>
                Comparison title
                <input
                  aria-label="Valuation title"
                  required
                  maxLength={120}
                  value={title}
                  onChange={(e) => {
                    clear();
                    setTitle(e.target.value);
                  }}
                />
              </label>
              <div className="valuation-controls">
                <label>
                  Equity multiple
                  <Select
                    aria-label="Valuation method"
                    value={method}
                    onChange={(e) => {
                      clear();
                      setMethod(e.target.value);
                      setCases((old) =>
                        old.map((c) => ({
                          ...c,
                          multiple: "",
                          reference_id: null,
                        })),
                      );
                    }}
                  >
                    <option value="earnings">P/E × projected net income</option>
                    <option value="sales">P/S × projected revenue</option>
                  </Select>
                </label>
                <label>
                  Years after base period
                  <Select
                    aria-label="Valuation horizon"
                    value={years}
                    onChange={(e) => {
                      clear();
                      setYears(e.target.value);
                    }}
                  >
                    {[1, 2, 3, 4, 5].map((y) => (
                      <option key={y}>{y}</option>
                    ))}
                  </Select>
                </label>
              </div>
              <p className="valuation-explainer">
                {method === "earnings"
                  ? "Net margin means net income attributable to common equity after interest and tax, divided by revenue. Positive earnings are required for a P/E result."
                  : "P/S compares total equity value with annual revenue. A high sales multiple needs context from profitability and financing; it does not establish that a company is cheap or expensive."}
              </p>
              <section
                className="price-reference-inputs"
                aria-label="Share price assumptions"
              >
                <label className="price-reference-toggle">
                  <Checkbox
                    checked={includePrices}
                    onChange={(e) => {
                      clear();
                      setIncludePrices(e.target.checked);
                    }}
                  />
                  Add entry and horizon price references
                </label>
                {includePrices && (
                  <>
                    <p>
                      Choose a projected share count and annual return to
                      translate these scenarios into per-share prices. These
                      inputs stay separate from the analyst targets above.
                    </p>
                    <div className="valuation-controls">
                      <label>
                        Projected diluted shares (millions)
                        <input
                          aria-label="Projected diluted shares in millions"
                          type="number"
                          required
                          min="0.000001"
                          max="10000000"
                          step="any"
                          value={priceReference.projected_shares_millions}
                          onChange={(e) => {
                            clear();
                            setPriceReference((p) => ({
                              ...p,
                              projected_shares_millions: e.target.value,
                            }));
                          }}
                        />
                      </label>
                      <label>
                        Annual return assumption %
                        <input
                          aria-label="Annual return assumption"
                          type="number"
                          required
                          min="0"
                          max="100"
                          step="any"
                          value={priceReference.annual_return_percent}
                          onChange={(e) => {
                            clear();
                            setPriceReference((p) => ({
                              ...p,
                              annual_return_percent: e.target.value,
                            }));
                          }}
                        />
                      </label>
                      <label>
                        Valuation date (UTC)
                        <input
                          aria-label="Price reference valuation date"
                          type="date"
                          required
                          min={report?.filed_on}
                          max={today()}
                          value={priceReference.valuation_date}
                          onChange={(e) => {
                            clear();
                            setPriceReference((p) => ({
                              ...p,
                              valuation_date: e.target.value,
                            }));
                          }}
                        />
                      </label>
                    </div>
                    <label>
                      Share count source and assumptions
                      <textarea
                        aria-label="Share count basis"
                        required
                        minLength={8}
                        maxLength={1200}
                        placeholder="Record the source and date, share classes, split basis and expected dilution or buybacks."
                        value={priceReference.share_basis}
                        onChange={(e) => {
                          clear();
                          setPriceReference((p) => ({
                            ...p,
                            share_basis: e.target.value,
                          }));
                        }}
                      />
                    </label>
                    <details>
                      <summary>Which share count should I use?</summary>
                      <p>
                        Enter your expected total diluted common shares at the
                        horizon, including economically equivalent share
                        classes. One billion shares is 1,000 million. A reported
                        weighted-average count is historical context, not a
                        forecast of future shares.
                      </p>
                      <p>
                        Keep share splits and dilution consistent. Do not use
                        one class alone, a depositary receipt ratio or unequal
                        economic rights without a separate conversion. The app
                        does not verify this assumption or adjust it
                        automatically.
                      </p>
                    </details>
                  </>
                )}
              </section>
              <div className="valuation-case-inputs">
                {cases.map((c, i) => (
                  <fieldset key={i}>
                    <legend>Case {i + 1}</legend>
                    <label>
                      Name
                      <input
                        aria-label={`Case ${i + 1} name`}
                        required
                        maxLength={60}
                        value={c.name}
                        onChange={(e) =>
                          updateCase(i, { name: e.target.value })
                        }
                      />
                    </label>
                    <label>
                      Annual revenue growth %
                      <input
                        aria-label={`Case ${i + 1} growth`}
                        required
                        type="number"
                        min="-100"
                        max="200"
                        step="any"
                        value={c.growth}
                        onChange={(e) =>
                          updateCase(i, { growth: e.target.value })
                        }
                      />
                    </label>
                    {method === "earnings" && (
                      <label>
                        Net margin at horizon %
                        <input
                          aria-label={`Case ${i + 1} margin`}
                          required
                          type="number"
                          min="-100"
                          max="100"
                          step="any"
                          value={c.margin}
                          onChange={(e) =>
                            updateCase(i, { margin: e.target.value })
                          }
                        />
                      </label>
                    )}
                    <label>
                      {method === "earnings" ? "P/E" : "P/S"} multiple ×
                      <input
                        aria-label={`Case ${i + 1} multiple`}
                        required
                        type="number"
                        min="0.000001"
                        max="200"
                        step="any"
                        value={c.multiple}
                        onChange={(e) =>
                          updateCase(i, {
                            multiple: e.target.value,
                            reference_id: null,
                          })
                        }
                      />
                    </label>
                    <label>
                      Optional reference
                      <Select
                        aria-label={`Case ${i + 1} reference`}
                        value={c.reference_id || ""}
                        onChange={(e) => {
                          const ref = references.find(
                            (x) => x.reference?.id === e.target.value,
                          )?.reference;
                          updateCase(
                            i,
                            ref
                              ? {
                                  reference_id: ref.id,
                                  multiple: ref.metrics[method].value,
                                }
                              : { reference_id: null },
                          );
                        }}
                      >
                        <option value="">My own multiple assumption</option>
                        {references
                          .filter(
                            (r) =>
                              r.reference?.metrics[method].value &&
                              Number(r.reference.metrics[method].value) <= 200,
                          )
                          .map((r) => (
                            <option key={r.id} value={r.reference.id}>
                              {r.symbol} · {r.reference.metrics[method].value}×
                              TTM
                            </option>
                          ))}
                      </Select>
                    </label>
                    <label>
                      Why these assumptions?
                      <textarea
                        aria-label={`Case ${i + 1} rationale`}
                        required
                        minLength={3}
                        maxLength={1200}
                        value={c.rationale}
                        onChange={(e) =>
                          updateCase(i, { rationale: e.target.value })
                        }
                      />
                    </label>
                    {cases.length > 1 && (
                      <button
                        type="button"
                        onClick={() => {
                          clear();
                          setCases((old) => old.filter((_, j) => j !== i));
                        }}
                      >
                        Remove case {i + 1}
                      </button>
                    )}
                  </fieldset>
                ))}
              </div>
              <div className="valuation-actions">
                <button
                  type="button"
                  disabled={cases.length >= 3}
                  onClick={() => {
                    clear();
                    setCases((old) => [...old, newCase(old.length)]);
                  }}
                >
                  Add case
                </button>
                <button type="button" onClick={examples}>
                  Try illustrative assumptions
                </button>
              </div>
              <details className="financial-method">
                <summary>Sensitivity settings</summary>
                <div className="valuation-controls">
                  <label>
                    Growth step (percentage points)
                    <input
                      aria-label="Growth sensitivity step"
                      type="number"
                      required
                      min="0.0001"
                      max="50"
                      step="any"
                      value={growthStep}
                      onChange={(e) => {
                        clear();
                        setGrowthStep(e.target.value);
                      }}
                    />
                  </label>
                  {method === "earnings" ? (
                    <label>
                      Margin step (percentage points)
                      <input
                        aria-label="Margin sensitivity step"
                        type="number"
                        required
                        min="0.0001"
                        max="50"
                        step="any"
                        value={marginStep}
                        onChange={(e) => {
                          clear();
                          setMarginStep(e.target.value);
                        }}
                      />
                    </label>
                  ) : (
                    <p>
                      P/S columns use 75%, 100% and 125% of the chosen multiple,
                      capped at 200×.
                    </p>
                  )}
                </div>
              </details>
              <div className="valuation-actions">
                <button
                  className="primary"
                  disabled={!ready || sourceChanged}
                  type="submit"
                >
                  {busy ? "Working…" : "Calculate scenarios"}
                </button>
                {result && !result.saved && (
                  <button
                    type="button"
                    disabled={!ready || sourceChanged}
                    onClick={save}
                  >
                    Save this comparison
                  </button>
                )}
              </div>
            </fieldset>
          </form>
          <Results record={result} />
        </>
      )}
    </section>
  );
}
