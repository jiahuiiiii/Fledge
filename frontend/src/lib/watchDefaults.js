import { defaultEventWindow } from "./eventWindows.js";

// AI suggestions leave an event's dates empty (they never invent a horizon).
// One-click "Watch this" gives such events the same default window a hand-added
// event gets: a week back to ninety days ahead, inclusive UTC publication dates.
export function withDefaultWindows(form, today = new Date()) {
  const window = defaultEventWindow(today);
  let applied = null;
  const events = (form.events || []).map((event) => {
    if (event.window_start && event.deadline) return event;
    applied = window;
    return {
      ...event,
      window_start: event.window_start || window.window_start,
      deadline: event.deadline || window.deadline,
    };
  });
  return { form: { ...form, events }, applied };
}

// A numerical suggestion without a threshold needs the user's own number.
export const needsThreshold = (form) =>
  (form.conditions || []).some(
    (c) => c.value == null || String(c.value).trim() === "",
  );

// A starting point, not advice: the round multiple of 5 just below the latest
// reported figure, so the check begins below where the company is today.
export function suggestThreshold(latest) {
  const value = Number(latest);
  if (latest == null || latest === "" || !Number.isFinite(value)) return null;
  return String(Math.floor((value - 1e-9) / 5) * 5);
}
