import LoadingSkeleton from "./LoadingSkeleton";
import Select from "./Select";
import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { stamp } from "./MarketResearch";
import SentimentContext from "./SentimentContext";
import { SourceLabel } from "./SourceFilters";
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
  enabled,
  onSource,
}) {
  const [open, setOpen] = useState(false),
    [data, setData] = useState(null),
    [selected, setSelected] = useState(null);
  const [busy, setBusy] = useState(""),
    [error, setError] = useState("");
  const sequence = useRef(0);
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
    try {
      const next = await api.generateThemes(instrumentId, analysisId);
      if (ticket !== sequence.current) return;
      setSelected(next);
      setData((d) => ({
        ...d,
        current: next,
        items: [next, ...(d?.items || []).filter((r) => r.id !== next.id)],
      }));
    } catch (e) {
      if (ticket === sequence.current) setError(e.message);
    } finally {
      if (ticket === sequence.current) setBusy("");
    }
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
  const readings = [data?.current, ...(data?.items || []), selected].filter(
    (r, i, all) => r && all.findIndex((v) => v?.id === r.id) === i,
  );
  const themes = (selected?.result?.themes || []).filter(
    (t) => scope === "all" || t.scope === scope,
  );
  const sources = new Map((selected?.sources || []).map((s) => [s.id, s]));
  function claim(value, index) {
    const source = value.source_id && sources.get(value.source_id);
    return (
      <div className="theme-claim" key={index}>
        {source && (
          <p className="fine theme-claim-source">
            {source.source} · {stamp(source.published_at)}
          </p>
        )}
        <p>{value.text}</p>
        <details>
          <summary>Inspect supporting passages</summary>
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
                  .filter(
                    (c) => c.source_id === id && c.role !== "source_title",
                  )
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
        </details>
      </div>
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
        <section aria-label="Discussion themes">
          <div className="market-section-head">
            <div>
              <span className="section-label">DISCUSSION THEMES</span>
              <h3>{names[scope]}</h3>
            </div>
            <button
              disabled={!!busy || !enabled || !analysisId}
              onClick={generate}
            >
              {busy === "generate"
                ? "Reading saved sources…"
                : "Read themes from this sample"}
            </button>
          </div>
          <p className="fine">
            Optional AI reading · uses your existing budget. Reopening saved
            readings makes no AI call. New readings use two AI steps: a draft
            and an evidence check, both charged to the same budget.
          </p>
          {!enabled && (
            <p className="warning" role="status">
              New AI readings are unavailable right now. You can still inspect
              saved readings.
            </p>
          )}
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
              Saved theme reading{" "}
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
                    {stamp(r.cutoff)} · saved {stamp(r.created_at)}
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
          {!selected && !busy && (
            <p>
              No saved theme reading yet. Generate one after analysing a source
              sample.
            </p>
          )}
          {selected && (
            <>
              <p className="fine">
                Captured {stamp(selected.cutoff)} ·{" "}
                {scope === "all"
                  ? Object.values(selected.coverage.by_scope).reduce(
                      (sum, count) => sum + count,
                      0,
                    )
                  : selected.coverage.by_scope[scope] || 0}{" "}
                eligible {names[scope]} texts · not market consensus.
                {scope === "hackernews" &&
                  selected.result?.context_policy &&
                  ` ${selected.coverage.parent_contexts || 0} saved parent ${selected.coverage.parent_contexts === 1 ? "message" : "messages"} supplied as context, not additional sources.`}
              </p>
              {selected.analysis_id !== analysisId && (
                <p className="warning">
                  Earlier source sample. This reading does not describe the
                  sentiment sample currently displayed.
                </p>
              )}
              {selected.stale && (
                <p className="warning">
                  This source sample was captured more than 24 hours ago.
                </p>
              )}
              {selected.earlier_method && (
                <p className="warning">
                  This saved reading uses an earlier interpretation method.
                </p>
              )}
              {selected.withheld ? (
                <p className="warning">
                  Source access changed. This interpretation and its evidence
                  are withheld.
                </p>
              ) : (
                <>
                  <details className="theme-method">
                    <summary>How this sample was read</summary>
                    {selected.result.evidence_policy && (
                      <p className="fine">
                        Each finding has its own source. Original source titles
                        provide context alongside the selected passages.
                      </p>
                    )}
                    <p className="fine">{selected.result.limitation}</p>
                    {selected.result.evidence_check && (
                      <p className="fine">
                        {selected.result.evidence_check.limitation}
                      </p>
                    )}
                    <p className="fine">
                      Selection follows the saved relevance classification;
                      excluded texts can contain missed themes. Unchanged
                      samples reuse their readings. Opening history makes no
                      source or model request.
                    </p>
                  </details>
                  {!!selected.result.evidence_check?.withheld_themes && (
                    <p className="warning">
                      {selected.result.evidence_check.withheld_themes}{" "}
                      {selected.result.evidence_check.withheld_themes === 1
                        ? "proposed theme was"
                        : "proposed themes were"}{" "}
                      withheld after an automated evidence check across this
                      reading. The original source texts remain available in the
                      source view.
                    </p>
                  )}
                  {!themes.length && (
                    <p>
                      No specific theme was identified for {names[scope]} in
                      this reading. This does not establish an absence of
                      discussion elsewhere.
                    </p>
                  )}
                  {themes.map((t, i) => (
                    <article className="theme-card" key={i}>
                      {scope === "all" && <SourceLabel scope={t.scope} />}
                      <header>
                        <h3>{t.title}</h3>
                        <span className="fine">
                          {t.source_count} selected{" "}
                          {t.source_count === 1 ? "text" : "texts"} · not
                          independent confirmations
                        </span>
                      </header>
                      {view(t.reading, "What these sources say")}
                      {t.differing_view ? (
                        view(t.differing_view, "A differing view on this issue")
                      ) : (
                        <p className="fine">
                          No specific differing view identified within this
                          supplied sample.
                        </p>
                      )}
                      <p className="theme-unknown">
                        <strong>Still unknown:</strong> {t.unknown}
                      </p>
                    </article>
                  ))}
                  {!!selected.result.gaps.length && (
                    <details>
                      <summary>Limits of the combined reading</summary>
                      <ul>
                        {selected.result.gaps.map((g, i) => (
                          <li key={i}>{g}</li>
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
    </details>
  );
}
