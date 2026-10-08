import LoadingSkeleton from "./LoadingSkeleton";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import PriceChart from "./PriceChart";
import { stamp } from "./MarketResearch";
import { readableLoad } from "../lib/loading";
export default function HistoricalPrices({
  instrumentId,
  initialRead,
  loadStep,
}) {
  const [data, setData] = useState(initialRead?.data || null),
    [error, setError] = useState(initialRead?.error || "");
  useEffect(() => {
    if (initialRead) {
      setData(initialRead.data);
      setError(initialRead.error);
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
        <span className="fine">Included in Refresh research</span>
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
          <PriceChart key={snapshot.id} prices={bars} fictional={false} />
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
              York dates) · retrieved {stamp(snapshot.retrieved_at)}.
              Current-day bars are excluded; this is not a live chart.
            </p>
            <p className="fine">
              Manual refresh · at most once per hour · no AI call.{" "}
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
              {series.requested_end_exclusive} (exclusive), America/New_York.
              Reading this table makes no source request.
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
