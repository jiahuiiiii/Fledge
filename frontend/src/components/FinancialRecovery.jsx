import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import Select from "./Select";
import { day, money } from "../lib/financialStory";

export default function FinancialRecovery({ instrumentId, onApplied }) {
  const [open, setOpen] = useState(false);
  const [documentId, setDocumentId] = useState("");
  const [plan, setPlan] = useState(null);
  const [accepted, setAccepted] = useState([]);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const generation = useRef(0);
  useEffect(() => {
    if (!open) return;
    const token = ++generation.current;
    setPlan(null);
    setError("");
    api
      .financialRecovery(instrumentId, documentId)
      .then((next) => {
        if (token !== generation.current) return;
        setPlan(next);
        setAccepted(next.reading?.accepted || []);
      })
      .catch((failure) => {
        if (token === generation.current) setError(failure.message);
      });
    return () => {
      generation.current++;
    };
  }, [instrumentId, documentId, open, revision]);
  async function run() {
    const token = generation.current;
    setBusy("Reading the saved statement with OpenAI…");
    setError("");
    try {
      const reading = await api.generateFinancialRecovery(instrumentId, {
        document_id: plan.document.id,
        plan_id: plan.plan_id,
      });
      if (token !== generation.current) return;
      setPlan((old) => ({
        ...old,
        reading,
        can_run: false,
        maximum_cost_usd: 0,
      }));
      setAccepted(reading.accepted || []);
    } catch (failure) {
      if (token === generation.current) setError(failure.message);
    } finally {
      if (token === generation.current) setBusy("");
    }
  }
  async function save() {
    const token = generation.current;
    setBusy("Saving your review…");
    setError("");
    try {
      const reading = await api.reviewFinancialRecovery(
        instrumentId,
        plan.reading.id,
        { accepted, expected_review: plan.reading.review_id },
      );
      if (token !== generation.current) return;
      setPlan((old) => ({ ...old, reading }));
      await onApplied?.();
    } catch (failure) {
      if (token === generation.current) setError(failure.message);
    } finally {
      if (token === generation.current) setBusy("");
    }
  }
  return (
    <details
      className="financial-recovery financial-chart-card"
      onToggle={(event) => setOpen(event.currentTarget.open)}
    >
      <summary>Missing figures · optional AI help</summary>
      {open && (
        <div className="financial-recovery-body">
          <p>
            The normal reader checks saved statements first. An optional OpenAI
            reading can suggest how original statement cells match a missing
            figure. You review the meaning before using it; calculations are
            checked by the app.
          </p>
          <p className="muted">
            Nothing runs automatically. This uses your existing AI allowance.
            Reviewed suggestions apply to your financial research view;
            monitoring keeps its original reported inputs.
          </p>
          {plan && (
            <>
              <label>
                Saved report{" "}
                <Select
                  value={plan.document.id}
                  disabled={Boolean(busy)}
                  onChange={(event) => setDocumentId(event.target.value)}
                >
                  {plan.documents.map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      {doc.form === "10-K" ? "Annual" : "Quarterly"} ·{" "}
                      {day(doc.end)}
                    </option>
                  ))}
                </Select>
              </label>
              <p>{plan.message}</p>
              {!plan.reading && (
                <>
                  {plan.missing.length > 0 && (
                    <p>
                      Not found by the normal reader:{" "}
                      {plan.missing.map((m) => m.label).join(", ")}.
                    </p>
                  )}
                  {plan.missing.length > 0 && plan.omitted_cells > 0 && (
                    <p>
                      {plan.omitted_cells} other cells are outside this bounded
                      reading. It may leave gaps.
                    </p>
                  )}
                  {plan.candidate_cells > 0 && plan.missing.length > 0 && (
                    <>
                      <p>
                        {plan.candidate_cells} saved cells will be sent to
                        OpenAI. Maximum new cost US$
                        {(
                          Math.ceil(plan.maximum_cost_usd * 10000) / 10000
                        ).toFixed(4)}
                        .
                      </p>
                      <button
                        disabled={!plan.can_run || Boolean(busy)}
                        onClick={run}
                      >
                        Find missing figures with OpenAI
                      </button>
                      {!plan.can_run && (
                        <p>
                          This reading cannot run with the current source or
                          spending state. Check Data &amp; sources for details.
                        </p>
                      )}
                    </>
                  )}
                </>
              )}
              {plan.reading?.withheld && (
                <p role="alert">
                  The original evidence is no longer accessible. These
                  suggestions are withheld.
                </p>
              )}
              {plan.reading?.result && (
                <>
                  <p>
                    <strong>Review suggested figures</strong> · Matching cells
                    and arithmetic do not establish that the financial meaning
                    is correct. Open the original report before accepting a
                    suggestion.
                  </p>
                  <a
                    href={plan.reading.document.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open original {plan.reading.document.form} ↗
                  </a>
                  {plan.reading.result.items.map((item) => (
                    <article className="financial-recovery-item" key={item.id}>
                      <label>
                        <input
                          type="checkbox"
                          disabled={Boolean(busy)}
                          checked={accepted.includes(item.id)}
                          onChange={(event) =>
                            setAccepted((old) =>
                              event.target.checked
                                ? [...old, item.id]
                                : old.filter((id) => id !== item.id),
                            )
                          }
                        />{" "}
                        Use {item.label}: {money(item.value)}
                      </label>
                      <p>
                        {item.start ? `${day(item.start)} – ` : "At "}
                        {day(item.end)} · AI-assisted suggestion
                      </p>
                      <p>{item.explanation}</p>
                      {item.formula && <p>Calculation: {item.formula}</p>}
                      {item.inputs.map((input) => (
                        <blockquote key={input.id}>
                          <a
                            href={`${plan.reading.document.url}#${encodeURIComponent(input.id)}`}
                            target="_blank"
                            rel="noreferrer"
                          >
                            {input.label} · {money(input.value)} ↗
                          </a>
                          <p>{input.text}</p>
                        </blockquote>
                      ))}
                    </article>
                  ))}
                  {plan.reading.result.items.length > 0 && (
                    <button disabled={Boolean(busy)} onClick={save}>
                      Save reviewed figures
                    </button>
                  )}
                  {plan.reading.result.items.length === 0 && (
                    <p>
                      No supported suggestion was found. The missing figures
                      remain unknown.
                    </p>
                  )}
                  {plan.reading.result.unresolved.length > 0 && (
                    <p>
                      {plan.reading.result.unresolved.length} figures remain
                      unresolved.
                    </p>
                  )}
                  {plan.reading.result.rejected.length > 0 && (
                    <p>
                      {plan.reading.result.rejected.length} suggestions failed
                      the evidence checks and were withheld.
                    </p>
                  )}
                  <p className="muted">
                    Uncheck a figure and save again to stop using that
                    interpretation. Saved readings can be reopened without an AI
                    charge.
                  </p>
                </>
              )}
            </>
          )}
          {!plan && !error && <p role="status">Checking saved figures…</p>}
          {busy && <p role="status">{busy}</p>}
          {error && (
            <p role="alert">
              {error}{" "}
              <button
                disabled={Boolean(busy)}
                onClick={() => setRevision((n) => n + 1)}
              >
                Reload saved reading
              </button>
            </p>
          )}
        </div>
      )}
    </details>
  );
}
