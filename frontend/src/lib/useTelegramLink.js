import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";

// Is a Telegram chat connected? `configured` is false on installations with no
// bot, where there is nothing to connect and no reason to ask.
export function useTelegramLink() {
  const [state, setState] = useState({ ready: false, configured: false, linked: false });
  const refresh = useCallback(
    () =>
      api
        .telegram()
        .then((value) => {
          const next = { ready: true, configured: !!value?.configured, linked: !!value?.linked };
          setState(next);
          return next;
        })
        .catch(() => {
          setState((old) => ({ ...old, ready: true }));
          return { ready: true, configured: false, linked: false };
        }),
    [],
  );
  useEffect(() => {
    refresh();
  }, [refresh]);
  return { ...state, refresh };
}
