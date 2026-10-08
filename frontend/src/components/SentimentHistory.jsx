import LoadingSkeleton from "./LoadingSkeleton";
import Select from "./Select";
import SentimentLimits from "./SentimentLimits";
import SentimentBasis from "./SentimentBasis";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import { stamp } from "./MarketResearch";
import Modal from "./Modal";

const changes = {
  added: "Newly selected text",
  removed: "No longer selected",
  relabeled: "Same text · labels changed",
  unchanged: "Same text · labels unchanged",
};
const title = (s, index) =>
  `Sample ${index + 1} · ${stamp(s.cutoff)} · saved ${new Date(s.created_at).toLocaleTimeString("en-GB", { timeZone: "UTC", hour12: false })} UTC${s.earlier_method ? " · earlier method" : ""}${s.withheld ? " · unavailable" : ""}`;

export default function SentimentHistory({ instrumentId, latestId }) {
  const [open, setOpen] = useState(false),
    [items, setItems] = useState([]),
    [cursor, setCursor] = useState(null);
  const [before, setBefore] = useState(""),
    [after, setAfter] = useState(""),
    [comparison, setComparison] = useState(null);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [source, setSource] = useState(null);
  useEffect(() => {
    if (!open) return;
    let active = true;
    setBusy(true);
    setItems([]);
    setComparison(null);
    setError("");
    setBefore("");
    setAfter("");
    api
      .sentimentHistory(instrumentId)
      .then((d) => {
        if (!active) return;
        setItems(d.items);
        setCursor(d.next_cursor);
        setAfter(d.items[0]?.id || "");
        setBefore(d.items[1]?.id || "");
      })
      .catch((e) => active && setError(e.message))
      .finally(() => active && setBusy(false));
    return () => {
      active = false;
    };
  }, [open, instrumentId, latestId]);
  useEffect(() => {
    setComparison(null);
    if (!open || !before || !after) return;
    let active = true;
    setError("");
    api
      .sentimentComparison(instrumentId, before, after)
      .then((d) => active && setComparison(d))
      .catch((e) => active && setError(e.message));
    return () => {
      active = false;
    };
  }, [open, instrumentId, before, after]);
  async function more() {
    setBusy(true);
    setError("");
    try {
      const d = await api.sentimentHistory(instrumentId, cursor);
      setItems((p) => [
        ...p,
        ...d.items.filter((i) => !p.some((a) => a.id === i.id)),
      ]);
      setCursor(d.next_cursor);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  function later(id) {
    setAfter(id);
    setBefore(items[items.findIndex((i) => i.id === id) + 1]?.id || "");
  }
  const older = items.slice(items.findIndex((i) => i.id === after) + 1);
  function reading(side, snapshot, label) {
    if (!side)
      return <p className="fine">{label}: not selected in this sample.</p>;
    const item = side.item,
      s = snapshot.sources.find((s) => s.id === side.source_id);
    return (
      <div className="sample-reading">
        <strong>{label}</strong>
        <p className="fine">
          {item.relevance} · {item.sentiment} ·{" "}
          {item.statement.replaceAll("_", " ")}
        </p>
        <SentimentBasis item={item} />
        <details>
          <summary>Evidence for this label</summary>
          {!item.evidence_policy &&
            item.citations.map((c, i) => (
              <blockquote key={i}>{c.quote}</blockquote>
            ))}
          <SentimentContext value={item.conversation} />
        </details>
        <button className="source-link" onClick={() => setSource(s)}>
          Inspect {label.toLowerCase()} source ↗
        </button>
      </div>
    );
  }
  return (
    <>
      <details
        className="sentiment-history"
        open={open}
        onToggle={(e) => setOpen(e.currentTarget.open)}
      >
        <summary>Compare sentiment samples</summary>
        <p className="fine">
          Compare saved news and social samples. These are irregular checks of
          selected texts, not a market sentiment time series. Opening this view
          does not fetch new sources or run AI. Samples are listed newest first.
        </p>
        {error && (
          <p className="warning" role="alert">
            {error}
          </p>
        )}
        {busy && !items.length && (
          <LoadingSkeleton variant="panel" rows={2} label="Loading samples…" />
        )}
        {!busy && !error && items.length < 2 && (
          <p>
            Two saved analyses are needed to compare samples. An unchanged
            cached analysis does not create a new sample.
          </p>
        )}
        {items.length >= 2 && (
          <div className="sample-selectors">
            <label>
              Later sample
              <Select
                aria-label="Later sentiment sample"
                value={after}
                onChange={(e) => later(e.target.value)}
              >
                {items.map((s, index) => (
                  <option key={s.id} value={s.id}>
                    {title(s, index)}
                  </option>
                ))}
              </Select>
            </label>
            <label>
              Earlier sample
              <Select
                aria-label="Earlier sentiment sample"
                value={before}
                onChange={(e) => setBefore(e.target.value)}
              >
                <option value="">Choose an earlier sample</option>
                {older.map((s) => (
                  <option key={s.id} value={s.id}>
                    {title(
                      s,
                      items.findIndex((item) => item.id === s.id),
                    )}
                  </option>
                ))}
              </Select>
            </label>
          </div>
        )}
        {cursor && (
          <button disabled={busy} onClick={more}>
            Load older samples
          </button>
        )}
        {before && after && !comparison && !error && (
          <LoadingSkeleton
            variant="panel"
            rows={2}
            label="Comparing saved samples…"
          />
        )}
        {comparison?.withheld && (
          <p className="warning">
            This comparison is withheld because access to a consumed source
            changed.
          </p>
        )}
        {comparison && !comparison.withheld && (
          <div aria-label="Sentiment sample comparison" role="region">
            {comparison.method_changed && (
              <p className="warning">
                The analysis method changed. Differences may come from a
                different model, prompt or counting rule; do not treat them as a
                sentiment shift.
              </p>
            )}
            {comparison.same_selected_text && (
              <p className="notice">
                The same texts were selected in both samples. Changed labels are
                a reanalysis, not new reporting.
              </p>
            )}
            <p className="fine">
              “Newly selected” means absent from the earlier sample, not newly
              published. Removed text may have aged out or fallen outside the
              selection limit; its claim was not necessarily withdrawn.
            </p>
            {comparison.comparison_context_changed && (
              <p className="fine">
                The additional reports used for news comparison changed.
              </p>
            )}
            {comparison.parent_context_changed && (
              <p className="notice">
                The saved parent context for a shared social comment changed. A
                changed interpretation is not evidence of a new investor
                opinion.
              </p>
            )}
            {comparison.grouping_changed && (
              <p className="fine">
                The news grouping links changed. Group counts can change without
                new labels on the same text.
              </p>
            )}
            {["news", "social"].map((ch) => {
              const delta = comparison.channels[ch],
                old = comparison.before.summary[ch],
                current = comparison.after.summary[ch];
              return (
                <section
                  className="sample-channel"
                  aria-label={`${ch === "news" ? "News" : "Social"} sample changes`}
                  key={ch}
                >
                  <h3>
                    {ch === "news"
                      ? "Company news"
                      : "Social discussion · compare each platform separately"}
                  </h3>
                  <div className="sample-comparison-grid">
                    {[
                      ["Earlier", old, comparison.before],
                      ["Later", current, comparison.after],
                    ].map(([label, sum, snapshot]) => (
                      <div key={label}>
                        <SentimentLimits
                          value={snapshot.coverage?.input_limits}
                        />
                        <strong>
                          {label} · {sum.tone}
                        </strong>
                        {ch === "social" &&
                          snapshot.summary.social_platforms &&
                          Object.entries(snapshot.summary.social_platforms).map(
                            ([platform, value]) => (
                              <p key={platform}>
                                {platform === "hackernews"
                                  ? "Hacker News"
                                  : platform === "x"
                                    ? "X"
                                    : "Reddit"}
                                : {value.tone} · {value.relevant}/
                                {value.selected} relevant
                              </p>
                            ),
                          )}
                        <p className="fine">
                          Cutoff {stamp(snapshot.cutoff)} · saved{" "}
                          {stamp(snapshot.created_at)}
                        </p>
                        <p>
                          {sum.relevant} relevant / {sum.selected} selected ·{" "}
                          {sum.counted_groups ?? sum.relevant} counted groups
                        </p>
                        <p className="fine">
                          Positive {sum.counts.positive} · Negative{" "}
                          {sum.counts.negative} · Mixed {sum.counts.mixed} ·
                          Neutral {sum.counts.neutral} · Unclear{" "}
                          {sum.counts.unclear}
                        </p>
                      </div>
                    ))}
                  </div>
                  <p>
                    {delta.counts.added} newly selected · {delta.counts.removed}{" "}
                    no longer selected · {delta.counts.relabeled} relabeled ·{" "}
                    {delta.counts.unchanged} unchanged
                  </p>
                  {!old.selected || !current.selected ? (
                    <p className="warning">
                      A sample has no eligible texts in this channel. Missing
                      coverage is not neutral sentiment.
                    </p>
                  ) : null}
                  <details>
                    <summary>
                      Inspect compared texts ({delta.items.length})
                    </summary>
                    {delta.items.map((d, i) => {
                      const s = (
                        d.after ? comparison.after : comparison.before
                      ).sources.find(
                        (s) => s.id === (d.after || d.before).source_id,
                      );
                      return (
                        <article key={i} className="sample-change">
                          <strong>{changes[d.change]}</strong>
                          <h4>{s?.title}</h4>
                          <div className="sample-comparison-grid">
                            {reading(d.before, comparison.before, "Earlier")}
                            {reading(d.after, comparison.after, "Later")}
                          </div>
                        </article>
                      );
                    })}
                  </details>
                </section>
              );
            })}
            <details>
              <summary>Recorded analysis methods</summary>
              <p className="fine">
                Earlier:{" "}
                {Object.values(comparison.before_method)
                  .filter(Boolean)
                  .join(" · ")}
              </p>
              <p className="fine">
                Later:{" "}
                {Object.values(comparison.after_method)
                  .filter(Boolean)
                  .join(" · ")}
              </p>
            </details>
          </div>
        )}
      </details>
      <Modal
        open={!!source}
        title="Historical sentiment source"
        onClose={() => setSource(null)}
      >
        {source && (
          <div className="source-modal">
            <span className="demo-tag">
              {source.kind === "social"
                ? source.platform === "hackernews"
                  ? "SOCIAL · HACKER NEWS COMMENT"
                  : source.platform === "x"
                    ? "SOCIAL · X POST"
                    : "SOCIAL · PUBLIC REDDIT POST"
                : "NEWS · PROVIDER SNIPPET"}
            </span>
            <h3>{source.title}</h3>
            <p className="fine">
              {source.source} · published {stamp(source.published_at)} · first
              available here {stamp(source.available_at)}
            </p>
            <blockquote>{source.body}</blockquote>
            <a href={source.url} target="_blank" rel="noopener noreferrer">
              Read original source ↗
            </a>
          </div>
        )}
      </Modal>
    </>
  );
}
import SentimentContext from "./SentimentContext";
