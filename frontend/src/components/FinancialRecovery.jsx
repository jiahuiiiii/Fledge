import { Fragment, useEffect, useId, useRef, useState } from "react";
import { api } from "../api/client";
import Select from "./Select";
import { Button } from "./ui";
import { day, money } from "../lib/financialStory";

export default function FinancialRecovery({ instrumentId, onApplied }) {
  const [open, setOpen] = useState(false);
  const [documentId, setDocumentId] = useState("");
  const [selectedIds, setSelectedIds] = useState([]);
  const [previewError, setPreviewError] = useState("");
  const checklistId = useId();
  const [plan, setPlan] = useState(null);
  const [accepted, setAccepted] = useState([]);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const [firstLoad, setFirstLoad] = useState("loading");
  // Free previews of every report still waiting for an AI reading.
  const [batch, setBatch] = useState(null);
  const generation = useRef(0);
  // Read on mount (saved data only, no AI) so the panel can stay hidden when
  // the charts have no gaps it could help with.
  useEffect(() => {
    const token = ++generation.current;
    setPlan(null);
    api
      .financialRecovery(instrumentId, documentId)
      .then((next) => {
        if (token !== generation.current) return;
        setPlan(next);
        setAccepted(next.reading?.accepted || []);
        setFirstLoad((state) => (state === "loading" ? "ready" : state));
      })
      .catch((failure) => {
        if (token !== generation.current) return;
        setError(failure.message);
        setFirstLoad((state) => (state === "loading" ? "failed" : state));
      });
    return () => {
      generation.current++;
    };
  }, [instrumentId, documentId, revision]);
  useEffect(() => {
    setDocumentId("");
    setFirstLoad("loading");
    setSelectedIds([]);
    setBusy("");
    setError("");
    setBatch(null);
    setOpen(false);
  }, [instrumentId]);
  const pendingIds = (plan?.documents || [])
    .filter((doc) => doc.gaps?.length && !doc.saved)
    .map((doc) => doc.id)
    .join();
  useEffect(() => {
    setBatch(null);
    setPreviewError("");
    if (!open || !pendingIds) return;
    let live = true;
    Promise.all(
      pendingIds
        .split(",")
        .map((id) => api.financialRecovery(instrumentId, id)),
    )
      .then((previews) => live && setBatch(previews))
      .catch((failure) => live && setPreviewError(failure.message));
    return () => {
      live = false;
    };
  }, [open, instrumentId, pendingIds, revision]);
  async function runAll(runnable) {
    const token = generation.current;
    setError("");
    let done = 0;
    try {
      for (const preview of runnable) {
        if (token !== generation.current) return;
        setBusy(`Reading report ${done + 1} of ${runnable.length} with AI…`);
        await api.generateFinancialRecovery(instrumentId, {
          document_id: preview.document.id,
          plan_id: preview.plan_id,
        });
        if (token !== generation.current) return;
        done += 1;
        setSelectedIds((ids) => ids.filter((id) => id !== preview.document.id));
      }
    } catch (failure) {
      if (token === generation.current)
        setError(
          `${failure.message} ${done} of ${runnable.length} reports were read; their suggestions are saved.`,
        );
    } finally {
      if (token === generation.current) {
        setBusy("");
        // Show the first report's suggestions; the list marks the others.
        if (done) setDocumentId(runnable[0].document.id);
        setRevision((n) => n + 1);
      }
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
  // Nothing to offer: no chart gap in any saved report, or no readable report.
  if (
    firstLoad === "failed" ||
    (firstLoad === "ready" && !plan?.has_gaps && !open)
  )
    return null;
  const reading = plan?.reading;
  const items = reading?.result?.items || [];
  const saved = reading?.accepted || [];
  const unchanged = [...accepted].sort().join() === [...saved].sort().join();
  const runnable = (batch || []).filter(
    (preview) => preview.can_run && preview.candidate_cells > 0,
  );
  const selected = runnable.filter((preview) =>
    selectedIds.includes(preview.document.id),
  );
  const selectedCost = selected.reduce((sum, p) => sum + p.maximum_cost_usd, 0);
  const allSelected =
    runnable.length > 0 && selected.length === runnable.length;
  const pending = (plan?.documents || []).filter(
    (doc) => doc.gaps?.length && !doc.saved,
  );
  const reviewed = (plan?.documents || []).filter((doc) => doc.saved);
  const reportCount = (plan?.documents || []).filter(
    (doc) => doc.gaps?.length,
  ).length;
  const gapList = (doc) =>
    batch
      ?.find((preview) => preview.document.id === doc.id)
      ?.missing?.map((item) => item.label) ||
    doc.gaps ||
    [];
  const gapKey = (doc) => [...gapList(doc)].sort().join("|");
  const commonGaps =
    pending.length > 0 &&
    pending.every((doc) => gapKey(doc) === gapKey(pending[0]))
      ? gapList(pending[0]).map(short).join(", ")
      : "";
  return (
    <section
      className="financial-recovery"
      aria-label="Missing financial figures"
    >
      <div className="financial-recovery-header">
        <Button
          variant="plain"
          className="financial-recovery-toggle"
          aria-expanded={open}
          aria-controls={checklistId}
          onClick={() => setOpen((value) => !value)}
        >
          <svg
            className="recovery-chevron"
            viewBox="0 0 16 16"
            width="16"
            height="16"
            aria-hidden="true"
          >
            <path
              d="m6 4 4 4-4 4"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <span className="financial-recovery-label">
            <span>Fill missing figures</span>
            {reportCount > 0 && (
              <small>
                {reportCount} {reportCount === 1 ? "report" : "reports"}
              </small>
            )}
          </span>
        </Button>
        {open && pending.length > 0 && (
          <Button
            variant="plain"
            disabled={Boolean(busy) || !runnable.length}
            onClick={() =>
              setSelectedIds(
                allSelected ? [] : runnable.map((p) => p.document.id),
              )
            }
          >
            {allSelected ? "Clear selection" : "Select all"}
          </Button>
        )}
      </div>
      <div id={checklistId} hidden={!open}>
        {open && (
          <div className="financial-recovery-body">
            <p className="muted">
              Choose reports, then review the suggestions before using them.
            </p>
            {plan && (
              <>
                {pending.length > 0 && (
                  <>
                    {commonGaps && (
                      <p className="recovery-common-gaps">{commonGaps}</p>
                    )}
                    <fieldset
                      className="recovery-checklist"
                      disabled={Boolean(busy)}
                    >
                      <legend className="sr-only">
                        Reports with missing figures
                      </legend>
                      {pending.map((doc) => {
                        const preview = batch?.find(
                          (p) => p.document.id === doc.id,
                        );
                        const available =
                          preview?.can_run && preview.candidate_cells > 0;
                        return (
                          <label
                            className="recovery-checklist-row"
                            key={doc.id}
                          >
                            <input
                              type="checkbox"
                              checked={Boolean(
                                available && selectedIds.includes(doc.id),
                              )}
                              disabled={!available}
                              onChange={(event) =>
                                setSelectedIds((ids) =>
                                  event.target.checked
                                    ? [...ids, doc.id]
                                    : ids.filter((id) => id !== doc.id),
                                )
                              }
                            />
                            <span className="recovery-checklist-copy">
                              <strong>
                                {doc.form === "10-K" ? "Annual" : "Quarterly"} ·{" "}
                                {day(doc.end)}
                              </strong>
                              {!commonGaps && (
                                <span>
                                  {gapList(doc).map(short).join(", ")}
                                </span>
                              )}
                              {preview && !available && (
                                <small>{preview.message}</small>
                              )}
                            </span>
                          </label>
                        );
                      })}
                    </fieldset>
                    {!batch && !previewError && (
                      <p role="status">Checking reports…</p>
                    )}
                    {previewError && (
                      <p role="alert">
                        {previewError}{" "}
                        <button
                          disabled={Boolean(busy)}
                          onClick={() => setRevision((n) => n + 1)}
                        >
                          Reload reports
                        </button>
                      </p>
                    )}
                    <div className="recovery-run">
                      <button
                        className="primary"
                        disabled={!selected.length || Boolean(busy)}
                        onClick={() => runAll(selected)}
                      >
                        Find figures with AI
                        {selected.length > 0
                          ? ` · ${selected.length} ${selected.length === 1 ? "report" : "reports"}`
                          : ""}
                      </button>
                      <span className="muted" aria-live="polite">
                        {selected.length > 0 &&
                          `At most US$${(Math.ceil(selectedCost * 10000) / 10000).toFixed(4)} in total`}
                      </span>
                    </div>
                    {selected.some((preview) => preview.omitted_cells > 0) && (
                      <p className="muted">
                        Some figures may remain unavailable because the
                        statement sample is limited.
                      </p>
                    )}
                  </>
                )}
                {reviewed.length > 0 && (
                  <label className="recovery-report">
                    <span>Review saved suggestions</span>
                    <Select
                      value={reading ? plan.document.id : ""}
                      disabled={Boolean(busy)}
                      onChange={(event) => {
                        setError("");
                        setDocumentId(event.target.value);
                      }}
                    >
                      {!reading && (
                        <option value="" disabled>
                          Choose a report
                        </option>
                      )}
                      {reviewed.map((doc) => (
                        <option key={doc.id} value={doc.id}>
                          {doc.form === "10-K" ? "Annual" : "Quarterly"} ·{" "}
                          {day(doc.end)}
                        </option>
                      ))}
                    </Select>
                  </label>
                )}
                {!reading && !pending.length && (
                  <p className="muted">{plan.message}</p>
                )}
                {reading?.withheld && (
                  <p role="alert">
                    The original report is no longer accessible, so these
                    suggestions are hidden.
                  </p>
                )}
                {reading?.result && (
                  <section
                    className="recovery-results"
                    aria-label="Suggested figures"
                  >
                    <div className="recovery-results-head">
                      <h4>Suggested figures</h4>
                      <a
                        href={reading.document.url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Check the original {reading.document.form} ↗
                      </a>
                    </div>
                    <p className="muted">
                      Check each figure against the original report before using
                      it.
                    </p>
                    {items.map((item) => {
                      const using = accepted.includes(item.id);
                      return (
                        <article
                          className={`recovery-card${using ? " using" : ""}`}
                          key={item.id}
                        >
                          <div className="recovery-card-head">
                            <div>
                              <span>{short(item.label)}</span>
                              <strong>{money(item.value)}</strong>
                              <small>
                                {item.start
                                  ? `${day(item.start)} – ${day(item.end)}`
                                  : `At ${day(item.end)}`}
                                {saved.includes(item.id) &&
                                  " · used in your charts"}
                              </small>
                            </div>
                            <label className="recovery-use">
                              <input
                                type="checkbox"
                                disabled={Boolean(busy)}
                                checked={using}
                                onChange={(event) =>
                                  setAccepted((old) =>
                                    event.target.checked
                                      ? [...old, item.id]
                                      : old.filter((id) => id !== item.id),
                                  )
                                }
                              />
                              Use in my charts
                            </label>
                          </div>
                          <div className="recovery-sum">
                            {item.inputs.map((input, index) => (
                              <Fragment key={input.id}>
                                {index > 0 && (
                                  <span
                                    className="recovery-op"
                                    aria-hidden="true"
                                  >
                                    {item.operation === "subtract" ? "−" : "+"}
                                  </span>
                                )}
                                <a
                                  className="recovery-part"
                                  href={`${reading.document.url}#${encodeURIComponent(input.id)}`}
                                  target="_blank"
                                  rel="noreferrer"
                                >
                                  <span>{input.label}</span>
                                  <strong>{money(input.value)}</strong>
                                </a>
                              </Fragment>
                            ))}
                            {item.inputs.length > 1 && (
                              <>
                                <span
                                  className="recovery-op"
                                  aria-hidden="true"
                                >
                                  =
                                </span>
                                <span className="recovery-part total">
                                  <span>{short(item.label)}</span>
                                  <strong>{money(item.value)}</strong>
                                </span>
                              </>
                            )}
                          </div>
                          <p className="recovery-note">
                            AI note: {item.explanation}
                          </p>
                          <details className="recovery-rows">
                            <summary>Show the original statement rows</summary>
                            <table>
                              <tbody>
                                {item.inputs.map((input) => {
                                  const cells = rowCells(input.text);
                                  return (
                                    <tr key={input.id}>
                                      <th scope="row">
                                        {cells[0] || input.label}
                                      </th>
                                      {cells.slice(1).map((cell, index) => (
                                        <td key={index}>{cell}</td>
                                      ))}
                                    </tr>
                                  );
                                })}
                              </tbody>
                            </table>
                            <p className="muted">
                              As printed in the filing, usually in millions. The
                              first column is normally this report’s date.
                            </p>
                          </details>
                        </article>
                      );
                    })}
                    {items.length > 0 && (
                      <div className="recovery-run">
                        {items.length > 1 && (
                          <button
                            disabled={
                              Boolean(busy) ||
                              items.every((item) => accepted.includes(item.id))
                            }
                            onClick={() =>
                              setAccepted(items.map((item) => item.id))
                            }
                          >
                            Use all {items.length}
                          </button>
                        )}
                        <button
                          className="primary"
                          disabled={Boolean(busy) || unchanged}
                          onClick={save}
                        >
                          {unchanged ? "Choices saved" : "Save my choices"}
                        </button>
                        <span className="muted">
                          Untick and save to remove a figure.
                        </span>
                      </div>
                    )}
                    {items.length === 0 && (
                      <p>
                        The AI couldn’t match these figures to the report’s
                        lines, so they stay blank.
                      </p>
                    )}
                    {reading.result.unresolved.length > 0 &&
                      items.length > 0 && (
                        <p className="muted">
                          Not found: {reading.result.unresolved.length}{" "}
                          {reading.result.unresolved.length === 1
                            ? "figure"
                            : "figures"}
                          .
                        </p>
                      )}
                    {reading.result.rejected.length > 0 && (
                      <p className="muted">
                        {reading.result.rejected.length} suggestion
                        {reading.result.rejected.length === 1 ? "" : "s"} failed
                        the app’s checks and{" "}
                        {reading.result.rejected.length === 1 ? "was" : "were"}{" "}
                        left out.
                      </p>
                    )}
                  </section>
                )}
              </>
            )}
            {reading?.result && (
              <p className="muted">
                Reviewed figures update these charts only. Monitoring uses
                reported figures.
              </p>
            )}
            {!plan && !error && <p role="status">Checking saved figures…</p>}
            {busy && <p role="status">{busy}</p>}
            {error && (
              <p role="alert">
                {error}{" "}
                <button
                  disabled={Boolean(busy)}
                  onClick={() => {
                    setError("");
                    setRevision((n) => n + 1);
                  }}
                >
                  Reload preview
                </button>
              </p>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

// "Borrowing (short- and long-term debt)" → "Borrowing" for compact labels.
function short(label) {
  return String(label || "").replace(/\s*\([^)]*\)\s*$/, "");
}

// Saved statement rows are "Label | 1,000 |  | 999 |"; show the non-empty cells.
function rowCells(text) {
  return String(text || "")
    .split("|")
    .map((cell) => cell.trim())
    .filter(Boolean);
}
