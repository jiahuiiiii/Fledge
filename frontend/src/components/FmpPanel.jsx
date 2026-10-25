import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import AnalystForecasts from "./AnalystForecasts";
import { requestUpdate } from "../lib/updateRequest";

// Saved analyst forecasts for the Financials tab. Reading is free; checking
// the provider is an explicit button inside the table.
export default function FmpPanel({ instrumentId, visible, revision }) {
  const [data, setData] = useState(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const mounted = useRef(true);
  const actionBusy = useRef(false);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  useEffect(() => {
    let active = true;
    if (visible && !actionBusy.current)
      api
        .fmp(instrumentId)
        .then((result) => {
          if (active && mounted.current) {
            setData(result);
            setError("");
          }
        })
        .catch((failure) => {
          if (active && mounted.current) setError(failure.message);
        });
    return () => {
      active = false;
    };
  }, [instrumentId, visible, revision]);
  async function check() {
    if (actionBusy.current) return;
    actionBusy.current = true;
    setBusy(true);
    setError("");
    try {
      const result = (await api.refreshFmp(instrumentId)).context;
      if (mounted.current) setData(result);
    } catch (failure) {
      if (mounted.current) setError(failure.message);
    } finally {
      actionBusy.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  return (
    <AnalystForecasts
      data={data}
      busy={busy}
      error={error}
      onCheck={check}
      onCheckPublic={requestUpdate}
    />
  );
}
