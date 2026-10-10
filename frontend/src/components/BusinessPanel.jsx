import { readableNote } from "../lib/readingNotes";
import { useEffect, useId, useRef, useState } from "react";
import { api } from "../api/client";
import { modelAvailability } from "../lib/modelAvailability";
import Modal from "./Modal";
import Select from "./Select";

const titles = {
  business: "What it does",
  revenue_model: "How it makes money",
  customers: "Who its customers are",
  drivers: "What drives results",
  competition: "Who it competes with",
  financial_position: "Cash and obligations",
  risks: "Key risks",
};
const day = (value) =>
  new Date(value).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
const stamp = (value) => new Date(value).toLocaleString("en-GB");
const sourceStamp = (value) =>
  new Date(value).toLocaleString("en-GB", {
    timeZone: "UTC",
    timeZoneName: "short",
  });

export default function BusinessPanel({
  instrumentId,
  visible,
  disclosures,
  modelStatus,
  onRefresh,
  onDraft,
  focusTopic,
}) {
  const [history, setHistory] = useState(null),
    [selected, setSelected] = useState(null);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [evidence, setEvidence] = useState(null);
  const generation = useRef(0);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  useEffect(() => {
    if (!visible) return;
    const token = ++generation.current;
    api
      .businessHistory(instrumentId)
      .then((result) => {
        if (token === generation.current) {
          setHistory(result);
          setSelected(result.current || result.latest);
          setError("");
        }
      })
      .catch((failure) => {
        if (token === generation.current) setError(failure.message);
      });
    return () => {
      generation.current++;
    };
  }, [instrumentId, visible, disclosures?.source_status?.last_attempt_at]);
  async function action(more = false) {
    const token = ++generation.current;
    setBusy(true);
    setError("");
    try {
      if (more) {
        const next = await api.businessHistory(
          instrumentId,
          history.next_cursor,
        );
        if (token === generation.current)
          setHistory((old) => ({
            ...old,
            items: [
              ...old.items,
              ...next.items.filter(
                (item) => !old.items.some((prior) => prior.id === item.id),
              ),
            ],
            next_cursor: next.next_cursor,
          }));
      } else {
        const reading = await api.generateBusiness(instrumentId);
        if (token !== generation.current) return;
        setSelected(reading);
        const next = await api.businessHistory(instrumentId);
        if (token === generation.current) setHistory(next);
      }
    } catch (failure) {
      if (token === generation.current) setError(failure.message);
    } finally {
      if (mounted.current) setBusy(false);
    }
  }
  const availability = modelAvailability(modelStatus, "briefing_enabled");
  const readings = [
    history?.current,
    history?.latest,
    ...(history?.items || []),
    selected,
  ].filter(
    (item, i, all) =>
      item && all.findIndex((other) => other?.id === item.id) === i,
  );
  const forms = [
    ...new Set((selected?.sources || []).map((s) => s.form).filter(Boolean)),
  ];
  const brief = selected?.result && !selected.withheld ? selected : null;
  const omittedFindings = new Map();
  for (const item of brief?.result.withheld_findings || []) {
    const key = JSON.stringify([item.category, item.reason]);
    const prior = omittedFindings.get(key);
    omittedFindings.set(key, { ...item, count: (prior?.count || 0) + 1 });
  }
  const panel = useRef(null);
  const focusedTopic = useRef(null);
  useEffect(() => {
    if (
      !visible ||
      !focusTopic ||
      focusedTopic.current === focusTopic ||
      (!history && !error)
    )
      return;
    const frame = requestAnimationFrame(() => {
      const target =
        panel.current?.querySelector(`[data-topic="${focusTopic.topic}"] h3`) ||
        panel.current?.querySelector("h2");
      target?.focus({ preventScroll: true });
      target?.scrollIntoView({ block: "center", behavior: "instant" });
      focusedTopic.current = focusTopic;
    });
    return () => cancelAnimationFrame(frame);
  }, [visible, focusTopic, history, error]);
  return (
    <section
      ref={panel}
      className="business-panel"
      aria-label="Understand the business"
    >
      <div className="brief-head">
        <div>
          <h2 tabIndex={-1}>Understand the business</h2>
          {brief && (
            <p className="brief-meta">
              AI summary of the company’s own filings
              {forms.length ? ` (${forms.join(", ")})` : ""} · saved{" "}
              {day(brief.created_at)}
            </p>
          )}
        </div>
        <button
          title="Creating a brief is a paid AI action; reading a saved brief uses no AI credits."
          disabled={
            busy ||
            availability.blocked ||
            !history?.coverage?.selected_passages
          }
          onClick={() => action()}
        >
          {busy ? "Working…" : brief ? "Update brief" : "Create business brief"}
        </button>
      </div>
      {!brief && (
        <p className="brief-meta">
          A short explanation built from saved original filings. Creating a
          brief is a paid AI action; reading a saved brief uses no AI credits.
        </p>
      )}
      {availability.blocked && !brief && (
        <p className="financial-note">{availability.message}</p>
      )}
      {error && <p role="alert">{error}</p>}
      {history?.sample_changed && (
        <p className="financial-note">
          The latest saved brief uses a different source selection. Update the
          brief to read the current saved documents.
        </p>
      )}
      {selected?.withheld ? (
        <p>Source access changed. This saved explanation is withheld.</p>
      ) : brief ? (
        <>
          <div className="brief-grid">
            {Object.entries(titles).map(([category, title]) => (
              <BriefTopic
                key={category}
                category={category}
                title={title}
                findings={brief.result.findings.filter(
                  (finding) => finding.category === category,
                )}
                onEvidence={setEvidence}
              />
            ))}
          </div>
          {brief.result.questions.length > 0 && (
            <section
              className="brief-questions"
              aria-label="Questions to research next"
            >
              <h3>Questions to research next</h3>
              <div>
                {brief.result.questions.map((question) => (
                  <button key={question} onClick={() => onDraft(question)}>
                    {question}
                  </button>
                ))}
              </div>
            </section>
          )}
          <details className="secondary-details brief-about">
            <summary>About this summary</summary>
            <p className="fine">
              Saved {stamp(brief.created_at)} · sources saved through{" "}
              {stamp(brief.cutoff)}. Points are the company’s own statements
              unless marked as AI interpretation.
            </p>
            <p className="fine">{readableNote(brief.result.limitation)}</p>
            <p className="fine">{readableNote(brief.coverage.selection)}</p>
            {[...omittedFindings].map(([key, item]) => (
              <p className="fine" key={key}>
                {titles[item.category]} · {item.count}{" "}
                {item.count === 1 ? "finding" : "findings"} not shown.{" "}
                {readableNote(item.reason)}
              </p>
            ))}
            {brief.result.gaps.map((gap) => (
              <p className="fine" key={gap}>
                {gap}
              </p>
            ))}
            {availability.blocked && (
              <p className="fine">{availability.message}</p>
            )}
            {readings.length > 1 && (
              <label className="brief-history">
                Saved briefs
                <Select
                  aria-label="Saved business briefs"
                  value={selected?.id || ""}
                  onChange={(event) => {
                    setEvidence(null);
                    setSelected(
                      readings.find((item) => item.id === event.target.value),
                    );
                  }}
                >
                  {readings.map((item) => (
                    <option key={item.id} value={item.id}>
                      {stamp(item.created_at)}
                    </option>
                  ))}
                </Select>
              </label>
            )}
            {history?.next_cursor && (
              <button disabled={busy} onClick={() => action(true)}>
                Load older briefs
              </button>
            )}
            <a
              href={`/api/v1/companies/${instrumentId}/business/${brief.id}/export`}
            >
              Download saved brief ↗
            </a>
          </details>
        </>
      ) : (
        <p className="brief-meta">
          No business brief is saved yet. Collect original company documents,
          then create one.
        </p>
      )}
      <Modal
        open={Boolean(evidence)}
        onClose={() => setEvidence(null)}
        title="Original evidence"
        className="business-evidence-dialog"
      >
        <div className="business-evidence-body">
          <section className="business-evidence-claim">
            <span className="section-label">Statement in the brief</span>
            <p>{evidence?.text}</p>
            <small>
              {evidence?.kind === "interpretation"
                ? "AI interpretation"
                : "Company statement"}
            </small>
          </section>
          {evidence?.citations.map((citation) => (
            <BusinessCitation
              key={`${citation.source_id}-${citation.passage_id}`}
              citation={citation}
              source={selected?.sources.find(
                (item) => item.id === citation.source_id,
              )}
            />
          ))}
        </div>
      </Modal>
    </section>
  );
}

