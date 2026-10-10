import { readableNote, sourceTiming } from "../lib/readingNotes";
import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import Select from "./Select";
import AnalystForecasts from "./AnalystForecasts";
import TermHelp from "./TermHelp";
const PeerComparison = lazy(() => import("./PeerComparison"));
const stamp = (value) =>
  value
    ? new Date(value).toLocaleString("en-GB", { timeZone: "UTC" }) + " UTC"
    : "Not collected";
const figure = (value) =>
  value == null
    ? "Unavailable"
    : new Intl.NumberFormat("en-GB", { maximumFractionDigits: 2 }).format(
        Number(value),
      );
function SourceState({ source }) {
  return (
    <>
      <p className="financial-note">{source?.message}</p>
      {source && (
        <p className="financial-note">{sourceTiming(source, stamp)}</p>
      )}
    </>
  );
}
export default function FmpPanel({ instrumentId, visible, mode = "peers" }) {
  const [data, setData] = useState(null),
    [selections, setSelections] = useState([]),
    [hasDraft, setHasDraft] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const mounted = useRef(true);
  const company = useRef(instrumentId);
  const dirty = useRef(false),
    requestVersion = useRef(0),
    actionBusy = useRef(false);
  function editSelections(update) {
    dirty.current = true;
    setHasDraft(true);
    setSelections(update);
  }
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  useEffect(() => {
    company.current = instrumentId;
    let active = true;
    const token = ++requestVersion.current;
    if (visible && !actionBusy.current)
      api
        .fmp(instrumentId)
        .then((result) => {
          if (active && mounted.current && requestVersion.current === token) {
            setData(result);
            if (!dirty.current) setSelections(result.selected);
            setError("");
          }
        })
        .catch((failure) => {
          if (active && mounted.current && requestVersion.current === token)
            setError(failure.message);
        });
    return () => {
      active = false;
    };
  }, [instrumentId, visible]);
  async function act(save = false) {
    if (actionBusy.current) return;
    actionBusy.current = true;
    requestVersion.current++;
    const id = instrumentId;
    setBusy(true);
    setError("");
    try {
      const result = save
        ? await api.savePeers(id, selections)
        : (await api.refreshFmp(id)).context;
      if (mounted.current && company.current === id) {
        setData(result);
        if (save) {
          dirty.current = false;
          setHasDraft(false);
          setSelections(result.selected);
        } else if (!dirty.current) setSelections(result.selected);
      }
    } catch (failure) {
      if (mounted.current && company.current === id) setError(failure.message);
    } finally {
      actionBusy.current = false;
      if (mounted.current && company.current === id) setBusy(false);
    }
  }
  async function checkPublic() {
    if (actionBusy.current) return;
    actionBusy.current = true;
    requestVersion.current++;
    const id = instrumentId;
    setBusy(true);
    setError("");
    try {
      const result = await api.refreshPublicForecasts(id);
      if (mounted.current && company.current === id) setData(result);
    } catch (failure) {
      if (mounted.current && company.current === id) setError(failure.message);
    } finally {
      actionBusy.current = false;
      if (mounted.current && company.current === id) setBusy(false);
    }
  }
  const candidates = [
    ...(data?.suggestions?.data?.candidates || []),
    ...(data?.registered || []),
  ].filter(
    (item, i, all) =>
      all.findIndex((other) => other.symbol === item.symbol) === i,
  );
  if (mode === "outlook")
    return (
      <AnalystForecasts
        data={data}
        busy={busy}
        error={error}
        onCheck={() => act()}
        onCheckPublic={checkPublic}
      />
    );
  if (mode === "ratios")
    return (
      <details className="comparison-ratios">
        <summary>
          Other comparison measures · valuation ratios &amp; cash flow
        </summary>
        <p>
          Saved peer choices, with each provider and period kept separate. Edit
          the group above.
        </p>
        {error && <p role="alert">{error}</p>}
        <button disabled={busy} onClick={() => act()}>
          {busy ? "Checking…" : "Check FMP data"}
        </button>
        {data && (
          <Suspense fallback={<p>Loading saved measures…</p>}>
            <PeerComparison
              members={data.members}
              symbol={data.symbol}
              exclude={["pe_finnhub", "growth_sec"]}
            />
          </Suspense>
        )}
        <SourceState source={data?.ratios} />
      </details>
    );
  return (
    <section
      className="fmp-panel"
      aria-label={mode === "peers" ? "Comparison peers" : "Analyst forecasts"}
    >
      <div className="financial-heading">
        <h2>{mode === "peers" ? "Compare companies" : "Analyst forecasts"}</h2>
        <button disabled={busy} onClick={() => act()}>
          {busy ? "Checking…" : "Check FMP data"}
        </button>
      </div>
      {error && <p role="alert">{error}</p>}
      <details className="secondary-details source-details">
        <summary>Data source details</summary>
        <p>
          Data access depends on your FMP subscription. Checking data makes no
          AI request.
        </p>
        {data?.profile?.data && (
          <p>
            FMP classification: {data.profile.data.sector} ·{" "}
            {data.profile.data.industry}.{" "}
            {readableNote(data.profile.data.limitation)}
          </p>
        )}
      </details>
      {mode === "peers" && (
        <>
          <section className="business-topic">
            <h3>Choose useful comparisons</h3>
            <SourceState source={data?.suggestions} />
            <p>
              {data?.suggestions?.data?.basis ||
                "Review the company’s products, customers and financial definitions before selecting a peer."}
            </p>
            {selections.map((selection, index) => (
              <div className="peer-editor" key={index}>
                <label>
                  Company
                  <Select
                    aria-label={`Comparison company ${index + 1}`}
                    value={selection.symbol}
                    disabled={busy}
                    onChange={(event) =>
                      editSelections((old) =>
                        old.map((item, i) =>
                          i === index
                            ? { ...item, symbol: event.target.value }
                            : item,
                        ),
                      )
                    }
                  >
                    <option value="">Choose a company</option>
                    {candidates.map((candidate) => (
                      <option key={candidate.symbol} value={candidate.symbol}>
                        {candidate.symbol} · {candidate.name}
                      </option>
                    ))}
                  </Select>
                </label>
                <label>
                  Why is this comparison useful?
                  <textarea
                    value={selection.rationale}
                    minLength={8}
                    maxLength={600}
                    disabled={busy}
                    onChange={(event) =>
                      editSelections((old) =>
                        old.map((item, i) =>
                          i === index
                            ? { ...item, rationale: event.target.value }
                            : item,
                        ),
                      )
                    }
                  />
                </label>
                <button
                  disabled={busy}
                  onClick={() =>
                    editSelections((old) => old.filter((_, i) => i !== index))
                  }
                >
                  Remove comparison
                </button>
              </div>
            ))}
            <div className="peer-actions">
              <button
                disabled={busy || selections.length >= 8 || !candidates.length}
                onClick={() =>
                  editSelections((old) => [
                    ...old,
                    { symbol: "", rationale: "" },
                  ])
                }
              >
                Add comparison company
              </button>
              <button
                disabled={
                  busy ||
                  !data ||
                  selections.some(
                    (item) => !item.symbol || item.rationale.trim().length < 8,
                  )
                }
                onClick={() => act(true)}
              >
                Save comparisons
              </button>
              {hasDraft && (
                <button
                  disabled={busy}
                  onClick={() => {
                    dirty.current = false;
                    setHasDraft(false);
                    setSelections(data?.selected || []);
                  }}
                >
                  Discard changes
                </button>
              )}
            </div>
            {hasDraft && (
              <p role="status">
                Unsaved comparison changes. The chart uses your saved choices
                until you save.
              </p>
            )}
            <p>
              Choose up to eight useful peers and explain the overlap. Saving
              does not collect data; use Check FMP data afterwards.
            </p>
          </section>
          {data && (
            <Suspense fallback={<p role="status">Loading peer comparison…</p>}>
              <PeerComparison members={data.members} symbol={data.symbol} />
            </Suspense>
          )}
          {!!data?.members?.length && (
            <details className="peer-sources">
              <summary>
                Data behind the comparison · {data.members.length}{" "}
                {data.members.length === 1 ? "company" : "companies"}
              </summary>
              <div className="peer-comparisons">
                {data?.members?.map((member) => (
                  <section key={member.symbol} className="peer-card">
                    <h3>
                      {member.symbol}
                      {member.symbol === data.symbol
                        ? " · selected company"
                        : ""}
                    </h3>
                    {member.rationale && <p>{member.rationale}</p>}
                    <SourceState source={member.profile} />
                    {member.profile.data && (
                      <p>
                        {member.profile.data.name} ·{" "}
                        {member.profile.data.currency || "currency unavailable"}{" "}
                        · {member.profile.data.industry}
                      </p>
                    )}
                    <SourceState source={member.ratios} />
                    {member.ratios.data?.metrics?.map((metric) => (
                      <p key={metric.key}>
                        {metric.label}: {figure(metric.value)}
                        {metric.reason && ` · ${metric.reason}`}
                      </p>
                    ))}
                    {member.ratios.data && (
                      <p className="financial-note">
                        {member.ratios.data.basis}
                      </p>
                    )}
                    {member.saved_finnhub && (
                      <details>
                        <summary>Saved Finnhub trailing references</summary>
                        <p>
                          Retrieved {stamp(member.saved_finnhub.retrieved_at)}.
                          These use Finnhub’s own definitions; compare within
                          this section rather than mixing vendors.
                        </p>
                        <p>
                          P/E (TTM)
                          <TermHelp term="pe" />:{" "}
                          {figure(member.saved_finnhub.metrics.earnings.value)}
                        </p>
                        <p>
                          P/S (TTM):{" "}
                          {figure(member.saved_finnhub.metrics.sales.value)}
                        </p>
                      </details>
                    )}
                    {member.financials?.status === "available" && (
                      <details>
                        <summary>Saved SEC financial measures</summary>
                        <p>
                          Period ended {member.financials.period_end}. Fiscal
                          periods can differ between companies.
                        </p>
                        {member.financials.trailing
                          .filter((metric) =>
                            [
                              "revenue",
                              "operating_margin",
                              "free_cash_flow",
                            ].includes(metric.key),
                          )
                          .map((metric) => (
                            <p key={metric.key}>
                              {metric.label}: {figure(metric.value)}{" "}
                              {metric.unit}. {metric.reason}
                            </p>
                          ))}
                      </details>
                    )}
                  </section>
                ))}
              </div>
              {data && (
                <p className="financial-note">
                  {readableNote(data.limitation)}
                </p>
              )}
            </details>
          )}
        </>
      )}
    </section>
  );
}
