import { useEffect } from "react";
import { api } from "../api/client";
import { SYNC_MS, syncStep } from "./telegramCommandSync";

// See telegramCommandSync.js for what this keeps in step and why.
export function useTelegramCommandSync() {
  useEffect(() => {
    let last;
    let stopped = false;
    let timer;
    const controller = new AbortController();
    const schedule = () => {
      if (!stopped) timer = setTimeout(tick, SYNC_MS);
    };
    async function tick() {
      if (document.hidden) return schedule();
      try {
        const step = syncStep(
          last,
          await api.telegramCommandLatest({ signal: controller.signal }),
        );
        if (step.stop) {
          stopped = true;
          return;
        }
        if (step.changed) dispatchEvent(new Event("fledge:home-changed"));
        last = step.last;
      } catch {
        /* An older server or a dropped connection: try again later. */
      }
      schedule();
    }
    tick();
    return () => {
      stopped = true;
      clearTimeout(timer);
      controller.abort();
    };
  }, []);
}
