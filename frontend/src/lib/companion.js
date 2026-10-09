export const companionPromise =
  "Fledge helps you explore an investment idea, keep your reasoning, and review changes in the evidence you follow.";

// Reading shortcuts, not saved questions or requests for generated answers.
export const starterQuestions = [
  {
    id: "business",
    question: "How does this company make money?",
    section: "business",
    topic: "revenue_model",
    destination: "Overview · How it makes money",
    prompt:
      "Read the business explanation and open a source. Can you describe what customers pay for in your own words?",
  },
  {
    id: "growth",
    question: "Is it growing?",
    section: "fundamentals",
    destination: "Financials · Revenue, profit and cash",
    prompt:
      "Compare sales across the labelled periods, then look at profit and cash. A growing business can still have costs or risks to investigate.",
  },
  {
    id: "risks",
    question: "What could go wrong?",
    section: "business",
    topic: "risks",
    destination: "Overview · Key risks",
    prompt:
      "Read the company’s disclosed risks and their sources. Which could challenge your reason for being interested? This is not a complete risk list.",
  },
  {
    id: "outlook",
    question: "What do analysts and management expect?",
    section: "expectations",
    destination: "Outlook · Guidance and forecasts",
    prompt:
      "Compare management’s own guidance with analyst forecasts. Check the dates, periods and accounting basis; expectations are not reported results.",
  },
];

export const financialTerms = {
  revenue: [
    "Revenue",
    "Sales earned before the company subtracts its expenses.",
    "Check the reporting period; sales alone do not show profit or cash collected.",
  ],
  revenue_growth: [
    "Revenue growth",
    "The percentage change in sales from the stated earlier period to the later one.",
    "Compare the same kind of period and read both dates; fiscal-year and trailing results can differ.",
  ],
  operating_margin: [
    "Operating margin",
    "Operating profit as a percentage of revenue, before non-operating items such as interest and tax.",
    "Compare the same accounting basis and period; a higher margin is not a verdict on the investment.",
  ],
  free_cash_flow: [
    "Free cash flow",
    "Here, cash from operations minus cash capital spending for the same period.",
    "It excludes other uses of cash such as acquisitions, debt repayments and dividends; it is not the cash balance.",
  ],
  pe: [
    "P/E",
    "The share price divided by earnings per share for the stated earnings period.",
    "TTM means the trailing 12 months. Check the provider’s earnings definition; losses or very small earnings can make this ratio unhelpful.",
  ],
  accounting: [
    "GAAP and adjusted figures",
    "GAAP follows standard accounting rules; adjusted or non-GAAP figures remove items chosen by the company or provider.",
    "Read the stated exclusions and compare like with like. An adjusted forecast is not directly equivalent to reported GAAP results.",
  ],
  consensus: [
    "Analyst consensus",
    "A summary of forecasts from the analysts included by a provider, often an average.",
    "It is not a guarantee or necessarily agreement. Check the range, contributor count, forecast date and period.",
  ],
  guidance: [
    "Company guidance",
    "Management’s stated expectations for a future reporting period.",
    "Check the original release and any conditions or revisions; guidance is separate from analyst forecasts and actual results.",
  ],
};
