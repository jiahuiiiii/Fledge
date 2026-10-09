import LoadingSkeleton from "./LoadingSkeleton";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import PriceChart from "./PriceChart";
import { stamp } from "./MarketResearch";
import { readableLoad } from "../lib/loading";
import { preferPriceRead, priceRefreshDelay } from "../lib/priceRefresh";
export default function HistoricalPrices({
  instrumentId,
  initialRead,
  loadStep,
  visible = false,
  onRead,
}) {
  const [data, setData] = useState(initialRead?.data || null),
    [error, setError] = useState(initialRead?.error || "");
  const [checking, setChecking] = useState(false);
  const [paused, setPaused] = useState(false);
  const [pageVisible, setPageVisible] = useState(!document.hidden);
  const generation = useRef(0);
  const inFlight = useRef(false);
  useEffect(() => {
    const token = ++generation.current;
    const changed = () => setPageVisible(!document.hidden);
    document.addEventListener("visibilitychange", changed);
    return () => {
      if (generation.current === token) generation.current++;
      document.removeEventListener("visibilitychange", changed);
    };
  }, [instrumentId]);
  useEffect(() => {
    if (initialRead) {
      if (!initialRead.data) {
        if (initialRead.error) setError(initialRead.error);
        return;
      }
      const newer =
        Date.parse(initialRead.data.snapshot?.retrieved_at) >
        (Date.parse(data?.snapshot?.retrieved_at) || 0);
      setData((old) => preferPriceRead({ data: old }, initialRead)?.data);
      if (initialRead.error) setError(initialRead.error);
      else if (newer && !initialRead.data.error) {
        setError("");
        setPaused(false);
      }
      return;
    }
    let active = true;
    setData(null);
    setError("");
    readableLoad(api.priceHistory(instrumentId))
      .then((d) => {
        if (active) setData(d);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [instrumentId, initialRead]);
  const refreshPrices = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    const token = generation.current;
    setChecking(true);
    setError("");
    try {
      // Read shared state first: another tab or Refresh research may have
      // checked recently. Reuse it instead of competing for the source lease.
      let next = await api.priceHistory(instrumentId);
      if (token !== generation.current) return;
      if (
        priceRefreshDelay({ ...next, error: null }) === 0 &&
        !next.refreshing
      ) {
        await api.refreshPriceHistory(instrumentId);
        next = await api.priceHistory(instrumentId);
      }
      if (token !== generation.current) return;
      setData((old) => preferPriceRead({ data: old }, { data: next })?.data);
      onRead?.({ data: next, error: "" });
      setPaused(!!next.error);
    } catch (failure) {
      if (token === generation.current) {
        setError(failure.message);
        setPaused(true);
      }
    } finally {
      inFlight.current = false;
      if (token === generation.current) setChecking(false);
    }
  }, [instrumentId, onRead]);
  useEffect(() => {
    if (!visible || !pageVisible || paused || checking) return;
    const delay = priceRefreshDelay(data);
    if (delay == null) return;
    const timer = setTimeout(refreshPrices, Math.max(1000, delay));
    return () => clearTimeout(timer);
  }, [data, visible, pageVisible, paused, checking, refreshPrices]);
  const snapshot = data?.snapshot,
    series = snapshot?.series;
  const bars =
    series?.bars.map((p) => ({
      ...p,
      open: Number(p.open),
      high: Number(p.high),
      low: Number(p.low),
      close: Number(p.close),
      volume: p.volume == null ? null : Number(p.volume),
    })) || [];
  return (
    <section className="historical-prices" aria-label="Daily price history">
      <div className="market-section-head">
        <div>
          <span className="section-label">DAILY PRICE CONTEXT</span>
          <span className="fine"> · Yahoo Finance</span>
        </div>
        <button
          onClick={refreshPrices}
          disabled={checking || !data?.available || !data?.configured}
        >
          {checking ? "Checking prices…" : "Refresh prices"}
        </button>
      </div>
      {error && (
        <p className="warning" role="alert">
          {error}
        </p>
      )}
      {!data && !error && (
        <LoadingSkeleton variant="chart" label="Reading saved daily history…" />
      )}
      {data && !data.available && (
        <p className="warning">
          Price-history source access is unavailable. Saved chart data is
          withheld.
        </p>
      )}
      {data?.error && data.error !== error && (
        <p className="warning">{data.error}</p>
      )}
      {data?.refreshing && (
        <p role="status">A daily-history check is in progress.</p>
      )}
      {series && (
        <p className="fine" role="status">
          Latest session {bars.at(-1)?.date} · checked{" "}
          {stamp(snapshot.retrieved_at)}.
          {paused || data?.error
            ? " Updates paused after a failed check. Choose Refresh prices to try again."
            : !data?.configured
              ? " Price checks are unavailable while this source connection is disabled."
              : " Updates every minute while this chart is open and visible."}
          {series.delay_minutes > 0
            ? ` Yahoo reports a ${series.delay_minutes}-minute data delay.`
            : " Data may be delayed by the source."}
        </p>
      )}
      {data?.available &&
        !snapshot &&
        ["queued", "running"].includes(loadStep?.status) && (
          <LoadingSkeleton
            variant="chart"
            label={
              loadStep.status === "queued"
                ? "Price chart queued…"
                : "Fetching daily prices…"
            }
          />
        )}
      {data?.available &&
        !snapshot &&
        !["queued", "running"].includes(loadStep?.status) && (
          <p className="muted">
            {loadStep?.message ||
              "Preparing the price chart. Source checks start automatically when you open this company."}
          </p>
        )}
      {series && (
        <>
          <PriceChart prices={bars} fictional={false} />
          {data.check_stale && (
            <p className="warning">
              Daily history was last checked more than 24 hours ago. Refresh it
              for a newer check.
            </p>
          )}
          {series.old_last_session && (
            <p className="warning">
              The supplied history ends more than seven days before the
              requested cutoff.
            </p>
          )}
          {series.partial_window && (
            <p className="warning">
              The source supplied less than the requested year of history. The
              chart shows the available dates.
            </p>
          )}
          {(series.omitted_sessions > 0 ||
            series.missing_volume_sessions > 0) && (
            <p className="warning">
              {series.omitted_sessions} incomplete price rows omitted;{" "}
              {series.missing_volume_sessions} sessions have no reported volume.
              Missing values are not zero.
            </p>
          )}
          <details>
            <summary>Inspect daily prices and source</summary>
            <p className="fine">
              {bars.length} supplied sessions · through {bars.at(-1)?.date} (New
              York dates) · retrieved {stamp(snapshot.retrieved_at)}. Today's
              supplied session is included. A provisional bar shows the latest
              supplied session price, not a final daily close.
            </p>
            <p className="fine">
              Price-only checks · at most once per minute · no AI call.{" "}
              {data?.next_refresh_at
                ? `Next refresh available ${stamp(data.next_refresh_at)}.`
                : ""}
            </p>
            <p className="fine">
              {series.basis} Changes shown are price changes, not total
              investment returns. No company news or sentiment is used to
              calculate this chart.
            </p>
            <p className="fine">
              1M, 3M and 6M show the latest 21, 63 and 126 available sessions;
              1Y shows the available requested year. Inspect the actual date
              range below the chart. Lines connect supplied sessions; no missing
              day is filled in.
            </p>
            <p className="fine">
              Requested {series.requested_start} to{" "}
              {series.requested_through ||
                `${series.requested_end_exclusive} (exclusive)`}
              , America/New_York. Reading this table makes no source request.
            </p>
            <a href={data.source_url} target="_blank" rel="noreferrer">
              Yahoo Finance history ↗
            </a>
            <div className="price-table-wrap">
              <table>
                <caption>Stored daily USD prices · {data.symbol}</caption>
                <thead>
                  <tr>
                    {["Date", "Open", "High", "Low", "Close", "Volume"].map(
                      (h) => (
                        <th key={h} scope="col">
                          {h}
                        </th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {series.bars
                    .slice()
                    .reverse()
                    .map((p) => (
                      <tr key={p.date}>
                        <th scope="row">{p.date}</th>
                        {["open", "high", "low", "close"].map((k) => (
                          <td key={k}>{Number(p[k]).toFixed(2)}</td>
                        ))}
                        <td>
                          {p.volume == null
                            ? "Unknown"
                            : Number(p.volume).toLocaleString("en-US")}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </details>
        </>
      )}
    </section>
  );
}
