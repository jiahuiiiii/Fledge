import { day } from "./financialStory.js";

export function evidenceValue(raw, unit = "USD") {
  if (raw == null || raw === "" || typeof raw === "boolean")
    return "Unavailable";
  const value = Number(raw);
  if (!Number.isFinite(value)) return "Unavailable";
  const abs = Math.abs(value);
  const scale =
    unit === "USD"
      ? abs >= 1e12
        ? 1e12
        : abs >= 1e9
          ? 1e9
          : abs >= 1e6
            ? 1e6
            : 1
      : 1;
  const amount = (abs / scale).toLocaleString(
    "en-GB",
    abs > 0 && abs / scale < 0.01
      ? { maximumSignificantDigits: 3 }
      : { maximumFractionDigits: 2 },
  );
  const signed = `${value < 0 ? "−" : ""}${unit === "USD" ? "US$" : ""}${amount}`;
  return (
    signed +
    (unit === "USD"
      ? { 1000000000000: " tril", 1000000000: " bil", 1000000: " mil" }[
          scale
        ] || ""
      : unit === "percent"
        ? "%"
        : ["multiple", "times"].includes(unit)
          ? "×"
          : ` ${unit}`)
  );
}

export const evidencePeriod = (row) =>
  row?.start && row?.end
    ? `${day(row.start)} – ${day(row.end)}`
    : row?.end
      ? `At ${day(row.end)}`
      : "Period unavailable";

const concepts = {
  RevenueFromContractWithCustomerExcludingAssessedTax: "Revenue",
  RevenueFromContractWithCustomerIncludingAssessedTax: "Revenue",
  Revenues: "Revenue",
  SalesRevenueNet: "Net sales",
  OperatingIncomeLoss: "Operating income",
  NetIncomeLoss: "Net income",
  ProfitLoss: "Net result",
  NetIncomeLossAvailableToCommonStockholdersBasic:
    "Income available to common shareholders",
  NetCashProvidedByUsedInOperatingActivities: "Operating cash flow",
  PaymentsToAcquirePropertyPlantAndEquipment: "Capital spending",
  CostOfRevenue: "Cost of revenue",
  CostOfGoodsAndServicesSold: "Cost of sales",
  GrossProfit: "Gross profit",
  OperatingExpenses: "Operating expenses",
  ResearchAndDevelopmentExpense: "Research & development",
  SellingGeneralAndAdministrativeExpense: "Selling & administration",
  IncomeTaxExpenseBenefit: "Income tax",
  InterestExpenseNonOperating: "Interest expense",
  Assets: "Assets",
  AssetsCurrent: "Current assets",
  Liabilities: "Liabilities",
  LiabilitiesCurrent: "Current liabilities",
  StockholdersEquity: "Shareholders’ equity",
  CashAndCashEquivalentsAtCarryingValue: "Cash & equivalents",
  DebtLongtermAndShorttermCombinedAmount: "Total borrowing",
  LongTermDebt: "Long-term debt",
  LongTermDebtCurrent: "Current portion of long-term debt",
  LongTermDebtNoncurrent: "Noncurrent debt",
  ShortTermBorrowings: "Short-term borrowing",
  CommercialPaper: "Commercial paper",
};
export function inputLabel(row, input, index) {
  if (
    row.inputs?.length === 3 &&
    row.formula?.startsWith("Previous fiscal year +")
  )
    return [
      "Previous fiscal year",
      "Current year to date",
      "Prior year to date",
    ][index];
  if (row.key === "revenue_growth" && row.inputs?.length === 2)
    return index === 0 ? "Current fiscal year" : "Previous fiscal year";
  return concepts[input.concept] || "Reported figure";
}
export function evidenceFormula(row) {
  if (row.key === "revenue_growth")
    return "(Revenue ÷ previous revenue − 1) × 100";
  if (row.key === "operating_margin") return "Operating income ÷ revenue × 100";
  return row.formula?.replace(/_/g, " ");
}
export function filingName(form) {
  const base = form?.replace("/A", "");
  const label =
    base === "10-K"
      ? "Annual report"
      : base === "10-Q"
        ? "Quarterly report"
        : "Source report";
  return form?.endsWith("/A") ? `${label} amendment` : label;
}
export function evidenceSources(row, fallbackUrl) {
  const sources = new Map();
  for (const input of [
    ...(row.inputs || []),
    ...(row.prior ? [row.prior] : []),
  ]) {
    const url = input.filing_url || fallbackUrl;
    if (url && !sources.has(url))
      sources.set(url, { url, label: filingName(input.form), date: input.end });
  }
  const url = row.source_report?.filing_url || fallbackUrl;
  if (url && !sources.has(url))
    sources.set(url, {
      url,
      label: filingName(row.source_report?.form),
      date: row.end,
    });
  return [...sources.values()];
}