// One card per topic: the first point is visible, the rest on request.
function BriefTopic({ title, category, findings, onEvidence }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const shown = open ? findings : findings.slice(0, 1);
  return (
    <article className="brief-topic" aria-labelledby={id} data-topic={category}>
      <h3 id={id} tabIndex={-1}>
        {title}
      </h3>
      {findings.length ? (
        <ul>
          {shown.map((finding, i) => (
            <li key={i}>
              {finding.kind === "interpretation" && (
                <span className="brief-tag">AI interpretation</span>
              )}
              <p>{finding.text}</p>
              <button
                className="brief-source"
                onClick={() => onEvidence(finding)}
              >
                View source
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="brief-empty">Not covered by the selected passages.</p>
      )}
      {findings.length > 1 && (
        <button
          className="brief-more"
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
        >
          {open ? "Show less" : `Show ${findings.length - 1} more`}
        </button>
      )}
    </article>
  );
}

// Preview is explicitly the start of the saved quote, never a new AI excerpt.
function BusinessCitation({ citation, source }) {
  const [expanded, setExpanded] = useState(false);
  const id = useId();
  const quote = citation.quote;
  const long = quote.length > 420;
  const prefix = quote.slice(0, 420);
  const boundary = prefix.lastIndexOf(" ");
  const preview = long
    ? prefix.slice(0, boundary > 0 ? boundary : prefix.length)
    : quote;
  return (
    <section className="business-evidence-citation">
      <header className="business-evidence-source">
        <h3>{source?.title || "Source unavailable"}</h3>
        {source && <p>SEC acceptance · {sourceStamp(source.published_at)}</p>}
      </header>
      <p className="business-evidence-caption">
        {long && !expanded
          ? "Beginning of saved passage · preview"
          : "Saved passage · original wording"}
      </p>
      <blockquote id={id}>
        {expanded ? quote : preview}
        {long && !expanded && <span aria-hidden="true">…</span>}
      </blockquote>
      <div className="business-evidence-actions">
        {long && (
          <button
            type="button"
            aria-expanded={expanded}
            aria-controls={id}
            onClick={() => setExpanded((value) => !value)}
          >
            {expanded ? "Show less" : "Read full passage"}
          </button>
        )}
        {source?.url && (
          <a href={source.url} target="_blank" rel="noreferrer">
            Open original filing ↗
          </a>
        )}
      </div>
    </section>
  );
}
