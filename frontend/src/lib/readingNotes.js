// Presentation copy for known application-authored notes, including saved versions.
// Never apply this to source quotations or generated findings. Unknown notes survive.
const notes = new Map([
  [
    "Trailing periods use the existing prior annual + current YTD − comparable prior YTD bridge. Original filing vintages and accounting-policy changes need review.",
    "Past 12 months = last full financial year + this year so far − the same part of last year. Subtracting that earlier period avoids counting it twice. Revised reports or changes in accounting can affect comparisons.",
  ],
  [
    "Previous fiscal year + current fiscal year to date − comparable prior fiscal year to date",
    "Last full financial year + this year so far − the same part of last year",
  ],
  [
    "All connected figures share explicit USD fiscal dates. Missing values are not zero; unreconciled or negative flows are withheld.",
    "Connected figures use US dollars and the same reporting period. Missing values stay unknown. Connections are hidden when amounts do not add up or are negative.",
  ],
  [
    "Trailing values cover the explicit fiscal dates shown; a 52/53-week fiscal year is not a calendar-year estimate.",
    "Past 12 months follows the company's reporting dates shown here. A financial year may have 52 or 53 weeks and need not run from January to December.",
  ],
  [
    "Annual/YTD bridges combine identified filing vintages. Restatement and accounting-policy consistency need the original notes; no price prediction is made.",
    "These calculations combine annual reports with this year's results so far. Check the original report notes for revisions or changes in accounting. These figures do not predict the share price.",
  ],
  [
    "Research calculations do not change saved monitoring definitions. Whole-company standard US-GAAP USD concepts only.",
    "These calculations use whole-company figures reported in US dollars under US accounting rules. They do not change your saved monitoring conditions.",
  ],
  [
    "Up to 36 whole passages selected across business, customers, revenue, competition, drivers, debt and risk terms; 28,000 serialized bytes. This is a bounded reading, not the whole filing.",
    "Based on selected sections about the business, customers, sales, competition, growth, debt and risks. It does not cover every part of the filings.",
  ],
  [
    "This claim adds a number or period absent from its own cited passages. It was withheld without rewriting or another AI call.",
    "Numbers or dates were not supported by the cited passages.",
  ],
  [
    "AI explanation of selected company disclosures. Matching source references do not establish interpretation accuracy. Financial calculations are shown separately.",
    "AI summaries can misread a source. Open the cited passages to check a finding. Financial calculations are shown separately.",
  ],
  [
    "This bounded reader recognizes selected prose outlook sections. Tables, complex ranges, segment forecasts and other wording may require the original release.",
    "Some forecasts may be missing, especially those in tables, for individual business lines, or with complex ranges. Check the original earnings release for the full outlook.",
  ],
  [
    "A dollar sign alone does not establish currency. An unlabeled revenue forecast does not establish GAAP accounting.",
    "A dollar sign does not tell us which country's dollars are meant. If a forecast does not name its accounting basis, we leave that unknown.",
  ],
  [
    "Comparisons use retained SEC filing results, not necessarily the earliest earnings announcement. No alert or research condition is created.",
    "Comparisons use saved SEC reports, which may have been published after the first earnings announcement. Viewing a comparison does not set up an alert.",
  ],
  [
    "Explicit company mentions, then expectation-related words and publication time. Up to twelve deduplicated snippets; important material may be omitted.",
    "Up to 12 news excerpts are selected by company mention, forecast wording and date. Duplicate excerpts are removed. Other useful reports may be missing.",
  ],
  [
    "AI reading of selected news headlines/snippets. Management statements are reported by these sources, not checked against original company guidance. Named analyst views are not consensus. Missing expectations may be outside this sample.",
    "This AI reading uses selected news excerpts. Statements attributed to management have not been checked against the company's own guidance. Individual analyst views do not represent all analysts. Other forecasts may be missing.",
  ],
  [
    "Vendor classification and values, first observed at retrieval. Provider quote time is not supplied; the description is not used as original-company evidence.",
    "Industry labels and values come from the data provider. Dates show when Fledge first saved them; the provider did not supply the quote time. This description is not a statement from the company.",
  ],
  [
    "Analyst consensus is distinct from management guidance and price targets. Forecast vintage is first observed at collection, not a historical pre-release forecast. Missing currency or earnings convention prevents a comparable actual-results verdict.",
    "These are analyst forecasts, separate from the company's guidance and share-price targets. The saved date does not establish when analysts made a forecast. Without its currency and accounting basis, we cannot say whether reported results beat or missed it.",
  ],
  [
    "An additional AI evidence check can withhold proposed themes. It can still miss errors; inspect the original sources.",
    "An AI check removes topics it cannot support with the sources. It can still miss mistakes; use the source links to check the summary.",
  ],
]);
const themeLimitation =
  "AI interpretation of selected, previously classified source text. News, Reddit, Hacker News and X are separate samples, not market consensus or independent verification. Only explicitly supplied saved parents provide conversation context; full threads and linked articles are not model inputs.";
const themeBatching =
  "Sources were read in complete batches. Topics and differing views were compared within each batch, not ranked or merged across the whole sample; similar topics may appear more than once.";
const themeReading =
  "This AI summary uses selected news and social posts. It is not a survey of investors or independent confirmation. Replies have context only when a saved parent message was included; full threads and linked articles were not read.";
const groupedReading =
  "Sources were read in smaller sets. Topics and differing views were compared within each set, so topics may repeat and some opposing views may be missed. Topics are not ranked across all sources.";
notes.set(themeLimitation, themeReading);
notes.set(themeBatching, groupedReading);
notes.set(
  `${themeLimitation} ${themeBatching}`,
  `${themeReading} ${groupedReading}`,
);

export function readableNote(note) {
  return notes.get(note) ?? note;
}

// Drop only the app's known batch prefix; preserve the original finding itself.
export function readingGap(gap, batching) {
  const match =
    typeof gap === "string" && /^Batch ([1-9]\d*): (.+)$/s.exec(gap);
  return match && Number(match[1]) <= (batching?.completed || 0)
    ? match[2]
    : gap;
}

export function sourceTiming(source, format) {
  const parts = [];
  if (source?.first_observed_at)
    parts.push(`First saved ${format(source.first_observed_at)}`);
  if (source?.checked_at)
    parts.push(`Last checked ${format(source.checked_at)}`);
  return parts.join(" · ") || "Source dates unavailable.";
}
