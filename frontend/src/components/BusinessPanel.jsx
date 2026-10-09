import { useEffect, useId, useRef, useState } from "react";
import { api } from "../api/client";
import { modelAvailability } from "../lib/modelAvailability";
import Modal from "./Modal";
import Select from "./Select";
import EvidenceButton from "./EvidenceButton";

const titles = {
  business: "What the company does",
  revenue_model: "How it makes money",
  customers: "Who pays it",
  drivers: "What drives performance",
  competition: "Where it competes",
  financial_position: "Borrowing and obligations",
  risks: "Risks to investigate",
};
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
  return (
    <section className="business-panel" aria-label="Understand the business">
      <div className="financial-heading">
        <div>
          <span className="section-label">START WITH THE COMPANY</span>
          <h2>Understand the business</h2>
        </div>
        <button
          disabled={
            busy ||
            availability.blocked ||
            !history?.coverage?.selected_passages
          }
          onClick={() => action()}
        >
          {busy ? "Working…" : "Create business brief"}
        </button>
      </div>
      <p>
        A short explanation based on saved original filings. Creating a brief is
        a paid AI action; reading a saved brief uses no AI credits.
      </p>
      {availability.blocked && (
        <p className="financial-note">{availability.message}</p>
      )}
      {error && <p role="alert">{error}</p>}
      <EvidenceButton label="Saved briefs" title="Saved business briefs">
        {readings.length > 0 && (
          <label>
            Saved business briefs
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
      </EvidenceButton>
      {history?.sample_changed && (
        <p className="financial-note">
          The latest saved brief uses a different source selection. Create a
          brief to read the current saved documents.
        </p>
      )}
      {selected?.withheld ? (
        <p>Source access changed. This saved explanation is withheld.</p>
      ) : selected?.result ? (
        <>
          <p className="financial-coverage">
            Saved {stamp(selected.created_at)} · source cutoff{" "}
            {stamp(selected.cutoff)}
          </p>
          {Object.entries(titles).map(([category, title]) => (
            <details
              className="business-topic business-overview-topic"
              key={category}
              open={["business", "revenue_model", "risks"].includes(category)}
            >
              <summary>{title}</summary>
              {selected.result.findings
                .filter((finding) => finding.category === category)
                .map((finding, i) => (
                  <div key={i}>
                    <small>
                      {finding.kind === "interpretation"
                        ? "AI interpretation"
                        : "Company statement"}
                    </small>
                    <small>
                      {[
                        ...new Set(
                          finding.citations.map((citation) => {
                            const source = selected.sources.find(
                              (item) => item.id === citation.source_id,
                            );
                            return source
                              ? `${source.form} · SEC acceptance ${sourceStamp(source.published_at)}`
                              : "";
                          }),
                        ),
                      ]
                        .filter(Boolean)
                        .join("; ")}
                    </small>
                    <p>{finding.text}</p>
                    <button
                      className="source-link"
                      onClick={() => setEvidence(finding)}
                    >
                      Inspect evidence ↗
                    </button>
                  </div>
                ))}
              {!selected.result.findings.some(
                (finding) => finding.category === category,
              ) && (
                <p className="financial-note">
                  Not established by the selected passages.
                </p>
              )}
            </details>
          ))}
          <details className="business-topic">
            <summary>Evidence gaps and limits</summary>
            {selected.result.withheld_findings?.map((item, index) => (
              <p key={index}>
                {titles[item.category]}: {item.reason}
              </p>
            ))}
            {selected.result.gaps.map((gap) => (
              <p key={gap}>{gap}</p>
            ))}
            <p>{selected.result.limitation}</p>
            <p>{selected.coverage.selection}</p>
          </details>
          {selected.result.questions.length > 0 && (
            <section className="business-topic">
              <h3>Questions to investigate</h3>
              {selected.result.questions.map((question) => (
                <button key={question} onClick={() => onDraft(question)}>
                  {question} ↗
                </button>
              ))}
            </section>
          )}
          <a
            href={`/api/v1/companies/${instrumentId}/business/${selected.id}/export`}
          >
            Download saved brief ↗
          </a>
        </>
      ) : (
        <p>
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
