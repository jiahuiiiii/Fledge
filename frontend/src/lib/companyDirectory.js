// The SEC listing directory refreshes itself when the Add company dialog
// opens and the saved copy is missing or more than a day old.
export const LISTING_MAX_AGE_MS = 24 * 60 * 60 * 1000;

export function needsListingUpdate(result, now = Date.now()) {
  if (!result) return false;
  if (!result.retrieved_at) return true;
  const retrieved = Date.parse(result.retrieved_at);
  return !Number.isFinite(retrieved) || now - retrieved > LISTING_MAX_AGE_MS;
}
