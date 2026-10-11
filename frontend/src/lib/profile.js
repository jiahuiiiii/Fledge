import { createContext, useContext } from "react";

// Per-account first-login answers, tailored home content and the
// explain/data preference. `home` comes from GET /api/v1/home.
export const ProfileContext = createContext({
  home: null,
  profile: null,
  setDetailMode: () => {},
});
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
