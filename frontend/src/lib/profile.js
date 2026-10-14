import { createContext, useContext } from "react";

// Per-account first-login answers, tailored home content and the
// explain/data preference. `home` comes from GET /api/v1/home.
// mode is "explain" (Beginner) or "data" (Pro).
export const ProfileContext = createContext({
  home: null,
  profile: null,
  mode: "data",
  setDetailMode: () => {},
});

// Accounts that skipped the first-login questions keep their mode in this
// browser; answered accounts save it on the server.
const MODE_KEY = "fledge:detail-mode";
export function readLocalMode() {
  try {
    const value = localStorage.getItem(MODE_KEY);
    return value === "explain" || value === "data" ? value : null;
  } catch {
    return null;
  }
}
export function writeLocalMode(mode) {
  try {
    localStorage.setItem(MODE_KEY, mode);
  } catch {
    // Storage can be unavailable (private windows); the choice lasts this visit.
  }
}
export const useProfile = () => useContext(ProfileContext);

// Reorder shortcuts to match the user's goal; unknown ids keep their order.
export function orderStarters(items, order) {
  if (!order?.length) return items;
  const rank = (id) => {
    const index = order.indexOf(id);
    return index === -1 ? order.length : index;
  };
  return [...items].sort((a, b) => rank(a.id) - rank(b.id));
}
