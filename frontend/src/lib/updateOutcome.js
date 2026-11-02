// What to tell someone when an Update data run finishes. Update collects news,
// posts and prices; it never rates them (that is Rate on the Summary). Most
// sources have a cooldown (minutes to a day), so a second Update soon after
// another fetches nothing new: say that instead of "up to date".
const FETCHED = new Set(["ready", "partial"]);

export function updateOutcome(steps = [], name = "This company") {
  const sources = steps.filter((s) => s.key !== "analysis");
  if (sources.length && sources.every((s) => s.status === "failed"))
    return `Couldn’t update ${name} right now. Saved data is still shown; try again later.`;
  if (!sources.some((s) => FETCHED.has(s.status)))
    return `Nothing new to fetch for ${name}: its sources were checked in the last few minutes, so the saved news is shown. Update doesn’t rate news; use Rate on the Summary for that.`;
  return `${name} is updated. Anything new is on the Summary; rate it there to see what’s good or bad.`;
}
