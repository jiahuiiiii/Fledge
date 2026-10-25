import { formatTimestamp } from "../lib/dateTime";
import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import FinancialHistory from "./FinancialHistory";
import Modal from "./Modal";
import Select from "./Select";
import Checkbox from "./Checkbox";
import { day, metric, number } from "../lib/financialStory";
import { profitOptions, consistentProfitRows } from "../lib/profitHistory";
import { requestUpdate } from "../lib/updateRequest";
import {
  chartForecasts,
  forecastAmount,
  forecastSources,
  forecastTakeaway,
  horizonLabel,
  quarterlyHistory,
} from "../lib/revenueForecasts";
import "./RevenueHistory.css";

const stamp = (value) =>
  formatTimestamp(value, { fallback: "Date not supplied" });

export default function RevenueHistory({
  instrumentId,
  workspace,
  story,
  visible,
  series,
  revision,
}) {
  const [kind, setKind] = useState("annual"),
    [selected, setSelected] = useState("");
  const [profitChoice, setProfitChoice] = useState(null);
  const [context, setContext] = useState(null),
    [error, setError] = useState("");
  const [sourceKey, setSourceKey] = useState(""),
    [declinedSource, setDeclinedSource] = useState(null);
  const [evidence, setEvidence] = useState(null),
    [attempt, setAttempt] = useState(0);
  const generation = useRef(0);
  useEffect(() => {
    if (!visible) return;
    const token = ++generation.current;
    api
      .fmp(instrumentId)
      .then((result) => {
        if (token === generation.current) {
          setContext({ instrumentId, result });
          setError("");
        }
      })
      .catch((failure) => {
        if (token === generation.current) {
          setContext(null);
          setError(failure.message);
        }
      });
    return () => {
      generation.current++;
    };
  }, [instrumentId, visible, revision, workspace.management_outlook, attempt]);
  const sources =
    context?.instrumentId === instrumentId ? context.result : null;
  const { groups, guidance } = forecastSources(
    sources,
    workspace.management_outlook,
  );
  const analyst = groups.find((g) => g.key === sourceKey) || groups[0];
  const reportedRows =
    kind === "quarter"
      ? story?.status === "available" && Array.isArray(story.quarterly)
        ? story.quarterly
        : quarterlyHistory(workspace.income_flow)
      : story?.status === "available"
        ? story[kind] || []
        : [];
  const profitChoices = profitOptions(story);
  const profit =
    profitChoices.find(
      (choice) =>
        profitChoice?.instrumentId === instrumentId &&
        choice.key === profitChoice.key,
    ) || profitChoices[0];
  const rows = consistentProfitRows(reportedRows, profit?.key);
  const active = rows.find((r) => r.id === selected) || rows.at(-1);
  const points = [...(analyst?.points || []), ...guidance];
  const assumptionKey = JSON.stringify(
    points
      .filter((p) => p.periodKind === kind && !p.currency)
      .map((p) => [p.id, p.observedAt, p.value, p.low, p.high]),
  );
  // On by default: estimates with no stated currency are plotted as USD and
  // marked as assumed; the reader can switch the assumption off.
  const assumeUSD = declinedSource !== assumptionKey;
  const { plotted, excluded } = chartForecasts(points, rows, kind, assumeUSD);
  const pendingCurrency = excluded.filter(
    (p) => !p.currency && p.reason === "The source does not state a currency.",
  );
  const hasAssumed = plotted.some((p) => p.assumedCurrency);
  const summaries = ["analyst", "management"]
    .map(
      (type) =>
        plotted.find((p) => p.kind === type) ||
        excluded.find((p) => p.kind === type),
    )
    .filter(Boolean);
  const otherGuidance = guidance.find(
    (p) =>
      p.periodKind !== kind &&
      ["annual", "quarter"].includes(p.periodKind) &&
      p.end &&
      Date.parse(p.end) >
        Date.parse(
          workspace.income_flow?.periods
            ?.filter((r) => r.kind === p.periodKind)
            .sort((a, b) => Date.parse(b.end) - Date.parse(a.end))[0]?.end ||
            "1900-01-01",
        ),
  );
  const chartSeries =
    kind === "quarter"
      ? series.filter((s) =>
          ["revenue", "net_income", "operating_income"].includes(s.key),
        )
      : series;
  function changeKind(value) {
    setKind(value);
    setSelected("");
    setEvidence(null);
  }
  // Revalidate a selected dialog against the current permitted source responses.
  const selectedEvidence =
    evidence && [...plotted, ...excluded].find((p) => p.id === evidence);
  return (
    <div className="revenue-history">
      <header className="revenue-history-heading">
        <div>
          <h2>Sales over time &amp; outlook</h2>
          <p>
            Reported results, followed by what analysts and management expect.
          </p>
        </div>
        <div
          className="revenue-history-periods"
          role="group"
          aria-label="Revenue chart period"
        >
          {[
            ["annual", "Fiscal year"],
            ["quarter", "Quarterly"],
            ["trailing", "Past 12 months"],
          ].map(([key, label]) => (
            <button
              key={key}
              aria-pressed={kind === key}
              onClick={() => changeKind(key)}
            >
              {label}
            </button>
          ))}
        </div>
      </header>
      <div className="revenue-forecast-controls">
        <p>{horizonLabel(kind)} · reported revenue in US dollars</p>
        {groups.length > 1 && (
          <label>
            Analyst source
            <Select
              aria-label="Revenue forecast source"
              value={analyst.key}
              onChange={(event) => setSourceKey(event.target.value)}
            >
              {groups.map((group) => (
                <option key={group.key} value={group.key}>
                  {group.label}
                </option>
              ))}
            </Select>
          </label>
        )}
      </div>
      {profit && (
        <div className="revenue-profit-definition">
          {profitChoices.length > 1 ? (
            <label>
              Profit shown
              <Select
                aria-label="Profit shown"
                value={profit.key}
                onChange={(event) =>
                  setProfitChoice({ instrumentId, key: event.target.value })
                }
              >
                {profitChoices.map((choice) => (
                  <option key={choice.key} value={choice.key}>
                    {choice.label}
                  </option>
                ))}
              </Select>
            </label>
          ) : (
            <span>Profit shown: {profit.label.toLowerCase()}</span>
          )}
          <p>
            {profit.key === "net_parent"
              ? "The profit or loss belonging to the parent company."
              : "Includes other owners’ share of subsidiaries."}{" "}
            The same definition is used for every date.
          </p>
        </div>
      )}
      {kind === "trailing" ? (
        <p className="revenue-forecast-note">
          Past 12 months combines the latest four quarters. Forecasts cover a
          fiscal year or a quarter; choose one of those views to compare them.
        </p>
      ) : (
        <>
          {(pendingCurrency.length > 0 || hasAssumed) && (
            <div className="revenue-currency-choice">
              <label>
                <Checkbox
                  checked={assumeUSD}
                  onChange={(event) =>
                    setDeclinedSource(
                      event.target.checked ? null : assumptionKey,
                    )
                  }
                />
                Plot estimates with unstated currency as USD
              </label>
              <p>
                {hasAssumed
                  ? "Marked estimates assume USD; their source doesn’t state a currency."
                  : "Estimates with no stated currency are off the chart while this is unticked."}
              </p>
            </div>
          )}
          {!context && !error && (
            <p className="revenue-forecast-note" role="status">
              Reading saved analyst forecasts…
            </p>
          )}
          {error && (
            <p className="revenue-forecast-note" role="status">
              Saved analyst forecasts could not be read.{" "}
              <button onClick={() => setAttempt((n) => n + 1)}>
                Try again
              </button>
            </p>
          )}
        </>
      )}
      <FinancialHistory
        key={kind}
        rows={rows}
        series={chartSeries}
        active={active}
        onSelect={setSelected}
        label="Sales, earnings and cash flow"
        forecasts={plotted}
        periodKind={kind}
        onForecast={(point) => setEvidence(point.id)}
      />
      {kind !== "trailing" && (
        <>
          <div className="revenue-forecast-readings">
            {summaries.map((point) => (
              <article
                key={point.id}
                className={`revenue-forecast-reading forecast-${point.kind}`}
              >
                <div>
                  <span className="forecast-type">
                    {point.kind === "analyst"
                      ? "Analyst forecast"
                      : "Management guidance"}
                  </span>
                  {point.assumedCurrency && (
                    <span className="forecast-assumption">USD assumed</span>
                  )}
                </div>
                <p>{forecastTakeaway(point, rows)}</p>
                {Date.parse(point.end) < Date.now() && (
                  <p className="forecast-range-caption">
                    This period has ended; its reported result is not saved yet.
                  </p>
                )}
                {point.low !== point.high && (
                  <p className="forecast-range-caption">
                    {point.kind === "analyst"
                      ? "Analyst low–high"
                      : "Management range"}
                    :{" "}
                    {forecastAmount(
                      point.low,
                      point.assumedCurrency ? "USD" : point.currency,
                    )}{" "}
                    –{" "}
                    {forecastAmount(
                      point.high,
                      point.assumedCurrency ? "USD" : point.currency,
                    )}
                    {point.kind === "management" &&
                      "; plotted point is the midpoint."}
                  </p>
                )}
                {point.reason && (
                  <p className="forecast-range-caption">
                    Not plotted: {point.reason}
                  </p>
                )}
                <button
                  className="forecast-source-link"
                  aria-haspopup="dialog"
                  onClick={() => setEvidence(point.id)}
                >
                  {point.sourceLabel} ·{" "}
                  {day(
                    point.publishedAt || point.updatedOn || point.observedAt,
                  )}{" "}
                  ↗
                </button>
              </article>
            ))}
          </div>
          {otherGuidance && (
            <p className="revenue-other-guidance">
              Management also gives{" "}
              {otherGuidance.periodKind === "quarter" ? "quarterly" : "annual"}{" "}
              guidance.{" "}
              <button onClick={() => changeKind(otherGuidance.periodKind)}>
                View{" "}
                {otherGuidance.periodKind === "quarter"
                  ? "quarterly"
                  : "fiscal-year"}{" "}
                outlook →
              </button>
            </p>
          )}
          {context && !analyst?.points.length && (
            <p className="revenue-forecast-note">
              No saved analyst revenue forecast.{" "}
              <button onClick={requestUpdate}>Update data →</button>
            </p>
          )}
          {analyst?.points.length > 0 &&
            !points.some(
              (p) =>
                p.kind === "analyst" &&
                p.periodKind === kind &&
                Date.parse(p.end) >
                  Date.parse(rows.at(-1)?.end || "1900-01-01"),
            ) && (
              <p className="revenue-forecast-note">
                {kind === "quarter"
                  ? "The saved analyst forecasts are annual. Choose Fiscal year to see them."
                  : "No saved analyst forecast extends beyond the latest reported year."}
              </p>
            )}
          {summaries.some((p) => p.stale || p.sourceError) && (
            <p className="revenue-forecast-note">
              Using saved forecasts. Source dates and the latest check are
              available through each source link.
            </p>
          )}
          {!!plotted.length && (
            <p className="revenue-forecast-note">
              Estimates may change. Dotted lines join reporting periods; they do
              not predict revenue between those dates.
            </p>
          )}
        </>
      )}
      <Modal
        open={!!selectedEvidence}
        onClose={() => setEvidence(null)}
        title={
          selectedEvidence?.kind === "analyst"
            ? "Analyst revenue forecast"
            : "Management revenue guidance"
        }
        className="revenue-forecast-dialog"
      >
        {selectedEvidence && (
          <ForecastEvidence point={selectedEvidence} rows={rows} />
        )}
      </Modal>
    </div>
  );
}

