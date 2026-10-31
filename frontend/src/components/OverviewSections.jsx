import { useEffect, useState } from "react";
import { api } from "../api/client";
import { companyName } from "../lib/companyIdentity";
import { day, money } from "../lib/companySnapshot";
import {
  overviewModel,
  guidanceAmount,
  guidancePeriod,
  multiple,
  revenueComparisons,
  signedPercent,
  number,
} from "../lib/overviewSections";
import { evidenceDialogRows } from "../lib/financialEvidence";
import { peTakeaway } from "../lib/overviewTakeaways";
import "./OverviewSections.css";
import OverviewReadCard from "./OverviewReadCard";
import { Disclosure, EvidenceDialog, FilterGroup, SectionHeader } from "./ui";

export default function OverviewSections({
  data,
  instrumentId,
  visible,
  onView,
  businessPanel,
  briefOpen,
  onBriefToggle,
}) {
  const [topic, setTopic] = useState("money");
  const [readState, setReadState] = useState({}),
    [evidence, setEvidence] = useState(null);
  // A new company or evidence version must never inherit another read's data
  // or its empty/error state, even on the render before the effect starts.
  const scope = JSON.stringify([
    instrumentId,
    data.snapshot_id,
    data.disclosures?.source_status?.last_success_at,
  ]);
  const reads = readState.scope === scope ? readState.values : {};
  useEffect(() => {
    if (!visible) return;
    let active = true;
    setReadState({ scope, values: {}, errors: {}, loading: {} });
    // These endpoints only read saved data. No source refresh, AI generation or peer save.
    for (const [key, read] of [
      ["valuation", api.valuationContext],
      ["business", api.businessHistory],
      ["sector", (id) => api.sectorPosition(id)],
    ]) {
      read(instrumentId)
        .then((result) => {
          if (active) {
            setReadState((old) =>
              old.scope === scope
                ? { ...old, values: { ...old.values, [key]: result } }
                : old,
            );
          }
        })
        .catch(() => {
          if (active) {
            setReadState((old) =>
              old.scope === scope
                ? { ...old, errors: { ...old.errors, [key]: true } }
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
  const m = overviewModel(data, reads),
    name = companyName(data.instrument),
    mix = m.mix[0],
    guidance = m.guidance;
  const show = (title, rows, extra = []) =>
    setEvidence({
      title,
      rows: [...evidenceDialogRows(rows), ...extra.filter(Boolean)],
    });
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
  const peVsPeers = peTakeaway(reads.sector, reads.valuation?.references);
  const briefText = m.brief?.result?.findings?.find(
    (f) => f.category === "business",
  )?.text;
  const guidanceRow = guidance && {
    id: "guidance",
    label: "Management guidance",
    meta: `${guidance.unit || "Currency unspecified"} · ${guidance.basis?.toUpperCase() || "Accounting basis unspecified"} · forecast for ${guidancePeriod(guidance.section)}${guidance.section.period_end ? "" : " · exact ending date not stated"}`,
    quote: guidance.quote,
    href: guidance.release.url,
    sourceLabel: "Original earnings release",
  };
  const { latestQuarter } = revenueComparisons(data, guidance);
  const topics = {
    money: {
      label: "Makes money",
      reading:
        briefText ||
        (mix
          ? `${name} reports ${mix.members.length} business categories: ${mix.members.map((g) => g.label).join(", ")}.`
          : "Read the company’s revenue, operating results and original business description together."),
      figures: [
        {
          label: "Revenue",
          value: money(m.revenue?.value),
          onOpen: () => show("Revenue", [m.revenue]),
        },
        { label: "Reporting period", value: day(m.revenue?.end) },
      ],
      to: ["fundamentals", "Financials"],
    },
    growth: {
      label: "Growth",
      reading: latestQuarter
        ? `Latest-quarter revenue was ${money(latestQuarter.current.value)}, ${latestQuarter.growth >= 0 ? "up" : "down"} ${Math.abs(latestQuarter.growth).toFixed(1)}% from a year earlier.`
        : growthNumber != null
          ? `Annual revenue ${growthNumber >= 0 ? "grew" : "fell"} ${Math.abs(growthNumber).toFixed(1)}%.`
          : "Comparable revenue growth is unavailable.",
      figures: [
        {
          label: "Annual growth",
          value: signedPercent(growthNumber),
          onOpen: () =>
            show("Revenue growth", [m.growth, m.revenue, annualPrior]),
        },
        {
          label: "Management guidance",
          value: guidance ? guidanceAmount(guidance) : "Unavailable",
          onOpen: guidance
            ? () => show("Management guidance", [], [guidanceRow])
            : undefined,
        },
      ],
      to: [
        "fundamentals",
        "Financials · what management expects",
        "management",
      ],
    },
    health: {
      label: "Financial health",
      reading:
        m.assetsRatio != null
          ? `Reported assets are ${multiple(m.assetsRatio)} liabilities. Read cash flow and borrowing alongside this snapshot.`
          : "A matching assets-to-liabilities comparison is unavailable. Read the reported cash flow and borrowing.",
      figures: [
        {
          label: "Free cash flow",
          value: money(m.freeCash?.value),
          onOpen: () => show("Free cash flow", [m.freeCash]),
        },
        {
          label: "Assets ÷ liabilities",
          value: multiple(m.assetsRatio),
          onOpen: () =>
            show("Assets and liabilities", [m.assets, m.liabilities]),
        },
      ],
      to: ["fundamentals", "Financials"],
    },
    value: {
      label: "Value",
      reading:
        peVsPeers ||
        "Whether a valuation looks high or low depends on growth, risks and the assumptions you compare it with.",
      figures: [
        {
          label: "Price to earnings",
          value: multiple(m.pe),
          onOpen: m.reference
            ? () => show("Valuation ratios", [m.reference])
            : undefined,
        },
        { label: "Price to sales", value: multiple(m.ps) },
      ],
      to: ["valuation", "Compare & value"],
    },
  };
  const current = topics[topic];
  return (
    <div className="overview-sections overview-sections-compact">
      <SectionHeader level="section" as="h2" title="The business" />
      <FilterGroup
        label="Business topic"
        value={topic}
        onValueChange={setTopic}
        options={Object.entries(topics).map(([value, t]) => ({
          value,
          label: t.label,
        }))}
      />
      <OverviewReadCard
        reading={current.reading}
        figures={current.figures}
        onView={() => onView(current.to[0], current.to[2])}
        destination={current.to[1]}
      />
      <Disclosure
        title="Business brief and research questions"
        description="Saved brief, original evidence and what to research next"
        open={briefOpen}
        onToggle={(event) => {
          if (event.target === event.currentTarget)
            onBriefToggle(event.currentTarget.open);
        }}
      >
        {briefOpen &&
          (typeof businessPanel === "function"
            ? businessPanel()
            : businessPanel)}
      </Disclosure>
      <EvidenceDialog
        open={!!evidence}
        onClose={() => setEvidence(null)}
        title={evidence?.title || "Evidence"}
        rows={evidence?.rows || []}
      />
    </div>
  );
}
