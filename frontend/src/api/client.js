// Adapted from Kestrel src/api/client.js; same cookie/error/result contract.
// Managed identities are verified by the server; provider tokens stay there.
import { companyCache } from "../lib/companyCache.js";
import { expandSharedTexts } from "../lib/sharedTexts.js";

const BASE = "/api/v1";
let accountId = null;
// The signed-in account from the last session read (null before it).
export const currentAccount = () => accountId;
function setAccount(next) {
  if (next !== accountId) companyCache.clear();
  accountId = next;
}
export class ApiError extends Error {
  constructor(status, message, body, code = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
    this.code = code;
  }
}
async function request(path, { method = "GET", body, signal } = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    signal,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-Thesis-Request": "local-ui",
      ...(accountId && path !== "/session"
        ? { "X-Thesis-Account": accountId }
        : {}),
    },
    body: body != null ? JSON.stringify(body) : undefined,
  });
  const responseAccount = res.headers.get("X-Thesis-Account");
  if (
    path !== "/session" &&
    accountId &&
    responseAccount &&
    responseAccount !== accountId
  ) {
    setAccount(null);
    window.dispatchEvent(new Event("thesis:account-changed"));
    throw new ApiError(
      409,
      "Your signed-in account changed. The previous action was not applied.",
    );
  }
  let parsed = null;
  try {
    parsed = await res.json();
  } catch (error) {
    if (signal?.aborted || error.name === "AbortError") throw error;
    /* Preserve a useful failure for non-JSON responses. */
  }
  if (!res.ok) {
    if (
      res.status === 401 &&
      path !== "/session" &&
      !path.startsWith("/auth/")
    ) {
      window.dispatchEvent(new Event("thesis:sign-in-required"));
    }
    const first = parsed?.result?.errors?.[0];
    const failure = new ApiError(
      res.status,
      first?.error_message ||
        "The local app could not complete that request. Your input is preserved.",
      parsed,
      first?.error_code,
    );
    const retry = res.headers.get("Retry-After");
    failure.retryAfter = retry && /^\d+$/.test(retry) ? Number(retry) : null;
    throw failure;
  }
  const result =
    parsed && Object.prototype.hasOwnProperty.call(parsed, "result")
      ? parsed.result
      : parsed;
  if (path === "/session")
    setAccount(result?.authenticated ? result.account_id : null);
  if (path === "/auth/logout") setAccount(null);
  return result;
}
export const api = {
  financialRecovery: (id, documentId) =>
    request(
      `/companies/${id}/financial-recovery${documentId ? `?document_id=${encodeURIComponent(documentId)}` : ""}`,
    ),
  generateFinancialRecovery: (id, body) =>
    request(`/companies/${id}/financial-recovery`, { method: "POST", body }),
  reviewFinancialRecovery: (id, readingId, body) =>
    request(`/companies/${id}/financial-recovery/${readingId}/review`, {
      method: "POST",
      body,
    }),
  fmp: (id) => request(`/companies/${id}/fmp`),
  sectorPosition: (id, peers) =>
    request(
      `/companies/${id}/sector-position${peers == null ? "" : `?peers=${encodeURIComponent(peers.join(","))}`}`,
    ),
  refreshFmp: (id, only) =>
    request(`/companies/${id}/fmp/refresh${only ? `?only=${only}` : ""}`, {
      method: "POST",
    }),
  refreshPublicForecasts: (id) =>
    request(`/companies/${id}/financial-forecasts/refresh`, { method: "POST" }),
  savePeers: (id, selections) =>
    request(`/companies/${id}/fmp/peers`, {
      method: "PUT",
      body: { selections },
    }),
  login: (email) => request("/auth/login", { method: "POST", body: { email } }),
  logout: () => request("/auth/logout", { method: "POST" }),
  register: (username, password, termsVersion) =>
    request("/auth/register", {
      method: "POST",
      body: {
        username,
        password,
        accept_terms: !!termsVersion,
        terms_version: termsVersion || "",
      },
    }),
  acceptTerms: (terms_version) =>
    request("/terms/accept", { method: "POST", body: { terms_version } }),
  passwordReset: (username, recovery_code, password) =>
    request("/auth/password-reset", {
      method: "POST",
      body: { username, recovery_code, password },
    }),
  changePassword: (current_password, new_password) =>
    request("/account/password", {
      method: "POST",
      body: { current_password, new_password },
    }),
  newRecoveryCode: (current_password) =>
    request("/account/recovery-code", {
      method: "POST",
      body: { current_password },
    }),
  legal: () => request("/legal"),
  passwordLogin: (username, password) =>
    request("/auth/password-login", {
      method: "POST",
      body: { username, password },
    }),
  businessHistory: (id, before = null) =>
    request(
      `/companies/${id}/business${before ? `?before=${encodeURIComponent(before)}` : ""}`,
    ),
  generateBusiness: (id) =>
    request(`/companies/${id}/business`, { method: "POST" }),
  disclosures: (id) => request(`/companies/${id}/disclosures`),
  refreshDisclosures: (id) =>
    request(`/companies/${id}/disclosures/refresh`, { method: "POST" }),
  disclosure: (id, documentId) =>
    request(`/companies/${id}/disclosures/${documentId}`),
  saveResearchQuestion: (id, question) =>
    request(`/companies/${id}/question-library`, {
      method: "PUT",
      body: { question },
    }),
  researchLoading: (id) => request(`/companies/${id}/loading`),
  // Long poll: the server holds this for up to `wait` seconds and answers as
  // soon as the run or pending work differs from the `since` token.
  researchActivity: (id, { since = "", wait = 0, signal } = {}) =>
    request(
      `/companies/${id}/activity?since=${encodeURIComponent(since)}&wait=${wait}`,
      { signal },
    ),
  startResearchLoading: (id, body = {}) =>
    request(`/companies/${id}/loading`, { method: "POST", body }),
  telegram: () => request("/telegram"),
  // Newest Telegram command that changed saved data ({enabled, latest}).
  telegramCommandLatest: ({ signal } = {}) =>
    request("/telegram/commands/latest", { signal }),
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
  alertPreviousSample: (id) =>
    request(`/research-alerts/${id}/previous-sample`),
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
  expectationHistory: (id, before = null, options) =>
    request(
      `/companies/${id}/expectations${before ? `?before=${encodeURIComponent(before)}` : ""}`,
      options,
    ),
  extractExpectations: (id) =>
    request(`/companies/${id}/expectations`, { method: "POST" }),
  questionHistory: (id, before = null) =>
    request(
      `/companies/${id}/questions${before ? `?before=${encodeURIComponent(before)}` : ""}`,
    ),
  researchAnswer: (id) => request(`/research-answers/${id}`),
  priceHistory: (id, options) =>
    request(`/companies/${id}/price-history`, options),
  workspaceFinancials: (id, options) =>
    request(`/companies/${id}/workspace-financials`, options),
  financialStory: (id) => request(`/companies/${id}/financial-story`),
  refreshPriceHistory: (id) =>
    request(`/companies/${id}/price-history/refresh`, { method: "POST" }),
  valuationContext: (id, options) =>
    request(`/companies/${id}/valuation`, options),
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
  reviewMoveAlert: (id, action) =>
    request(`/move-alerts/${id}/review`, { method: "POST", body: { action } }),
  rateAlert: (kind, id, value) =>
    request(`/alerts/${kind}/${id}/rating`, {
      method: "POST",
      body: { value },
    }),
  dailyUpdates: () => request("/daily-updates"),
  dailyDigest: (id, page = 0) => request(`/daily-updates/${id}?page=${page}`),
  priceReferences: (id) => request(`/companies/${id}/price-references`),
  setPriceReference: (id, symbol) =>
    request(`/companies/${id}/price-references`, {
      method: "POST",
      body: { symbol },
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
  session: (options) => request("/session", options),
  profile: () => request("/profile"),
  saveProfile: (body) => request("/profile", { method: "PUT", body }),
  saveDetailMode: (detail_mode) =>
    request("/profile/detail-mode", { method: "PUT", body: { detail_mode } }),
  home: () => request("/home"),
  worldNews: () => request("/world-news"),
  portfolio: () => request("/portfolio"),
  explainPortfolio: () => request("/portfolio/explain", { method: "POST" }),
  refreshWorldNews: () => request("/world-news/refresh", { method: "POST" }),
  checkWorldNews: () => request("/world-news/check", { method: "POST" }),
  addToWatchlist: (instrument_id) =>
    request("/watchlist", { method: "POST", body: { instrument_id } }),
  removeFromWatchlist: (instrument_id) =>
    request(`/watchlist/${instrument_id}`, { method: "DELETE" }),
  modelStatus: (options) => request("/model-status", options),
  selectPassages: (expected_stage, instrument_id) =>
    request("/research/selection", {
      method: "POST",
      body: { expected_stage, instrument_id },
    }),
  // Light reads for the home cards: every saved quote, then per-company
  // news tone and (Pro) the two trailing filing figures.
  homeCards: ({ signal } = {}) => request("/home-cards", { signal }),
  // Saved widget arrangement for the overview or home page ({lg, md, sm, hidden}).
  layout: (page, { signal } = {}) => request(`/layouts/${page}`, { signal }),
  saveLayout: (page, body) =>
    request(`/layouts/${page}`, { method: "PUT", body }),
  resetLayout: (page) => request(`/layouts/${page}`, { method: "DELETE" }),
  // This company's alerts with details; the company read has status only.
  companyAlerts: (id, { signal } = {}) =>
    request(`/companies/${id}/alerts`, { signal }),
  homeCard: (id, { figures = true, signal } = {}) =>
    request(`/companies/${id}/home-card?figures=${figures}`, { signal }),
  // `known`: the revision of the copy already on screen; an unchanged company
  // answers `{unchanged: true}` instead of everything again. `shared=1`: this
  // page puts repeated source texts back (expandSharedTexts), so the server
  // may send each once.
  workspace: (
    instrument_id,
    { includeFinancials = true, signal, known } = {},
  ) =>
    request(
      `/workspace?shared=1&include_financials=${includeFinancials}${instrument_id ? `&instrument_id=${encodeURIComponent(instrument_id)}` : ""}${known ? `&known=${encodeURIComponent(known)}` : ""}`,
      { signal },
    ).then(expandSharedTexts),
  // Loaded separately from the workspace so presenting every saved relevance
  // check never delays the page.
  ideaAlerts: ({ signal } = {}) => request("/idea-alerts", { signal }),
  save: (body, instrument_id) =>
    request("/idea", {
      method: "POST",
      body: { ...body, ...(instrument_id ? { instrument_id } : {}) },
    }),
  archiveIdea: (instrument_id) =>
    request(`/companies/${instrument_id}/idea/archive`, { method: "POST" }),
  research: (body) => request("/research-actions", { method: "POST", body }),
  review: (id, action) =>
    request(`/evaluations/${id}/review`, { method: "POST", body: { action } }),
  advance: (expected_stage, instrument_id) =>
    request("/demo/advance", {
      method: "POST",
      body: { expected_stage, instrument_id },
    }),
};
