import { readableNote, readingGap } from "../lib/readingNotes";
import ReadingNotes from "./ReadingNotes";
import LoadingSkeleton from "./LoadingSkeleton";
import Select from "./Select";
import Modal from "./Modal";
import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { stamp } from "./MarketResearch";
import SentimentContext from "./SentimentContext";
import { SourceLabel } from "./SourceFilters";
import "./DiscussionThemes.css";
const names = {
  all: "All sources",
  news: "Company news",
  reddit: "Reddit discussion",
  hackernews: "Hacker News",
  x: "X / Twitter",
};

export default function DiscussionThemes({
  instrumentId,
  analysisId,
  scope,
  unavailableReason,
  onRefresh,
  onSource,
}) {
  const [open, setOpen] = useState(false),
    [data, setData] = useState(null),
    [selected, setSelected] = useState(null);
  const [evidence, setEvidence] = useState(null);
  const [busy, setBusy] = useState(""),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const sequence = useRef(0);
  useEffect(
    () => setEvidence(null),
    [selected, scope, open, instrumentId, analysisId],
  );
  useEffect(() => {
    if (open) load();
    return () => {
      sequence.current += 1;
    };
  }, [open, instrumentId, analysisId]);
  async function load() {
    const ticket = ++sequence.current;
    setBusy("read");
    setError("");
    setNotice("");
    try {
      const next = await api.themeHistory(instrumentId, analysisId);
      if (ticket !== sequence.current) return;
      setData(next);
      setSelected(next.current || next.items[0] || null);
    } catch (e) {
      if (ticket === sequence.current) setError(e.message);
    } finally {
      if (ticket === sequence.current) setBusy("");
    }
  }
  async function generate() {
    const ticket = ++sequence.current;
    setBusy("generate");
    setError("");
    setNotice("");
    let next, failure;
    try {
      next = await api.generateThemes(instrumentId, analysisId);
    } catch (e) {
      failure = e.message;
    }
    if (ticket !== sequence.current) return;
    // Refresh the shared reservation state before showing the outcome and
    // restoring the action. This read never retries generation.
    try {
      await onRefresh?.();
    } catch {
      /* The reading outcome remains visible if the status read fails. */
    }
    if (ticket !== sequence.current) return;
    if (failure) {
      setError(failure);
      try {
        const refreshed = await api.themeHistory(instrumentId, analysisId);
        if (ticket !== sequence.current) return;
        setData(refreshed);
        setSelected(
          (previous) =>
            [refreshed.current, ...refreshed.items].find(
              (reading) => reading && reading.id === previous?.id,
            ) ||
            refreshed.current ||
            refreshed.items[0] ||
            null,
        );
      } catch {
        // Keep the original failure; this read never repeats paid work.
      }
      if (ticket !== sequence.current) return;
    } else {
      setSelected(next);
      setData((d) => ({
        ...d,
        current: next,
        generation: { cached: true, maximum_new_usd: "0" },
        items: [next, ...(d?.items || []).filter((r) => r.id !== next.id)],
      }));
      setNotice("Discussion summary ready below.");
    }
    setBusy("");
  }
  async function more() {
    const ticket = ++sequence.current;
    setBusy("more");
    setError("");
    try {
      const next = await api.themeHistory(
        instrumentId,
        analysisId,
        data.next_cursor,
      );
      if (ticket !== sequence.current) return;
      setData((d) => ({
        ...d,
        items: [
          ...d.items,
          ...next.items.filter((r) => !d.items.some((old) => old.id === r.id)),
        ],
        next_cursor: next.next_cursor,
      }));
    } catch (e) {
      if (ticket === sequence.current) setError(e.message);
    } finally {
      if (ticket === sequence.current) setBusy("");
    }
  }
  const generationBlock = unavailableReason || data?.generation?.blocked_reason;
  const generationPlan = data?.generation;
  const readings = [data?.current, ...(data?.items || []), selected].filter(
    (r, i, all) => r && all.findIndex((v) => v?.id === r.id) === i,
  );
  const themes = (selected?.result?.themes || []).filter(
    (t) => scope === "all" || t.scope === scope,
  );
  const sources = new Map((selected?.sources || []).map((s) => [s.id, s]));
  const titleRecovery = selected?.result?.batching
    ? selected.result.batching.parts.some((p) => p.citation_normalization)
    : !!selected?.result?.citation_normalization;
  const omitted = selected?.result?.evidence_check?.withheld_themes || 0;
  const activeEvidence =
    open && !selected?.withheld && evidence?.readingId === selected?.id
      ? evidence?.value
      : null;
  function claim(value, index) {
    const citedSources = [
      ...new Set(
        value.source_id
          ? [value.source_id]
          : value.citations.map((c) => c.source_id),
      ),
    ]
      .map((id) => sources.get(id))
      .filter(Boolean);
    return (
      <div className="theme-claim" key={index}>
        <div className="theme-claim-sources">
          {citedSources.length ? (
            citedSources.map((source) => (
              <button
                className="theme-claim-source"
                key={source.id}
                aria-haspopup="dialog"
                onClick={() => setEvidence({ readingId: selected.id, value })}
              >
                {source.source} · {stamp(source.published_at)}
              </button>
            ))
          ) : (
            <button
              className="theme-claim-source"
              aria-haspopup="dialog"
              onClick={() => setEvidence({ readingId: selected.id, value })}
            >
              View supporting passages
            </button>
          )}
        </div>
        <p>{value.text}</p>
      </div>
    );
  }
  function passages(value) {
    return (
      <>
        <p className="theme-evidence-finding">{value.text}</p>
        <p className="fine">
          Selected excerpts · open the original source for full context.
        </p>
        {[...new Set(value.citations.map((c) => c.source_id))].map((id) => {
          const source = sources.get(id);
          return (
            <div className="theme-source" key={id}>
              {source && (
                <>
                  <p className="fine">Source title</p>
                  <h4>{source.title}</h4>
                  <p className="fine">
                    {source.source} · published {stamp(source.published_at)}
                  </p>
                </>
              )}
              {value.citations
                .filter((c) => c.source_id === id && c.role !== "source_title")
                .map((c) => (
                  <blockquote key={c.passage_id}>{c.quote}</blockquote>
                ))}
              {source && (
                <button onClick={() => onSource(source)}>
                  Open theme source ↗
                </button>
              )}
            </div>
          );
        })}
        <SentimentContext value={value.conversation} purpose="finding" />
      </>
    );
  }
  function view(value, heading) {
    return (
      <div className="theme-view">
        <h4>{heading}</h4>
        {(value.claims || [value]).map(claim)}
      </div>
    );
  }

  return (
    <details
      className="discussion-themes"
      onToggle={(e) => setOpen(e.currentTarget.open)}
    >
      <summary>What are people discussing?</summary>
      {open && (
        <section aria-label="Discussion themes" aria-busy={!!busy}>
          <div className="market-section-head">
            <div>
              <h3>Discussion summary</h3>
              <p className="theme-intro">
                Topics and differing views in the saved sources.
              </p>
            </div>
            <button
              disabled={!!busy || !!generationBlock || !analysisId}
              onClick={generate}
            >
              {busy === "generate"
                ? "Creating discussion summary…"
                : generationPlan?.saved_drafts && !generationPlan.cached
                  ? "Continue discussion summary"
                  : "Summarise discussions"}
            </button>
          </div>
          {generationPlan?.maximum_new_usd != null && !generationBlock && (
            <p className="fine">
              {generationPlan.cached
                ? "Saved summary · no AI cost to reopen."
                : `${generationPlan.sources} relevant sources · maximum new cost US$${(Math.ceil(Number(generationPlan.maximum_new_usd) * 10000) / 10000).toFixed(4)}.`}
            </p>
          )}
          {!generationPlan?.cached && (
            <p className="fine">
              A new summary uses your AI budget. Reading saved summaries is
              free.
            </p>
          )}
          {!!generationPlan?.saved_drafts &&
            !generationPlan.cached &&
            !generationBlock && (
              <p className="fine">
                {generationPlan.saved_drafts} saved{" "}
                {generationPlan.saved_drafts === 1
                  ? "draft will"
                  : "drafts will"}{" "}
                be reused. Only unfinished steps use budget.
                {!!generationPlan.normalized_title_references &&
                  " The saved draft is ready for its evidence check."}
              </p>
            )}
          {busy === "generate" ? (
            <p className="fine" role="status">
              Creating your summary and checking its evidence. This can take a
              few minutes; the result will appear here.
            </p>
          ) : generationBlock ? (
            <p className="warning" role="status">
              {generationBlock}
            </p>
          ) : null}
          {notice && !busy && <p role="status">{notice}</p>}
          {error && (
            <p className="warning" role="alert">
              {error}{" "}
              <button disabled={!!busy} onClick={load}>
                Reload saved readings
              </button>
            </p>
          )}
          {busy === "read" && (
            <LoadingSkeleton
              variant="panel"
              rows={2}
              label="Loading saved themes…"
            />
          )}
          {!!readings.length && (
            <label className="theme-history">
              Saved summary{" "}
              <Select
                aria-label="Saved theme reading"
                value={selected?.id || ""}
                disabled={!!busy}
                onChange={(e) =>
                  setSelected(readings.find((r) => r.id === e.target.value))
                }
              >
                {readings.map((r) => (
                  <option key={r.id} value={r.id}>
                    Saved {stamp(r.created_at)}
                    {r.analysis_id === analysisId
                      ? " · this sample"
                      : " · earlier sample"}
                  </option>
                ))}
              </Select>
            </label>
          )}
          {data?.next_cursor && (
            <button disabled={!!busy} onClick={more}>
              Load earlier theme readings
            </button>
          )}
          {!selected && !busy && <p>No discussion summary saved yet.</p>}
          {selected && (
            <>
              <p className="fine theme-sample">
                {scope === "all"
                  ? Object.values(selected.coverage.by_scope).reduce(
                      (sum, count) => sum + count,
                      0,
                    )
                  : selected.coverage.by_scope[scope] || 0}{" "}
                relevant sources · {names[scope]} · captured{" "}
                {stamp(selected.cutoff)}
                {scope === "hackernews" &&
                  selected.result?.context_policy &&
                  ` ${selected.coverage.parent_contexts || 0} saved parent ${selected.coverage.parent_contexts === 1 ? "message" : "messages"} supplied as context, not additional sources.`}
              </p>
              {selected.withheld ? (
                <p className="warning">
                  Source access changed. This interpretation and its evidence
                  are withheld.
                </p>
              ) : (
                <>
                  <ReadingNotes
                    className="theme-method"
                    title="About this summary"
                    differentSources={selected.analysis_id !== analysisId}
                    stale={selected.stale}
                    earlierMethod={selected.earlier_method}
                    omitted={omitted}
                  >
                    {selected.result.evidence_policy && (
                      <p className="fine">
                        Each finding has its own source. Original source titles
                        provide context alongside the selected passages.
                      </p>
                    )}
                    <p>{readableNote(selected.result.limitation)}</p>
                    {titleRecovery && (
                      <p className="fine">
                        Some source links were repaired using the original
                        article titles. The findings were unchanged and still
                        went through the evidence check.
                      </p>
                    )}
                    {selected.result.evidence_check && (
                      <p className="fine">
                        {readableNote(
                          selected.result.evidence_check.limitation,
                        )}
                      </p>
                    )}
                    <p className="fine">
                      Only sources previously labelled relevant were included.
                      That selection can miss useful topics. Reading saved
                      summaries does not use your AI budget.
                    </p>
                  </ReadingNotes>
                  {!themes.length && (
                    <p>
                      No specific theme was identified for {names[scope]} in
                      this reading. This does not establish an absence of
                      discussion elsewhere.
                    </p>
                  )}
                  {themes.map((t, i) => (
                    <article className="theme-card" key={i}>
                      <header>
                        <h3>{t.title}</h3>
                        <div className="theme-card-meta">
                          {scope === "all" && <SourceLabel scope={t.scope} />}
                          <span>
                            {t.source_count} cited{" "}
                            {t.source_count === 1 ? "source" : "sources"}
                          </span>
                        </div>
                      </header>
                      {view(t.reading, "What these sources say")}
                      {t.differing_view ? (
                        view(t.differing_view, "A differing view on this issue")
                      ) : (
                        <p className="fine">
                          No differing view found in this sample.
                        </p>
                      )}
                      <p className="theme-unknown">
                        <strong>Still unknown:</strong> {t.unknown}
                      </p>
                    </article>
                  ))}
                  {!!selected.result.gaps.length && (
                    <details>
                      <summary>What this summary may miss</summary>
                      <ul>
                        {selected.result.gaps.map((g, i) => (
                          <li key={i}>
                            {readingGap(g, selected.result.batching)}
                          </li>
                        ))}
                      </ul>
                    </details>
                  )}
                  <a
                    className="small-link"
                    href={`/api/v1/companies/${instrumentId}/discussion-themes/${selected.id}/export`}
                    download
                  >
                    Download this theme reading
                  </a>
                </>
              )}
            </>
          )}
        </section>
      )}
      <Modal
        open={!!activeEvidence}
        onClose={() => setEvidence(null)}
        title="Supporting evidence"
        className="theme-evidence-dialog"
      >
        {activeEvidence && (
          <div className="theme-evidence-body">{passages(activeEvidence)}</div>
        )}
      </Modal>
    </details>
  );
}
