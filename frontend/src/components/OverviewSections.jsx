import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { companyName } from "../lib/companyIdentity";
import { day, money, percent } from "../lib/companySnapshot";
import {
  overviewModel,
  segmentEvidence,
  guidanceAmount,
  multiple,
  number,
  yearLabel,
} from "../lib/overviewSections";
import RevenueFlow from "./RevenueFlow";
import FinancialEvidence from "./FinancialEvidence";
import Modal from "./Modal";
import TermHelp from "./TermHelp";
import { SourceIcon } from "./SourceFilters";
import "./OverviewSections.css";

const fallback = (value) => value ?? "Not available";
const stamp = (value) =>
  value
    ? new Date(value).toLocaleString("en-GB", {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "Not checked";
const check = (label, result) => ({
  label,
  state: result == null ? "unknown" : result ? "pass" : "fail",
});
function Reading({ checks, children, label = "Checks" }) {
  return (
    <div className="overview-reading">
      <div className="overview-checks">
        <strong>
          {label} {checks.filter((c) => c.state === "pass").length}/
          {checks.length}
        </strong>
        {checks.map((c) => (
          <span key={c.label} className={`overview-check ${c.state}`}>
            <span aria-hidden="true">
              {c.state === "pass" ? "✓" : c.state === "fail" ? "×" : "–"}
            </span>{" "}
            {c.label}
          </span>
        ))}
      </div>
      <p>{children}</p>
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
        No reconciled news-tone breakdown is available.
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
  const [reads, setReads] = useState({}),
    [errors, setErrors] = useState({}),
    [evidence, setEvidence] = useState(null),
    [filter, setFilter] = useState("all"),
    [briefOpen, setBriefOpen] = useState(false);
  const briefRef = useRef(null);
  useEffect(() => {
    if (!visible) return;
    let active = true;
    // These endpoints only read saved data. No source refresh, AI generation or peer save.
    for (const [key, read] of [
      ["valuation", api.valuationContext],
      ["fmp", api.fmp],
      ["business", api.businessHistory],
    ]) {
      read(instrumentId)
        .then((result) => {
          if (active) {
            setReads((old) => ({ ...old, [key]: result }));
            setErrors((old) => ({ ...old, [key]: null }));
          }
        })
        .catch((error) => {
          if (active) {
            setReads((old) => ({ ...old, [key]: null }));
            setErrors((old) => ({ ...old, [key]: error.message }));
          }
        });
    }
    return () => {
      active = false;
    };
  }, [
    instrumentId,
    visible,
    data.snapshot_id,
    data.disclosures?.source_status?.last_success_at,
  ]);
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
  const borrowedRatio = m.cashRatio > 0 ? 1 / m.cashRatio : null;
  const sources = m.headlines
    .filter((s) => filter === "all" || s.kind === filter)
    .slice(0, 4);
  const sourceChecks = [
    ["news", "News"],
    ["reddit", "Reddit"],
    ["hackernews", "Hacker News"],
    ["x", "X"],
  ].map(([platform, label]) =>
    check(
      label +
        (platform === "x" &&
        data.provider_status?.some(
          (p) => p.provider === "x" && p.status === "disabled",
        )
          ? " off"
          : ""),
      m.headlines.some(
        (s) => (s.kind === "news" ? "news" : s.platform) === platform,
      )
        ? true
        : null,
    ),
  );
  const briefText = m.brief?.result?.findings?.find(
    (f) => f.category === "business",
  )?.text;
  const guidanceBody = guidance && (
    <>
      <blockquote>{guidance.quote}</blockquote>
      <p>
        {guidance.unit || "Currency unspecified"} ·{" "}
        {guidance.basis?.toUpperCase() || "Accounting basis unspecified"}.
        Target {guidance.section.period_type} ends{" "}
        {day(guidance.section.period_end)}.
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
          checks={[
            check(
              "Revenue split by business",
              m.mix.some((g) => g.chartable) ? true : null,
            ),
            check(
              "Quarterly report saved",
              data.performance?.reports?.quarter ? true : null,
            ),
            check(
              m.olderBrief
                ? "Brief uses earlier documents"
                : "Business brief saved",
              m.brief ? (m.olderBrief ? null : true) : null,
            ),
          ]}
        >
          {briefText ||
            (mix
              ? `${name} reports ${mix.members.length} business categories: ${mix.members.map((g) => g.label).join(", ")}.`
              : "Read the company’s revenue, operating results and original business description together.")}
          {m.margin?.value != null &&
            ` Operating profit was ${percent(m.margin.value)} of revenue over the past 12 months.`}
        </Reading>
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
        <RevenueFlow
          data={data.income_flow}
          segments={data.segment_revenue}
          compactOverview
          compactHeading
        />
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
        <Reading
          checks={[
            check(
              "Revenue grew last fiscal year",
              growthNumber == null ? null : growthNumber > 0,
            ),
            check("Management outlook available", guidance ? true : null),
            check(
              m.forecasts
                ? "Analyst forecasts saved"
                : "Analyst forecasts unavailable",
              m.forecasts ? true : null,
            ),
          ]}
        >
          {growthNumber != null
            ? `Revenue ${growthNumber >= 0 ? "grew" : "fell"} ${Math.abs(growthNumber).toFixed(1)}% to ${money(m.revenue?.value)} in the fiscal year ended ${day(m.revenue?.end)}. `
            : "Comparable annual revenue growth is not available. "}
          {guidance
            ? `Management’s revenue outlook is ${guidanceAmount(guidance)} for the ${guidance.section.period_type} ending ${day(guidance.section.period_end)}.`
            : "No current management revenue outlook is saved."}
        </Reading>
        <div className="overview-section-grid">
          <KeyInformation
            figures={[
              {
                value: percent(m.growth?.value),
                label: "Revenue growth, fiscal year",
                term: "revenue_growth",
              },
              {
                value: guidanceAmount(guidance),
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
                value: guidance ? day(guidance.section.period_end) : null,
              },
              {
                label: "Analyst forecasts",
                value: m.forecasts ? "Saved" : "Not available",
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
                  : `a filing accepted ${day(guidance.release.published_at)}`}
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
        <Reading
          checks={[
            check(
              "Owns more than it owes",
              number(m.assets?.value) != null &&
                number(m.liabilities?.value) != null
                ? number(m.assets.value) > number(m.liabilities.value)
                : null,
            ),
            check(
              "Cash covers borrowing",
              number(m.cash?.value) != null &&
                number(m.borrowing?.value) != null
                ? number(m.cash.value) >= number(m.borrowing.value)
                : null,
            ),
          ]}
        >
          {m.assetsRatio != null
            ? `Reported assets are ${multiple(m.assetsRatio)} liabilities. `
            : "A matching assets-to-liabilities comparison is unavailable. "}
          {borrowedRatio != null
            ? `Borrowing of ${money(m.borrowing.value)} is ${multiple(borrowedRatio)} cash of ${money(m.cash.value)}.`
            : number(m.cash?.value) != null &&
                number(m.borrowing?.value) != null
              ? `It has ${money(m.cash.value)} cash against ${money(m.borrowing.value)} borrowing.`
              : "Matching cash and borrowing figures are unavailable."}{" "}
          These balances describe the company’s position at one reporting date.
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
        <Reading checks={sourceChecks} label="Saved sources">
          {m.tone?.label
            ? `The saved company-news reading is ${m.tone.label.toLowerCase()}. `
            : "There is no usable saved company-news tone yet. "}
          Read the headlines and original posts below. Each social platform has
          its own sample and tone.
        </Reading>
        <div className="overview-section-grid">
          <KeyInformation
            figures={[
              { value: m.tone?.label, label: "Company-news tone" },
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
                    ? "On · check incomplete"
                    : `On · next ${stamp(data.news_watch.next_check_at)}`
                  : "Off",
              },
            ]}
          >
            <Tone tone={m.tone} />
            {data.sentiment?.earlier_method && (
              <p className="overview-caption">
                Saved with an earlier reading method.
              </p>
            )}
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
                    onClick={() => onSource(source.id)}
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
        <Reading
          label="Research steps"
          checks={[
            check(
              m.peers.length ? `${m.peers.length} peers saved` : "Choose peers",
              m.peers.length ? true : null,
            ),
            check(
              m.scenarios.length ? "Scenario saved" : "Try your own scenario",
              m.scenarios.length ? true : null,
            ),
          ]}
        >
          {m.pe != null
            ? `The saved trailing P/E is ${multiple(m.pe)}: about $${m.pe.toFixed(0)} of share price for every $1 of annual earnings. `
            : "A saved price-to-earnings multiple is not available. "}
          Whether that is expensive depends on the company’s growth, risks and
          the peers or assumptions you compare it with.
        </Reading>
        <div className="overview-section-grid">
          <KeyInformation
            figures={[
              { value: multiple(m.pe), label: "Price to earnings", term: "pe" },
              { value: multiple(m.ps), label: "Price to sales" },
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
                value: m.reference ? "Finnhub · past 12 months" : null,
              },
              {
                label: "Ratios saved",
                value: m.reference ? stamp(m.reference.retrieved_at) : null,
              },
              {
                label: "Saved peers",
                value: m.peers.length
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
              Compare growth and valuation across your chosen companies, or see
              what your own revenue, margin and valuation assumptions imply.
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
              <p className="overview-caption">
                Saved ratios could not be loaded. Open Compare &amp; value to
                retry.
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
