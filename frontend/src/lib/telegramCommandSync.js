// When /explain or /watch finishes in Telegram, the open app re-reads the same
// saved result: it fires the existing "fledge:home-changed" event, which the
// home page and "Your list today" already listen for (the company page's own
// 30-second refresh picks up a new watch). Polls only while the page is
// visible, and stops for this visit when Telegram commands are off.
export const SYNC_MS = 20000;

// Pure step, tested: what to do with one answer from the server.
export function syncStep(previous, result) {
  if (!result?.enabled) return { stop: true, changed: false, last: previous };
  const last = result.latest?.id ?? null;
  return {
    stop: false,
    // The first answer only sets the baseline; nothing changed yet.
    changed: previous !== undefined && last !== previous,
    last,
  };
}
