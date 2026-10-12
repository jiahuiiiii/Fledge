import { formatTimestamp } from "../lib/dateTime";
import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { companyName } from "../lib/companyIdentity";
import { day, money, percent } from "../lib/companySnapshot";
import {
  overviewModel,
  segmentEvidence,
  guidanceAmount,
  guidanceReason,
  guidancePeriod,
  guidanceStatusLabel,
  multiple,
  number,
  yearLabel,
} from "../lib/overviewSections";
import FinancialEvidence from "./FinancialEvidence";
import Modal from "./Modal";
import TermHelp from "./TermHelp";
import { SourceIcon } from "./SourceFilters";
import { growthTakeaway, peTakeaway } from "../lib/overviewTakeaways";
import "./OverviewSections.css";

const fallback = (value) => value ?? "Not available";
const stamp = (value) => formatTimestamp(value, { fallback: "Not checked" });
function Reading({ children, limit }) {
  return (
    <div className="overview-reading">
      <p>{children}</p>
      {limit && <p className="overview-limit">{limit}</p>}
    </div>
  );
}
function Section({ number, title, children }) {
  return (
    <section
      className="overview-section"
      aria-labelledby={`overview-section-${number}`}
    >
      <h3 id={`overview-section-${number}`}>
        <span>{number}</span>
        {title}
      </h3>
      {children}
    </section>
  );
}
function KeyInformation({ figures, rows, children }) {
  return (
    <article className="overview-card overview-key">
      <h4>Key information</h4>
      <div className="overview-key-figures">
        {figures.map((f, i) => (
          <div
            key={f.label}
            style={{
              "--figure-color": i
                ? "var(--color-caution)"
                : "var(--color-info)",
            }}
          >
            <strong>{fallback(f.value)}</strong>
            <span>
              {f.label}
              {f.term && <TermHelp term={f.term} />}
            </span>
          </div>
        ))}
      </div>
      {children}
      <dl className="overview-facts">
        {rows.map((row) => (
          <div key={row.label}>
            <dt>{row.label}</dt>
            <dd>
              {row.onClick && row.value != null ? (
                <button onClick={row.onClick} aria-haspopup="dialog">
                  {row.value}
                </button>
              ) : (
                fallback(row.value)
              )}
            </dd>
          </div>
        ))}
      </dl>
    </article>
  );
}
function Bars({ title, rows, onEvidence }) {
  const values = rows.map((r) => number(r.value)).filter((v) => v != null),
    low = Math.min(0, ...values),
    high = Math.max(0, ...values),
    span = high - low || 1;
  return (
    <div className="overview-bars">
      <h4>{title}</h4>
      {rows.map((row, i) => (
        <button
          className="overview-bar-row"
          key={row.label}
          onClick={() => onEvidence(row)}
          aria-haspopup="dialog"
        >
          <span className="overview-bar-label">{row.label}</span>
          <span className="overview-bar-track" aria-hidden="true">
            <i style={{ left: `${(-low / span) * 100}%` }} />
            {number(row.value) != null && (
              <span
                style={{
                  left: `${((Math.min(0, number(row.value)) - low) / span) * 100}%`,
                  width: `${(Math.abs(number(row.value)) / span) * 100}%`,
                  background:
                    row.color ||
                    (i ? "var(--color-caution)" : "var(--color-positive)"),
                }}
              />
            )}
          </span>
          <strong>{fallback(money(row.value))}</strong>
        </button>
      ))}
    </div>
  );
}
function RevenueMix({ groups, onEvidence, onBrief }) {
  const labels = [
    ...new Set(
      groups.flatMap((g) =>
        [...g.members]
          .sort((a, b) => number(b.value) - number(a.value))
          .map((m) => m.label),
      ),
    ),
  ];
  const colors = [
    "var(--color-info)",
    "var(--color-caution)",
    "var(--color-positive)",
    "#c993c9",
    "#8fbcc7",
    "#aea0db",
  ];
  return (
    <article className="overview-card overview-mix">
      <h4>Revenue by business</h4>
      {groups.length ? (
        groups.map((group) => (
          <div className="overview-mix-period" key={group.period}>
            <div>
              <strong>
                {group.period === "Quarter"
                  ? "Latest reported quarter"
                  : `Fiscal year ended ${day(group.end)}`}
              </strong>
              <span>{money(group.total)}</span>
            </div>
            {group.chartable ? (
              <button
                className="overview-mix-track"
                onClick={() => onEvidence(group)}
                aria-label={`${group.period} revenue split: ${group.members.map((m) => `${m.label} ${percent(m.percentage)}`).join(", ")}. View evidence`}
                aria-haspopup="dialog"
              >
                {[...group.members]
                  .sort(
                    (a, b) => labels.indexOf(a.label) - labels.indexOf(b.label),
                  )
                  .map((m) => (
                    <span
                      key={m.label}
                      style={{
                        width: `${number(m.percentage)}%`,
                        background:
                          colors[labels.indexOf(m.label) % colors.length],
                      }}
                    />
                  ))}
              </button>
            ) : (
              <p className="overview-caption">
                {group.reason ||
                  "These categories cannot be combined into a percentage chart."}
              </p>
            )}
            <ul className="overview-mix-legend">
              {group.members.map((m) => (
                <li key={m.label}>
                  <i
                    style={{
                      background:
                        colors[labels.indexOf(m.label) % colors.length],
                    }}
                  />
                  <span>{m.label}</span>
                  <strong>{money(m.value)}</strong>
                </li>
              ))}
            </ul>
            {group.period === "Quarter" && (
              <p className="overview-caption">
                {day(group.start)} – {day(group.end)}
              </p>
            )}
          </div>
        ))
      ) : (
        <p className="overview-empty">
          A business revenue split is not available in the saved reports.
        </p>
      )}
      <div className="overview-actions">
        <button onClick={() => onEvidence(groups[0])} disabled={!groups.length}>
          View evidence
        </button>
        <button onClick={onBrief}>Read the AI business brief →</button>
      </div>
    </article>
  );
}
function Tone({ tone }) {
  if (!tone?.total || !tone.reconciled)
    return (
      <p className="overview-caption">
        {tone?.total && !tone.reconciled
          ? "The saved tone totals do not agree, so a breakdown is not shown."
          : "There are no counted news developments to show in a tone breakdown."}
      </p>
    );
  const parts = [
    ["positive", tone.counts.positive || 0, "positive"],
    [
      "neutral",
      (tone.counts.neutral || 0) + (tone.counts.mixed || 0),
      "neutral / mixed",
    ],
    ["negative", tone.counts.negative || 0, "negative"],
    ["unclear", tone.counts.unclear || 0, "unclear"],
  ];
  return (
    <div className="overview-tone">
      <div
        className="overview-tone-track"
        role="img"
        aria-label={parts.map((p) => `${p[1]} ${p[2]}`).join(", ")}
      >
        {parts
          .filter((p) => p[1])
          .map((p) => (
            <span key={p[0]} className={p[0]} style={{ flexGrow: p[1] }} />
          ))}
      </div>
      <p>
        {parts
          .filter((p) => p[1])
          .map((p) => (
            <span key={p[0]}>
              <b>{p[1]}</b> {p[2]}
            </span>
          ))}
      </p>
      <small>
        {tone.selected} stories →{" "}
        {tone.relevant != null ? `${tone.relevant} relevant → ` : ""}
        {tone.total}{" "}
        {tone.grouped ? "distinct developments" : "counted text groups"}. News
        only; social samples stay separate.
      </small>
    </div>
  );
}

