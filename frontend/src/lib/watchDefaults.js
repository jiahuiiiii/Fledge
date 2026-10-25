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
