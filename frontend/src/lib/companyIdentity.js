// Presentation aliases only. Canonical issuer names remain in saved records.
const names = {
  AMD: "Advanced Micro Devices",
  AVGO: "Broadcom",
  FN: "Fabrinet",
  MRVL: "Marvell Technology",
  MU: "Micron Technology",
  NVDA: "NVIDIA",
  QCOM: "Qualcomm",
  AAPL: "Apple",
  MSFT: "Microsoft",
  GOOG: "Alphabet",
  GOOGL: "Alphabet",
};
export function companyName(company) {
  return (
    (company?.mode !== "recorded" && names[company?.symbol]) ||
    company?.name ||
    company?.symbol ||
    "Company"
  );
}
export function companyMatches(company, query) {
  return `${company?.symbol || ""} ${companyName(company)} ${company?.name || ""}`
    .toLowerCase()
    .includes(query.trim().toLowerCase());
}
