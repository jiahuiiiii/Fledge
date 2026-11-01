// Companies opened earlier in this tab, so switching back shows the last page
// at once while a fresh read runs. Kept in memory only (never storage), keyed
// by account so another sign-in never sees them, and limited to a few
// companies because a news-heavy company read is several megabytes.
const LIMIT = 6;

export function createCompanyCache(limit = LIMIT) {
  const entries = new Map();
  return {
    get(account, instrumentId) {
      if (!account || !instrumentId) return null;
      const key = `${account}:${instrumentId}`;
      const entry = entries.get(key);
      if (!entry) return null;
      entries.delete(key);
      entries.set(key, entry);
      return entry;
    },
    put(account, instrumentId, fields) {
      if (!account || !instrumentId) return;
      const key = `${account}:${instrumentId}`;
      const entry = { ...entries.get(key), ...fields };
      entries.delete(key);
      entries.set(key, entry);
      while (entries.size > limit) entries.delete(entries.keys().next().value);
    },
    clear() {
      entries.clear();
    },
    get size() {
      return entries.size;
    },
  };
}

export const FINANCIAL_FIELDS = [
  "financial_depth",
  "income_flow",
  "segment_revenue",
];

// A read without financials keeps the figures already on screen for the same
// company (the filings behind them change only after an update run).
export function keepFinancials(kept, next) {
  if (
    !kept ||
    kept.financials_pending ||
    !next?.financials_pending ||
    kept.instrument?.id !== next.instrument?.id
  )
    return next;
  const result = { ...next, financials_pending: false };
  for (const field of FINANCIAL_FIELDS) result[field] = kept[field];
  return result;
}

export const companyCache = createCompanyCache();
