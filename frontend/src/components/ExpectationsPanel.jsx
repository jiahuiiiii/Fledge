import { readableLoad } from "../lib/loading";
import { readableNote } from "../lib/readingNotes";
import ReadingNotes from "./ReadingNotes";
import LoadingSkeleton from "./LoadingSkeleton";
import Select from "./Select";
import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { stamp } from "./MarketResearch";

export default function ExpectationsPanel({
  visible = true,
  initialRead,
  instrumentId,
  enabled,
  onSource,
  onDraft,
  onView,
}) {
  const [data, setData] = useState(initialRead?.data || null),
    [selected, setSelected] = useState(
      initialRead?.data?.current_reading || initialRead?.data?.latest || null,
    );
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(initialRead?.error || "");
  const preloaded = useRef(initialRead);
  useEffect(() => {
    if (!visible) {
      preloaded.current = null;
      return;
    }
    if (preloaded.current) return;
    let active = true;
    readableLoad(api.expectationHistory(instrumentId), data ? 0 : 280)
      .then((d) => {
        if (active) {
          setData(d);
          setError("");
          setSelected(d.current_reading || d.latest);
        }
      })
      .catch((e) => active && setError(e.message));
    return () => {
      active = false;
    };
  }, [instrumentId, visible]);
  async function extract() {
    setBusy(true);
    setError("");
    try {
      const reading = await api.extractExpectations(instrumentId);
      setSelected(reading);
      const history = await api.expectationHistory(instrumentId);
      setData(history);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function more() {
    setBusy(true);
    setError("");
    try {
      const next = await api.expectationHistory(instrumentId, data.next_cursor);
      setData((d) => ({
        ...d,
        items: [
          ...d.items,
          ...next.items.filter((r) => !d.items.some((old) => old.id === r.id)),
        ],
        next_cursor: next.next_cursor,
      }));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  const sources = new Map((selected?.sources || []).map((s) => [s.id, s]));
  const readings = [
    data?.current_reading,
    data?.latest,
    ...(data?.items || []),
    selected,
  ].filter(
    (r, i, all) => r && all.findIndex((other) => other?.id === r.id) === i,
  );
  return (
    <section className="expectations-panel" aria-label="Company expectations">
      <div className="market-section-head">
        <div>
          <span className="section-label">EXPECTATIONS REPORTED IN NEWS</span>
          <h2>What the news says is expected</h2>
        </div>
        <button
          disabled={busy || !enabled || !data?.current_coverage.selected}
          onClick={extract}
        >
          {busy ? "Working…" : "Extract from saved news"}
        </button>
      </div>
      <p>
        Keep reported results, management outlook and individual analyst views
        separate. An expectation is something to investigate, not an outcome
        already achieved.
      </p>
      <p className="fine">
        A new reading uses your AI budget. Reading saved results is free.
      </p>
      {error && (
        <div className="warning" role="alert">
          {error}
        </div>
      )}
      {!data && !error && (
        <LoadingSkeleton
          variant="panel"
          rows={2}
          label="Loading saved expectations…"
        />
      )}
      {data && (
        <>
          <p className="fine">
            Saved news: {data.current_coverage.available_news} items ·{" "}
            {data.current_coverage.company_mentions} mention this company ·{" "}
            {data.current_coverage.selected} selected from the last seven days.
          </p>
          {!!readings.length && (
            <label className="expectation-history">
              Saved reading
              <Select
                aria-label="Saved expectations"
                value={selected?.id || ""}
                disabled={busy}
                onChange={(e) =>
                  setSelected(readings.find((r) => r.id === e.target.value))
                }
              >
                {readings.map((r) => (
                  <option key={r.id} value={r.id}>
                    {stamp(r.cutoff)}
                    {r.id === data.latest?.id ? " · latest sources" : ""}
                  </option>
                ))}
              </Select>
            </label>
          )}
          {data.next_cursor && (
            <button disabled={busy} onClick={more}>
              Load older readings
            </button>
          )}
          {!selected && (
            <div className="empty-history">
              <h3>No saved expectation reading yet</h3>
              <p>
                {data.current_coverage.selected
                  ? "Extract the selected news to identify attributed outlooks and the evidence still missing."
                  : "No complete recent company-news passages are available. Use Refresh research in the company toolbar."}
              </p>
            </div>
          )}
        </>
      )}
      {selected && (
        <>
          <p className="fine">
            Saved {stamp(selected.created_at)} · sources available through{" "}
            {stamp(selected.cutoff)}.
          </p>
          {selected.withheld ? (
            <p className="warning">
              Source access changed. Evidence and interpretation are withheld;
              the saved record remains in history.
            </p>
          ) : (
            <>
              <ReadingNotes
                differentSources={selected.id !== data?.current_reading?.id}
                stale={selected.stale}
                earlierMethod={selected.earlier_method}
              >
                {(selected.stale ||
                  selected.id !== data?.current_reading?.id) && (
                  <p>
                    Use “Extract from saved news” to read the currently selected
                    sources. This saved reading stays in history. A report's age
                    does not tell us whether its forecast was met or changed.
                  </p>
                )}
                <p>{readableNote(selected.result.limitation)}</p>
                <p>{readableNote(data?.current_coverage.selection)}</p>
                <p>
                  Dates below show when a report was published, which may differ
                  from when the quoted statement was made.
                </p>
              </ReadingNotes>
              {[
                ["management_outlook", "Reported management outlook"],
                ["analyst_view", "Attributed analyst views"],
              ].map(([kind, label]) => (
                <div className="expectation-group" key={kind}>
                  <h3>{label}</h3>
                  {!selected.result.items.some((i) => i.category === kind) && (
                    <p className="muted">
                      None identified in these selected passages. This does not
                      establish that no such outlook exists.
                    </p>
                  )}
                  {selected.result.items
                    .filter((i) => i.category === kind)
                    .map((item, n) => {
                      const source = sources.get(item.source_id);
                      return (
                        <article className="expectation-card" key={kind + n}>
                          <div className="row">
                            <span className="section-label">
                              {kind === "management_outlook"
                                ? "MANAGEMENT · AS REPORTED"
                                : "INDIVIDUAL VIEW · NOT CONSENSUS"}
                            </span>
                            <time>{stamp(source.published_at)}</time>
                          </div>
                          <h4>{item.summary}</h4>
                          <dl>
                            <div>
                              <dt>Attributed wording</dt>
                              <dd>{item.attribution_quote}</dd>
                            </div>
                            <div>
                              <dt>Numeric wording</dt>
                              <dd>
                                {item.value_quote ||
                                  "Not stated in the selected passages"}
                              </dd>
                            </div>
                            <div>
                              <dt>Target period</dt>
                              <dd>
                                {item.horizon_quote ||
                                  "Not stated in the selected passages"}
                              </dd>
                            </div>
                            <div>
                              <dt>Reported change</dt>
                              <dd>
                                {item.change_quote ||
                                  "No explicit revision stated"}
                              </dd>
                            </div>
                          </dl>
                          <details>
                            <summary>Inspect expectation evidence</summary>
                            <p className="fine">
                              {source.title} · {source.source} · reported{" "}
                              {stamp(source.published_at)}
                            </p>
                            {item.citations.map((c) => (
                              <blockquote key={c.passage_id}>
                                {c.quote}
                              </blockquote>
                            ))}
                            <button onClick={() => onSource(source)}>
                              Open expectation source ↗
                            </button>
                          </details>
                          <button
                            className="text-button"
                            onClick={() =>
                              onDraft(
                                `What has changed since this expectation was reported? ${item.summary}`,
                              )
                            }
                          >
                            Draft a research question ↗
                          </button>
                        </article>
                      );
                    })}
                </div>
              ))}
              <details className="secondary-details">
                <summary>What this reading may miss</summary>
                <ul>
                  {selected.result.gaps.map((g, n) => (
                    <li key={n}>{g}</li>
                  ))}
                </ul>
                <p>
                  These individual views do not establish an analyst consensus
                  or whether later results beat or missed a forecast.
                </p>
              </details>
            </>
          )}
          <a
            className="source-link"
            href={`/api/v1/companies/${instrumentId}/expectations/${selected.id}/export`}
          >
            Download this expectation reading
          </a>
        </>
      )}
      <div className="expectation-context">
        <h3>Compare different kinds of evidence</h3>
        <p>
          Reported figures describe completed periods. Social posts describe
          selected opinions. Your valuation cases contain your own assumptions.
          Keep their periods and sources separate when comparing them.
        </p>
        <div className="row">
          <button onClick={() => onView("fundamentals")}>
            Open reported performance ↗
          </button>
          <button onClick={() => onView("evidence")}>
            Open news + social sample ↗
          </button>
          <button onClick={() => onView("valuation")}>
            Open my valuation assumptions ↗
          </button>
        </div>
      </div>
    </section>
  );
}