function ForecastEvidence({ point, rows }) {
  const reported = metric(rows.at(-1), "revenue");
  const publicPage = point.source === "public";
  const earlierPageDate =
    publicPage &&
    point.updatedOn &&
    point.observedAt &&
    point.updatedOn < new Date(point.observedAt).toISOString().slice(0, 10);
  const basis = [
    "source revenue convention",
    "Source revenue definition",
  ].includes(point.basis)
    ? "Not specified by the source"
    : point.basis === "gaap"
      ? "GAAP"
      : point.basis;
  return (
    <div className="revenue-forecast-evidence">
      <p className="forecast-type">
        {point.sourceLabel} · {horizonLabel(point.periodKind)} ending{" "}
        {day(point.end)}
      </p>
      <strong className="forecast-evidence-value">
        {forecastAmount(
          point.value,
          point.assumedCurrency ? "USD" : point.currency,
          point.approximate,
        )}
      </strong>
      <p>
        {point.kind === "analyst"
          ? "Analysts’ average revenue estimate"
          : point.low !== point.high
            ? "Midpoint of management’s guidance range"
            : "Management’s revenue guidance"}{" "}
        — not a reported result.
      </p>
      {point.low !== point.high && (
        <p>
          Low–high: {forecastAmount(point.low, point.currency)} –{" "}
          {forecastAmount(point.high, point.currency)}.
        </p>
      )}
      {!point.currency && (
        <p>
          {point.assumedCurrency
            ? "You chose to plot this estimate as USD. The original source does not state its currency."
            : "The source does not state its currency, so it is not joined to reported USD revenue."}
        </p>
      )}
      {point.reason && <p>{point.reason}</p>}
      {earlierPageDate && (
        <p className="forecast-date-note">
          This page was checked on {stamp(point.observedAt)}. The publisher
          still lists {day(point.updatedOn)} as its update date.
        </p>
      )}
      <dl>
        <div>
          <dt>Revenue definition</dt>
          <dd>{basis}</dd>
        </div>
        <div>
          <dt>
            {publicPage
              ? "Publisher page updated"
              : point.kind === "management"
                ? "Release date"
                : "Forecast date"}
          </dt>
          <dd>
            {point.publishedAt || point.updatedOn
              ? day(point.publishedAt || point.updatedOn)
              : "Not supplied"}
          </dd>
        </div>
        <div>
          <dt>{publicPage ? "Page checked & saved" : "Saved"}</dt>
          <dd>
            {stamp(point.observedAt)}
            {point.stale ? " · over a day old" : ""}
          </dd>
        </div>
        {point.kind === "analyst" && point.checkedAt && (
          <div>
            <dt>Latest source check</dt>
            <dd>{stamp(point.checkedAt)}</dd>
          </div>
        )}
        {point.kind === "analyst" && (
          <div>
            <dt>Contributing analysts</dt>
            <dd>
              {point.analysts ??
                (point.tableAnalysts
                  ? `${point.tableAnalysts} for the source’s annual table; revenue contributors not specified`
                  : "Not supplied")}
            </dd>
          </div>
        )}
      </dl>
      {point.kind === "analyst" && (
        <p>
          Dates for individual analysts’ forecasts are not supplied. These
          figures cannot establish a historical beat-or-miss comparison.
        </p>
      )}
      {point.quote && <blockquote>{point.quote}</blockquote>}
      {point.context?.length > 0 && (
        <details>
          <summary>Read the guidance in context</summary>
          {point.context.map((p) => (
            <p key={p.id}>{p.quote}</p>
          ))}
        </details>
      )}
      {number(reported?.value) != null && (
        <p>
          Latest reported revenue:{" "}
          {forecastAmount(reported.value, reported.unit)} ·{" "}
          {day(reported.start)} – {day(reported.end)}.
        </p>
      )}
      {point.sourceError && <p>Latest source check: {point.sourceError}</p>}
      {point.restrictedYears?.length > 0 && (
        <p>
          The source does not provide public figures for{" "}
          {point.restrictedYears.join(", ")}.
        </p>
      )}
      {point.url && (
        <a href={point.url} target="_blank" rel="noreferrer">
          Open original{" "}
          {point.kind === "analyst" ? "forecast tables" : "earnings release"} ↗
        </a>
      )}
    </div>
  );
}
