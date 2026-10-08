// Adapted from Kestrel src/api/client.js; same cookie/error/result contract.
// This local slice bootstraps an OS-local demo session, not a production login.
const BASE = "/api/v1";
export class ApiError extends Error {
  constructor(status, message, body, code = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
    this.code = code;
  }
}
async function request(path, { method = "GET", body } = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-Thesis-Request": "local-ui",
    },
    body: body != null ? JSON.stringify(body) : undefined,
  });
  let parsed = null;
  try {
    parsed = await res.json();
  } catch {
    /* Preserve a useful failure for non-JSON responses. */
  }
  if (!res.ok) {
    const first = parsed?.result?.errors?.[0];
    throw new ApiError(
      res.status,
      first?.error_message ||
        "The local app could not complete that request. Your input is preserved.",
      parsed,
      first?.error_code,
    );
  }
  return parsed && Object.prototype.hasOwnProperty.call(parsed, "result")
    ? parsed.result
    : parsed;
}
export const api = {
  saveResearchQuestion: (id, question) =>
    request(`/companies/${id}/question-library`, {
      method: "PUT",
      body: { question },
    }),
  researchLoading: (id) => request(`/companies/${id}/loading`),
  startResearchLoading: (id, body = {}) =>
    request(`/companies/${id}/loading`, { method: "POST", body }),
  telegram: () => request("/telegram"),
  telegramConnect: () => request("/telegram/connect", { method: "POST" }),
  telegramCheck: () => request("/telegram/check", { method: "POST" }),
  telegramDelivery: (enabled) =>
    request("/telegram/delivery", { method: "POST", body: { enabled } }),
  telegramDisconnect: () => request("/telegram/disconnect", { method: "POST" }),
  telegramTest: () => request("/telegram/test", { method: "POST" }),
  scheduledReviews: (before = null) =>
    request(
      `/scheduled-reviews${before ? `?before=${encodeURIComponent(before)}` : ""}`,
    ),
  saveReviewSchedule: (body) =>
    request("/review-schedule", { method: "POST", body }),
  savedReview: (id, page = 0) =>
    request(`/scheduled-reviews/${id}?page=${page}`),
  seeReview: (id) =>
    request(`/scheduled-reviews/${id}/seen`, { method: "POST" }),
  conversation: (id, collect = false) =>
    request(`/social-sources/${id}/conversation`, {
      method: collect ? "POST" : "GET",
    }),
  eventWatch: (id, version_id) =>
    request(`/companies/${id}/event-watch`, {
      method: "POST",
      body: { version_id },
    }),
  filingWatch: (id, enabled) =>
    request(`/companies/${id}/filing-watch`, {
      method: "POST",
      body: { enabled },
    }),
  filingChecks: (id, before = null) =>
    request(
      `/companies/${id}/filing-checks${before ? `?before=${encodeURIComponent(before)}` : ""}`,
    ),
  sentimentHistory: (id, before = null) =>
    request(
      `/companies/${id}/sentiment-history${before ? `?before=${encodeURIComponent(before)}` : ""}`,
    ),
  sentimentComparison: (id, before, after) =>
    request(
      `/companies/${id}/sentiment-comparison?${new URLSearchParams({ before, after })}`,
    ),
  watchChecks: (id, before = null) =>
    request(
      `/companies/${id}/watch-checks${before ? `?before=${encodeURIComponent(before)}` : ""}`,
    ),
  askResearch: (id, body) =>
    request(`/companies/${id}/questions`, { method: "POST", body }),
  themeHistory: (id, analysisId, before = null) =>
    request(
      `/companies/${id}/discussion-themes?${new URLSearchParams({ ...(analysisId ? { analysis_id: analysisId } : {}), ...(before ? { before } : {}) })}`,
    ),
  generateThemes: (id, analysisId) =>
    request(`/companies/${id}/sentiment/${analysisId}/discussion-themes`, {
      method: "POST",
    }),
  expectationHistory: (id, before = null) =>
    request(
      `/companies/${id}/expectations${before ? `?before=${encodeURIComponent(before)}` : ""}`,
    ),
  extractExpectations: (id) =>
    request(`/companies/${id}/expectations`, { method: "POST" }),
  questionHistory: (id, before = null) =>
    request(
      `/companies/${id}/questions${before ? `?before=${encodeURIComponent(before)}` : ""}`,
    ),
  researchAnswer: (id) => request(`/research-answers/${id}`),
  priceHistory: (id) => request(`/companies/${id}/price-history`),
  refreshPriceHistory: (id) =>
    request(`/companies/${id}/price-history/refresh`, { method: "POST" }),
  valuationContext: (id) => request(`/companies/${id}/valuation`),
  refreshAnalystTargets: (id) =>
    request(`/companies/${id}/analyst-targets/refresh`, { method: "POST" }),
  refreshMultiples: (id) =>
    request(`/companies/${id}/multiples/refresh`, { method: "POST" }),
  previewValuation: (body) =>
    request("/valuation/preview", { method: "POST", body }),
  saveValuation: (body) => request("/valuation/save", { method: "POST", body }),
  valuationRecord: (id) => request(`/valuations/${id}`),
  researchReview: (filters) =>
    request(
      `/research-review?${new URLSearchParams(Object.entries(filters).filter(([, v]) => v !== "" && v != null))}`,
    ),
  refreshSocial: (id) =>
    request(`/companies/${id}/social/refresh`, { method: "POST" }),
  sentiment: (id) => request(`/companies/${id}/sentiment`, { method: "POST" }),
  newsWatch: (
    id,
    enabled,
    interval_minutes,
    match_idea,
    include_context,
    idea_purpose,
  ) =>
    request(`/companies/${id}/news-watch`, {
      method: "POST",
      body: {
        enabled,
        interval_minutes,
        match_idea,
        include_context,
        idea_purpose,
      },
    }),
  ideaAlertCheck: (id, analysis_id, version_id, purpose) =>
    request(`/companies/${id}/idea-alert-check`, {
      method: "POST",
      body: { analysis_id, version_id, purpose },
    }),
  reviewIdeaAlert: (id, action) =>
    request(`/idea-alerts/${id}/review`, { method: "POST", body: { action } }),
  reviewAlert: (id, action) =>
    request(`/research-alerts/${id}/review`, {
      method: "POST",
      body: { action },
    }),
  suggest: (body) => request("/proposals/generate", { method: "POST", body }),
  approveSuggestions: (proposal_ids, definition) =>
    request("/proposals/approve", {
      method: "POST",
      body: { proposal_ids, definition },
    }),
  rejectSuggestion: (id) =>
    request(`/proposals/${id}/reject`, { method: "POST" }),
  checkEvents: (version_id, snapshot_id, event_periods) =>
    request(`/ideas/versions/${version_id}/event-review`, {
      method: "POST",
      body: {
        snapshot_id,
        ...(event_periods && Object.keys(event_periods).length
          ? { event_periods }
          : {}),
      },
    }),
  compareEvidence: (version_id, snapshot_id, evaluation_id = null) =>
    request(`/ideas/versions/${version_id}/evidence-review`, {
      method: "POST",
      body: { snapshot_id, evaluation_id },
    }),
  refreshMarket: (id) => request(`/market/${id}/refresh`, { method: "POST" }),
  marketBrief: (id) => request(`/market/${id}/brief`, { method: "POST" }),
  companyDirectory: (query = "") =>
    request(`/company-directory?q=${encodeURIComponent(query)}`),
  refreshCompanyDirectory: () =>
    request("/company-directory/refresh", { method: "POST" }),
  addSecCompany: (symbol) =>
    request("/sec/companies", { method: "POST", body: { symbol } }),
  refreshSec: (id) => request(`/sec/${id}/refresh`, { method: "POST" }),
  session: () => request("/session"),
  modelStatus: () => request("/model-status"),
  selectPassages: (expected_stage, instrument_id) =>
    request("/research/selection", {
      method: "POST",
      body: { expected_stage, instrument_id },
    }),
  workspace: (instrument_id) =>
    request(
      `/workspace${instrument_id ? `?instrument_id=${encodeURIComponent(instrument_id)}` : ""}`,
    ),
  save: (body, instrument_id) =>
    request("/idea", {
      method: "POST",
      body: { ...body, ...(instrument_id ? { instrument_id } : {}) },
    }),
  research: (body) => request("/research-actions", { method: "POST", body }),
  review: (id, action) =>
    request(`/evaluations/${id}/review`, { method: "POST", body: { action } }),
  advance: (expected_stage, instrument_id) =>
    request("/demo/advance", {
      method: "POST",
      body: { expected_stage, instrument_id },
    }),
};