export default function OverviewSections({
  data,
  instrumentId,
  visible,
  onView,
  onSource,
  businessPanel,
  focusTopic,
}) {
  const [readState, setReadState] = useState({}),
    [retry, setRetry] = useState(0),
    [evidence, setEvidence] = useState(null),
    [filter, setFilter] = useState("all"),
    [briefOpen, setBriefOpen] = useState(false);
  const briefRef = useRef(null);
  // A new company or evidence version must never inherit another read's data
  // or its empty/error state, even on the render before the effect starts.
  const scope = JSON.stringify([
    instrumentId,
    data.snapshot_id,
    data.disclosures?.source_status?.last_success_at,
    retry,
  ]);
  const reads = readState.scope === scope ? readState.values : {};
  const errors = readState.scope === scope ? readState.errors : {};
  const loading = (key) =>
    readState.scope !== scope || readState.loading[key] !== false;
  const retryReads = () => setRetry((value) => value + 1);
  useEffect(() => {
    if (!visible) return;
    let active = true;
    setReadState({ scope, values: {}, errors: {}, loading: {} });
    // These endpoints only read saved data. No source refresh, AI generation or peer save.
    for (const [key, read] of [
      ["valuation", api.valuationContext],
      ["fmp", api.fmp],
      ["business", api.businessHistory],
      ["sector", (id) => api.sectorPosition(id)],
    ]) {
      read(instrumentId)
        .then((result) => {
          if (active) {
            setReadState((old) =>
              old.scope === scope
                ? {
                    ...old,
                    values: { ...old.values, [key]: result },
                    loading: { ...old.loading, [key]: false },
                  }
                : old,
            );
          }
        })
        .catch(() => {
          if (active) {
            setReadState((old) =>
              old.scope === scope
                ? {
                    ...old,
                    errors: { ...old.errors, [key]: true },
                    loading: { ...old.loading, [key]: false },
                  }
                : old,
            );
          }
        });
    }
    return () => {
      active = false;
    };
  }, [instrumentId, visible, scope]);
  useEffect(() => {
    setEvidence(null);
  }, [
    data.performance,
    data.financial_depth,
    data.segment_revenue,
    data.sentiment,
  ]);
  useEffect(() => {
    if (focusTopic) setBriefOpen(true);
  }, [focusTopic]);
  const m = overviewModel(data, reads),
    name = companyName(data.instrument),
    mix = m.mix[0],
    guidance = m.guidance;
  const show = (title, rows, body = null) =>
    setEvidence({ title, rows: rows.filter(Boolean), body });
  const figure =
    (row, label = row?.label) =>
    () =>
      show(`${label || "Figure"} · evidence`, [row]);
  const mixEvidence = (group) =>
    group && show("Revenue by business · evidence", segmentEvidence(group));
  const openBrief = () => {
    setBriefOpen(true);
    requestAnimationFrame(() => {
      briefRef.current?.querySelector("summary")?.focus();
      briefRef.current?.scrollIntoView({ block: "start", behavior: "instant" });
    });
  };
  const annualPrior = m.revenue?.prior
    ? {
        ...m.revenue.prior,
        label: "Revenue",
        key: "revenue",
        inputs: [
          {
            ...m.revenue.prior,
            filing_url: m.revenue.source_report?.filing_url,
          },
        ],
      }
    : null;
  const growthNumber = number(m.growth?.value);
  const growthVsPeers = growthTakeaway(reads.sector);
  const peVsPeers = peTakeaway(reads.sector, reads.valuation?.references);
  const borrowedRatio = m.cashRatio > 0 ? 1 / m.cashRatio : null;
  const sources = m.headlines
    .filter((s) => filter === "all" || s.kind === filter)
    .slice(0, 4);
  const forecastStatus = loading("fmp")
    ? "Loading saved forecasts…"
    : errors.fmp
      ? "Saved forecasts could not be loaded."
      : m.forecasts
        ? "Saved · see Outlook for dates and sources"
        : "No usable saved forecasts";
  const briefText = m.brief?.result?.findings?.find(
    (f) => f.category === "business",
  )?.text;
  const guidanceBody = guidance && (
    <>
      <blockquote>{guidance.quote}</blockquote>
      <p>
        {guidance.unit || "Currency unspecified"} ·{" "}
        {guidance.basis?.toUpperCase() || "Accounting basis unspecified"}.
        Forecast for {guidancePeriod(guidance.section)}.
        {!guidance.section.period_end && " Exact ending date not stated."}
      </p>
      <a href={guidance.release.url} target="_blank" rel="noreferrer">
        Read original earnings release ↗
      </a>
    </>
  );
  return (
    <div className="overview-sections">
      <Section number="1" title={`How ${name} makes money`}>
        <Reading
          limit={
            briefText && m.olderBrief
              ? "This AI explanation uses earlier saved documents and may not reflect newer reports."
              : null
          }
        >
          {briefText ||
            (mix
              ? `${name} reports ${mix.members.length} business categories: ${mix.members.map((g) => g.label).join(", ")}.`
              : "Read the company’s revenue, operating results and original business description together.")}
          {m.margin?.value != null &&
            ` Operating profit was ${percent(m.margin.value)} of revenue over the past 12 months.`}
        </Reading>
        {errors.business && (
          <p className="overview-caption" role="status">
            The saved business explanation could not be loaded.{" "}
            <button className="text-button" onClick={retryReads}>
              Retry saved data
            </button>
          </p>
        )}
        <div className="overview-section-grid">
          <KeyInformation
            figures={
              mix?.chartable
                ? [...mix.members]
                    .sort((a, b) => number(b.value) - number(a.value))
                    .slice(0, 2)
                    .map((row) => ({
                      value: percent(row.percentage, 0),
                      label: `${row.label}, ${mix.period === "Quarter" ? "latest quarter" : "fiscal year"}`,
                    }))
                : [
                    {
                      value: money(m.trailingRevenue?.value),
                      label: "Revenue, past 12 months",
                      term: "revenue",
                    },
                  ]
            }
            rows={[
              {
                label: "Revenue, latest quarter",
                value: money(m.quarterRevenue?.value),
                onClick: figure(m.quarterRevenue),
              },
              {
                label: yearLabel(m.revenue),
                value: money(m.revenue?.value),
                onClick: figure(m.revenue),
              },
              {
                label: "Revenue, past 12 months",
                value: money(m.trailingRevenue?.value),
                onClick: figure(m.trailingRevenue),
              },
              {
                label: "Operating margin, past 12 months",
                value: percent(m.margin?.value),
                onClick: figure(m.margin),
              },
              {
                label: "Latest report ends",
                value: m.latest
                  ? `${m.latest.form} · ${day(m.latest.period_end)}`
                  : null,
              },
            ]}
          />
          <RevenueMix
            groups={m.mix}
            onEvidence={mixEvidence}
            onBrief={openBrief}
          />
        </div>
        <p className="overview-flow-link">
          <button
            className="text-button"
            onClick={() => onView("fundamentals")}
          >
            See how revenue becomes profit in Financials →
          </button>
        </p>
        <details
          className="overview-brief"
          ref={briefRef}
          open={briefOpen}
          onToggle={(e) => setBriefOpen(e.currentTarget.open)}
        >
          <summary>
            AI business brief{" "}
            <span>Company statements, sources and research questions</span>
          </summary>
          {businessPanel}
        </details>
      </Section>
      <Section number="2" title="Growth & outlook">
        <Reading>
          {growthNumber != null
            ? `Revenue ${growthNumber >= 0 ? "grew" : "fell"} ${Math.abs(growthNumber).toFixed(1)}% to ${money(m.revenue?.value)} in the fiscal year ended ${day(m.revenue?.end)}. `
            : "Comparable annual revenue growth is not available. "}
          {growthVsPeers && `${growthVsPeers} `}
          {guidance
            ? `The latest saved release gives revenue guidance of ${guidanceAmount(guidance)} for ${guidancePeriod(guidance.section)}.`
            : guidanceReason(data.management_outlook)}
          {guidance &&
            !guidance.section.period_end &&
            ` ${guidanceReason(data.management_outlook)}`}
          {guidance &&
            !guidance.unit &&
            " Currency is not specified by the source."}
          {guidance &&
            !guidance.basis &&
            " Accounting basis is not specified by the source."}
        </Reading>
        {errors.sector && (
          <p className="overview-caption" role="status">
            The saved peer comparison could not be loaded.{" "}
            <button className="text-button" onClick={retryReads}>
              Retry saved data
            </button>
          </p>
        )}
        <div className="overview-section-grid">
          <KeyInformation
            figures={[
              {
                value: percent(m.growth?.value),
                label: "Revenue growth, fiscal year",
                term: "revenue_growth",
              },
              {
                value:
                  guidanceAmount(guidance) ||
                  guidanceStatusLabel(data.management_outlook),
                label: "Management revenue outlook",
                term: "guidance",
              },
            ]}
            rows={[
              {
                label: yearLabel(annualPrior),
                value: money(annualPrior?.value),
                onClick: figure(annualPrior),
              },
              {
                label: yearLabel(m.revenue),
                value: money(m.revenue?.value),
                onClick: figure(m.revenue),
              },
              {
                label: "Outlook period ends",
                value: guidance
                  ? guidance.section.period_end
                    ? day(guidance.section.period_end)
                    : `${guidance.section.period_label} · exact date not stated`
                  : "See explanation above",
              },
              {
                label: "Analyst forecasts",
                value: (
                  <span role="status">
                    {forecastStatus}
                    {errors.fmp && (
                      <>
                        {" "}
                        <button onClick={retryReads}>Retry saved data</button>
                      </>
                    )}
                  </span>
                ),
              },
            ]}
          />
          <article className="overview-card">
            <Bars
              title="Yearly revenue"
              rows={[
                {
                  label: annualPrior?.end
                    ? `Year to ${day(annualPrior.end)}`
                    : "Previous fiscal year",
                  value: annualPrior?.value,
                  row: annualPrior,
                  color: "#6076a6",
                },
                {
                  label: m.revenue?.end
                    ? `Year to ${day(m.revenue.end)}`
                    : "Latest fiscal year",
                  value: m.revenue?.value,
                  row: m.revenue,
                  color: "var(--color-info)",
                },
              ]}
              onEvidence={(r) => figure(r.row)()}
            />
            {guidance && (
              <p className="overview-caption">
                Outlook from{" "}
                {guidance.release.stated_release_date
                  ? `the ${day(guidance.release.stated_release_date.date)} release`
                  : `a filing accepted ${stamp(guidance.release.published_at)}`}
                . {!guidance.unit && "Currency unspecified. "}
                {!guidance.basis && "Accounting basis unspecified. "}Management
                guidance is separate from analyst forecasts.
              </p>
            )}
            <div className="overview-actions">
              <button
                onClick={() =>
                  show(
                    "Annual growth & outlook · evidence",
                    [m.growth, m.revenue, annualPrior],
                    guidanceBody,
                  )
                }
              >
                View evidence
              </button>
              <button onClick={() => onView("expectations")}>
                Open Outlook →
              </button>
            </div>
          </article>
        </div>
      </Section>
      <Section number="3" title="Financial health">
        <Reading>
          {m.assetsRatio != null
            ? `Reported assets are ${multiple(m.assetsRatio)} liabilities. `
            : "A matching assets-to-liabilities comparison is unavailable. "}
          {borrowedRatio != null
            ? `Borrowing of ${money(m.borrowing.value)} is ${multiple(borrowedRatio)} cash of ${money(m.cash.value)}.`
            : number(m.cash?.value) != null &&
                number(m.borrowing?.value) != null
              ? `It has ${money(m.cash.value)} cash against ${money(m.borrowing.value)} borrowing.`
              : "Matching cash and borrowing figures are unavailable."}{" "}
          These balances describe the company’s position at one reporting date.{" "}
          These balances alone do not establish whether future repayments are
          affordable.
        </Reading>
        <div className="overview-section-grid">
          <KeyInformation
            figures={[
              { value: multiple(m.assetsRatio), label: "Assets ÷ liabilities" },
              { value: multiple(m.cashRatio), label: "Cash ÷ borrowing" },
            ]}
            rows={[
              ...[
                ["Assets", m.assets],
                ["Liabilities", m.liabilities],
                ["Cash", m.cash],
                ["Borrowing", m.borrowing],
                ["Free cash flow, past 12 months", m.freeCash],
              ].map(([label, row]) => ({
                label,
                value: money(row?.value),
                onClick: figure(row, label),
              })),
              {
                label: "Balance date",
                value: m.latest ? day(m.latest.period_end) : null,
              },
            ]}
          />
          <article className="overview-card">
            <Bars
              title="Owns vs owes"
              rows={[
                { label: "Assets", value: m.assets?.value, row: m.assets },
                {
                  label: "Liabilities",
                  value: m.liabilities?.value,
                  row: m.liabilities,
                },
              ]}
              onEvidence={(r) => figure(r.row)()}
            />
            <Bars
              title="Cash vs borrowing"
              rows={[
                { label: "Cash", value: m.cash?.value, row: m.cash },
                {
                  label: "Borrowing",
                  value: m.borrowing?.value,
                  row: m.borrowing,
                },
              ]}
              onEvidence={(r) => figure(r.row)()}
            />
            <p className="overview-caption">
              Each pair uses its own shared scale. Cash is part of assets;
              borrowing is part of liabilities.
            </p>
            <div className="overview-actions">
              <button
                onClick={() =>
                  show("Financial position · evidence", [
                    m.assets,
                    m.liabilities,
                    m.cash,
                    m.borrowing,
                    m.freeCash,
                  ])
                }
              >
                View evidence
              </button>
              <button onClick={() => onView("fundamentals")}>
                Open Financials →
              </button>
            </div>
          </article>
        </div>
      </Section>
      <Section number="4" title="News & discussion">
        <Reading
          limit={
            data.sentiment?.withheld
              ? "The saved tone reading is hidden because source access changed. Permitted current sources remain readable."
              : m.tone
                ? [
                    m.tone.stale
                      ? "This reading uses a source sample captured over 24 hours ago; newer headlines may not be included."
                      : null,
                    data.sentiment?.earlier_method
                      ? "It was saved with an earlier analysis method."
                      : null,
                    "News tone describes this sample, not investor consensus or future returns.",
                  ]
                    .filter(Boolean)
                    .join(" ")
                : null
          }
        >
          {m.tone?.label
            ? `The saved company-news reading is ${m.tone.label.toLowerCase()}. `
            : m.tone
              ? "Too few news developments have a clear tone to describe the overall mood. "
              : "There is no usable saved company-news tone yet. "}
          Read the headlines and original posts below. Each social platform has
          its own sample and tone.
        </Reading>
        <div className="overview-section-grid">
          <KeyInformation
            figures={[
              {
                value:
                  m.tone?.label ||
                  (m.tone ? "Too little clear evidence" : null),
                label: "Company-news tone",
              },
              {
                value: m.tone ? String(m.tone.selected) : null,
                label: "News stories analysed",
              },
            ]}
            rows={[
              {
                label: "News cutoff",
                value: data.sentiment?.withheld
                  ? null
                  : data.sentiment?.cutoff
                    ? stamp(data.sentiment.cutoff)
                    : null,
              },
              {
                label: m.tone?.stale ? "Older reading saved" : "Reading saved",
                value: m.tone?.savedAt ? stamp(m.tone.savedAt) : null,
              },
              {
                label: "News watch",
                value: data.news_watch?.enabled
                  ? data.news_watch.error
                    ? "On · last update could not finish; saved research retained"
                    : `On · next ${stamp(data.news_watch.next_check_at)}`
                  : "Off",
              },
            ]}
          >
            <Tone tone={m.tone} />
          </KeyInformation>
          <article className="overview-card overview-headlines">
            <div className="overview-headlines-heading">
              <h4>Latest headlines & posts</h4>
              <div
                className="overview-news-filters"
                role="group"
                aria-label="Overview source filter"
              >
                {[
                  ["all", "All"],
                  ["news", "News"],
                  ["social", "Social"],
                ].map(([key, label]) => (
                  <button
                    key={key}
                    aria-pressed={filter === key}
                    onClick={() => setFilter(key)}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
            <ul>
              {sources.map((source) => (
                <li key={source.id}>
                  <button
                    className="overview-headline"
                    onClick={() => onSource(source)}
                  >
                    <strong>
                      {source.headline}
                      {!source.title && source.body?.length > 160 ? "…" : ""}
                    </strong>
                    <span>
                      <SourceIcon
                        scope={
                          source.kind === "news" ? "news" : source.platform
                        }
                      />
                      <span>
                        {source.tone
                          ? `${source.tone.charAt(0).toUpperCase()}${source.tone.slice(1)}`
                          : source.analysisLabel}{" "}
                        · {source.source || source.platform} ·{" "}
                        {stamp(source.published_at)}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            {!sources.length && (
              <p className="overview-empty">
                No permitted {filter === "all" ? "news or discussion" : filter}{" "}
                sources are saved in this sample.
              </p>
            )}
            <div className="overview-actions">
              <button onClick={() => onView("evidence")}>
                See all stories →
              </button>
              <button onClick={() => onView("evidence")}>
                Tone & source details
              </button>
            </div>
          </article>
        </div>
      </Section>
      <Section number="5" title="Value">
        <Reading>
          {m.pe != null
            ? `The saved trailing P/E is ${multiple(m.pe)}: about $${m.pe.toFixed(0)} of share price for every $1 of annual earnings. `
            : loading("valuation")
              ? "Loading saved valuation ratios… "
              : errors.valuation
                ? "Saved valuation ratios could not be loaded. "
                : "A usable saved price-to-earnings multiple is not available. "}
          {peVsPeers
            ? `${peVsPeers} ${peVsPeers.includes(" below ") ? "A lower multiple can mean the market expects slower growth or more risk, not only a bargain." : "A higher multiple can mean the market expects faster growth, which then has to arrive."}`
            : "Whether that is expensive depends on the company’s growth, risks and the peers or assumptions you compare it with."}
        </Reading>
        <div className="overview-section-grid">
          <KeyInformation
            figures={[
              {
                value: loading("valuation")
                  ? "Loading…"
                  : errors.valuation
                    ? "Could not load"
                    : multiple(m.pe),
                label: "Price to earnings",
                term: "pe",
              },
              {
                value: loading("valuation")
                  ? "Loading…"
                  : errors.valuation
                    ? "Could not load"
                    : multiple(m.ps),
                label: "Price to sales",
              },
            ]}
            rows={[
              {
                label: "Share price",
                value:
                  data.market?.quote?.quote?.price != null
                    ? `US$${Number(data.market.quote.quote.price).toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                    : null,
              },
              {
                label: "Ratios from",
                value: loading("valuation")
                  ? "Loading…"
                  : m.reference
                    ? "Finnhub · past 12 months"
                    : null,
              },
              {
                label: "Ratios saved",
                value: loading("valuation")
                  ? "Loading…"
                  : m.reference
                    ? stamp(m.reference.retrieved_at)
                    : null,
              },
              {
                label: "Saved peers",
                value: loading("fmp")
                  ? "Loading saved peers…"
                  : errors.fmp
                    ? "Could not load saved peers"
                    : m.peers.length
                      ? m.peers.map((p) => p.symbol).join(", ")
                      : "None yet",
              },
            ]}
          />
          <article className="overview-card overview-value-prompt">
            <h4>
              {m.pe != null
                ? `Is ${multiple(m.pe)} expensive?`
                : "What would make this price make sense?"}
            </h4>
            <p>
              {peVsPeers && growthVsPeers
                ? `${peTakeaway(reads.sector, reads.valuation?.references, "Its P/E is")} ${growthTakeaway(reads.sector, "Its revenue growth is")} Compare the two side by side, or test your own assumptions.`
                : "Compare growth and valuation across your chosen companies, or see what your own revenue, margin and valuation assumptions imply."}
            </p>
            <div className="overview-actions">
              <button className="primary" onClick={() => onView("valuation")}>
                {m.peers.length ? "Compare peers" : "Choose peers"}
              </button>
              <button onClick={() => onView("valuation", "scenario")}>
                Try a scenario
              </button>
            </div>
            <p className="overview-caption">
              Saved trailing ratios use the provider’s definitions. They are not
              forward estimates or an investment rating.
            </p>
            {errors.valuation && (
              <p className="overview-caption" role="status">
                Saved ratios could not be loaded.{" "}
                <button className="text-button" onClick={retryReads}>
                  Retry saved data
                </button>
              </p>
            )}
          </article>
        </div>
      </Section>
      <Modal
        open={!!evidence}
        onClose={() => setEvidence(null)}
        title={evidence?.title || "Evidence"}
        className="evidence-dialog"
      >
        <FinancialEvidence rows={evidence?.rows || []}>
          {evidence?.body}
        </FinancialEvidence>
      </Modal>
    </div>
  );
}
