import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import Select from "./Select";
import PublicForecasts from "./PublicForecasts";
const PeerComparison = lazy(() => import("./PeerComparison"));
const stamp = (value) =>
  value ? new Date(value).toLocaleString("en-GB") : "Not collected";
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
      {source?.checked_at && (
        <p className="financial-note">
          First observed {stamp(source.first_observed_at)} · last checked{" "}
          {stamp(source.checked_at)}
        </p>
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
      <p>
        Data access depends on your FMP subscription. Checking data makes no AI
        request.
      </p>
      {error && <p role="alert">{error}</p>}
      {data?.profile?.data && (
        <p>
          FMP classification: {data.profile.data.sector} ·{" "}
          {data.profile.data.industry}. {data.profile.data.limitation}
        </p>
      )}
      {mode === "outlook" && (
        <>
          <section className="business-topic">
            <h3>FMP financial expectations</h3>
            <SourceState source={data?.consensus} />
            {!data?.consensus?.data &&
              !data?.public_forecasts?.snapshot &&
              data?.symbol && (
                <p className="financial-note">
                  <a
                    href={`https://stockanalysis.com/stocks/${encodeURIComponent(data.symbol.toLowerCase())}/forecast/`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Inspect public financial forecasts on Stock Analysis ↗
                  </a>{" "}
                  This opens the source separately. Some years require
                  membership; its EPS forecasts use adjusted earnings. Use the
                  public forecast check below to save the available annual
                  table.
                </p>
              )}
            {data?.consensus?.data?.forecasts?.map((forecast) => (
              <section key={forecast.period_end}>
                <h4>Annual period ending {forecast.period_end}</h4>
                <p>
                  Currency: {forecast.currency || "not supplied by provider"}
                </p>
                {forecast.metrics.map((metric) => (
                  <p key={metric.key}>
                    {metric.key === "eps" ? "Earnings per share" : "Revenue"}:
                    average {figure(metric.average)} · low {figure(metric.low)}{" "}
                    · high {figure(metric.high)} ·{" "}
                    {metric.analysts == null
                      ? "analyst count unavailable"
                      : `${metric.analysts} analysts`}
                  </p>
                ))}
              </section>
            ))}
            <p className="financial-note">
              {data?.consensus?.data?.limitation ||
                "Consensus is separate from management guidance and price targets. Missing forecasts remain unknown."}
            </p>
            {data?.consensus_history?.length > 0 && (
              <details>
                <summary>Saved forecast vintages</summary>
                {data.consensus_history.map((vintage) => (
                  <section key={vintage.id}>
                    <p>First observed {stamp(vintage.available_at)}</p>
                    {vintage.data.forecasts.map((forecast) => (
                      <p key={forecast.period_end}>
                        Period ending {forecast.period_end} · revenue average{" "}
                        {figure(
                          forecast.metrics.find(
                            (metric) => metric.key === "revenue",
                          )?.average,
                        )}{" "}
                        · EPS average{" "}
                        {figure(
                          forecast.metrics.find(
                            (metric) => metric.key === "eps",
                          )?.average,
                        )}{" "}
                        · currency {forecast.currency || "unspecified"}
                      </p>
                    ))}
                  </section>
                ))}
              </details>
            )}
          </section>
          <PublicForecasts
            source={data?.public_forecasts}
            busy={busy}
            onRefresh={checkPublic}
          />
        </>
      )}
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
                disabled={busy || selections.length >= 3 || !candidates.length}
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
              Choose two or three useful peers and explain the overlap. Saving
              does not collect data; use Check FMP data afterwards.
            </p>
          </section>
          {data && (
            <Suspense fallback={<p role="status">Loading peer comparison…</p>}>
              <PeerComparison members={data.members} symbol={data.symbol} />
            </Suspense>
          )}
          <div className="peer-comparisons">
            {data?.members?.map((member) => (
              <section key={member.symbol} className="peer-card">
                <h3>
                  {member.symbol}
                  {member.symbol === data.symbol ? " · selected company" : ""}
                </h3>
                {member.rationale && <p>{member.rationale}</p>}
                <SourceState source={member.profile} />
                {member.profile.data && (
                  <p>
                    {member.profile.data.name} ·{" "}
                    {member.profile.data.currency || "currency unavailable"} ·{" "}
                    {member.profile.data.industry}
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
                  <p className="financial-note">{member.ratios.data.basis}</p>
                )}
                {member.saved_finnhub && (
                  <details>
                    <summary>Saved Finnhub trailing references</summary>
                    <p>
                      Retrieved {stamp(member.saved_finnhub.retrieved_at)}.
                      These use Finnhub’s own definitions; compare within this
                      section rather than mixing vendors.
                    </p>
                    <p>
                      P/E (TTM):{" "}
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
                          {metric.label}: {figure(metric.value)} {metric.unit}.{" "}
                          {metric.reason}
                        </p>
                      ))}
                  </details>
                )}
              </section>
            ))}
          </div>
          {data && <p className="financial-note">{data.limitation}</p>}
        </>
      )}
    </section>
  );
}
