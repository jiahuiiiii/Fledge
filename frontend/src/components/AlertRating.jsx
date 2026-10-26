import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import "./AlertRating.css";
import { Button } from "./ui";

export default function AlertRating({ record }) {
  const key = `${record.kind}:${record.id}`;
  const current = useRef({ key });
  if (current.current?.key !== key) current.current = { key };
  const [value, setValue] = useState(record.feedback?.value || "");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    const scope = { key };
    current.current = scope;
    setValue(record.feedback?.value || "");
    setBusy(false);
    setNotice("");
    setError("");
    return () => {
      if (current.current === scope) current.current = null;
    };
  }, [key, record.feedback?.value]);
  if (!record.feedback_enabled || record.detail?.withheld) return null;
  async function rate(next) {
    const target = current.current;
    setBusy(true);
    setNotice("");
    setError("");
    try {
      const result = await api.rateAlert(record.kind, record.id, next);
      if (current.current !== target) return;
      setValue(result.value);
      setNotice("Rating saved.");
    } catch (failure) {
      if (current.current === target) setError(failure.message);
    } finally {
      if (current.current === target) setBusy(false);
    }
  }
  return (
    <section className="alert-rating" aria-label="Rate this alert">
      <span>Was this alert useful?</span>
      <div className="alert-rating-choices">
        <Button
          variant="plain"
          size="sm"
          disabled={busy}
          aria-pressed={value === "useful"}
          onClick={() => rate("useful")}
        >
          Useful
        </Button>
        <Button
          variant="plain"
          size="sm"
          disabled={busy}
          aria-pressed={value === "not_useful"}
          onClick={() => rate("not_useful")}
        >
          Not useful
        </Button>
      </div>
      {notice && (
        <p className="fine" role="status">
          {notice}
        </p>
      )}
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
