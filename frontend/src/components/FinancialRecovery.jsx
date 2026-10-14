import { Fragment, useEffect, useRef, useState } from "react";
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
  const [firstLoad, setFirstLoad] = useState("loading");
  // Free previews of every report still waiting for an AI reading.
  const [batch, setBatch] = useState(null);
  const generation = useRef(0);
  // Read on mount (saved data only, no AI) so the panel can stay hidden when
  // the charts have no gaps it could help with.
  useEffect(() => {
    const token = ++generation.current;
    setPlan(null);
    setError("");
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
  }, [instrumentId]);
  const pendingIds = (plan?.documents || [])
    .filter((doc) => doc.gaps?.length && !doc.saved)
    .map((doc) => doc.id)
    .join();
  useEffect(() => {
    setBatch(null);
    if (!open || !pendingIds.includes(",")) return;
    let live = true;
    Promise.all(
      pendingIds
        .split(",")
        .map((id) => api.financialRecovery(instrumentId, id)),
    )
      .then((previews) => live && setBatch(previews))
      .catch(() => live && setBatch(null));
    return () => {
      live = false;
    };
  }, [open, instrumentId, pendingIds, revision]);
  async function run() {
    const token = generation.current;
    setBusy("Reading the saved statement with AI…");
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
  async function runAll(runnable) {
    const token = generation.current;
    setError("");
    let done = 0;
    try {
      for (const preview of runnable) {
        setBusy(`Reading report ${done + 1} of ${runnable.length} with AI…`);
        await api.generateFinancialRecovery(instrumentId, {
          document_id: preview.document.id,
          plan_id: preview.plan_id,
        });
        if (token !== generation.current) return;
        done += 1;
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
  const gapCounts = {};
  for (const doc of plan?.documents || [])
    for (const label of doc.gaps || [])
      gapCounts[short(label)] = (gapCounts[short(label)] || 0) + 1;
  const gapSummary = describeGaps(gapCounts);
  const reading = plan?.reading;
  const items = reading?.result?.items || [];
  const saved = reading?.accepted || [];
  const unchanged = [...accepted].sort().join() === [...saved].sort().join();
  const runnable = (batch || []).filter(
    (preview) => preview.can_run && preview.candidate_cells > 0,
  );
  const batchCost = runnable.reduce((sum, p) => sum + p.maximum_cost_usd, 0);
  // Reports with nothing to fill are left out, except the one being shown.
  const listed = (plan?.documents || []).filter(
    (doc) => doc.gaps?.length || doc.saved || doc.id === plan.document.id,
  );
  return (
    <details
      className="financial-recovery"
      onToggle={(event) => setOpen(event.currentTarget.open)}
    >
      <summary>
        <span className="financial-recovery-label">
          <span>Fill in missing figures with AI</span>
          {gapSummary && <small>{gapSummary}</small>}
        </span>
      </summary>
      {open && (
        <div className="financial-recovery-body">
          <p>
            Some figures are blank in your charts because the company’s filing
            doesn’t label them in a standard way. AI can read the original
            statement and suggest which lines make up each one. You check every
            suggestion before it is used, and the app does the arithmetic.
          </p>
          {plan && (
            <>
              {runnable.length > 1 && (
                <div className="recovery-run recovery-all">
                  <button
                    className="primary"
                    disabled={Boolean(busy)}
                    onClick={() => runAll(runnable)}
                  >
                    Find all with AI · {runnable.length} reports
                  </button>
                  <span className="muted">
                    Reads each report in turn · at most US$
                    {(Math.ceil(batchCost * 10000) / 10000).toFixed(4)} in total
                    · you still check every suggestion
                  </span>
                </div>
              )}
              <label className="recovery-report">
                <span>{runnable.length > 1 ? "Or one report" : "Report"}</span>
                <Select
                  value={plan.document.id}
                  disabled={Boolean(busy)}
                  onChange={(event) => setDocumentId(event.target.value)}
                >
                  {listed.map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      {doc.form === "10-K" ? "Annual" : "Quarterly"} ·{" "}
                      {day(doc.end)}
                      {doc.saved
                        ? " · AI suggestions saved"
                        : doc.gaps?.length
                          ? ` · missing ${doc.gaps.map(short).join(", ")}`
                          : " · nothing missing"}
                    </option>
                  ))}
                </Select>
              </label>
              {!reading && !plan.missing.length && (
                <p className="muted">{plan.message}</p>
              )}
              {!reading && plan.missing.length > 0 && (
                <div className="recovery-offer">
                  <p>
                    Missing from your charts for this report:{" "}
                    <strong>
                      {plan.missing.map((m) => short(m.label)).join(", ")}
                    </strong>
                  </p>
                  {!plan.can_run && <p role="alert">{plan.message}</p>}
                  {plan.candidate_cells > 0 && (
                    <div className="recovery-run">
                      <button
                        className="primary"
                        disabled={!plan.can_run || Boolean(busy)}
                        onClick={run}
                      >
                        Find {plan.missing.length === 1 ? "it" : "them"} with AI
                      </button>
                      <span className="muted">
                        Sends {plan.candidate_cells} lines from this report to
                        the AI provider · at most US$
                        {(
                          Math.ceil(plan.maximum_cost_usd * 10000) / 10000
                        ).toFixed(4)}
                        {plan.omitted_cells > 0 &&
                          ` · ${plan.omitted_cells} other lines are left out, so it may not find everything`}
                      </span>
                    </div>
                  )}
                </div>
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
                    Check each figure against the report before using it.
                    Matching lines and correct arithmetic don’t prove the
                    meaning is right.
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
                              <span className="recovery-op" aria-hidden="true">
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
                        Untick a figure and save to stop using it. Reopening
                        this costs nothing.
                      </span>
                    </div>
                  )}
                  {items.length === 0 && (
                    <p>
                      The AI couldn’t match these figures to the report’s lines,
                      so they stay blank.
                    </p>
                  )}
                  {reading.result.unresolved.length > 0 && items.length > 0 && (
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
          <p className="muted">
            Nothing runs automatically. Each reading uses your AI allowance.
            Accepted figures fill your research charts; monitoring keeps the
            company’s original reported figures.
          </p>
          {!plan && !error && <p role="status">Checking saved figures…</p>}
          {busy && <p role="status">{busy}</p>}
          {error && (
            <p role="alert">
              {error}{" "}
              <button
                disabled={Boolean(busy)}
                onClick={() => setRevision((n) => n + 1)}
              >
                Try again
              </button>
            </p>
          )}
        </div>
      )}
    </details>
  );
}

// "Borrowing (short- and long-term debt)" → "Borrowing" for compact labels.
function short(label) {
  return String(label || "").replace(/\s*\([^)]*\)\s*$/, "");
}

// "Borrowing and interest expense missing in 4 reports".
function describeGaps(counts) {
  const gaps = Object.entries(counts);
  if (!gaps.length) return "";
  const reports = (n) => `${n} ${n === 1 ? "report" : "reports"}`;
  const inSentence = (label, i) =>
    i > 0 && /^[A-Z][a-z]/.test(label)
      ? label[0].toLowerCase() + label.slice(1)
      : label;
  const list = (labels) =>
    labels.length < 2
      ? labels.join("")
      : `${labels.slice(0, -1).join(", ")} and ${labels.at(-1)}`;
  if (new Set(gaps.map(([, n]) => n)).size === 1)
    return `${list(gaps.map(([label], i) => inSentence(label, i)))} missing in ${reports(gaps[0][1])}`;
  return `${list(gaps.map(([label, n], i) => `${inSentence(label, i)} (${reports(n)})`))} missing`;
}

// Saved statement rows are "Label | 1,000 |  | 999 |"; show the non-empty cells.
function rowCells(text) {
  return String(text || "")
    .split("|")
    .map((cell) => cell.trim())
    .filter(Boolean);
}
