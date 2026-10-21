import { api } from "../api/client";
import { priceRefreshDelay } from "./priceRefresh";

// How often open pages ask for a newer price. The server still enforces its
// own one-minute cooldown per company and its Yahoo pacing.
export const LIVE_PRICE_MS = 60_000;

// Read the saved price; if it is due, ask the server to fetch a newer one.
export async function freshPrice(id) {
  let next = await api.priceHistory(id);
  if (priceRefreshDelay({ ...next, error: null }) === 0 && !next.refreshing) {
    try {
      await api.refreshPriceHistory(id);
    } catch {
      return next; // Cooldown or source problem: keep the saved price.
    }
    next = await api.priceHistory(id);
  }
  return next;
}
