import Select from "./Select";
import { useState } from "react";
import { stamp } from "./MarketResearch";
import SentimentContext from "./SentimentContext";
const labels = {
  supports: "May support your reasoning",
  challenges: "May challenge your reasoning",
  risk: "Risk to investigate",
  answers: "Evidence toward your question",
  possible_link: "Possible connection · not an alert",
  context: "Background context",
  unclear: "Connection unclear",
  unrelated: "No connection identified",
};
function MatchEvidence({ item, sources, onSource }) {
  const source = sources.find((s) => s.id === item.source_id);
  return (
    <article className={`idea-match ${item.relation}`}>
      <div className="row">
        <strong>{labels[item.relation]}</strong>
        <span className="fine">
          {item.channel === "social" ? "Public social post" : "Company news"}
        </span>
      </div>
      {item.reasoning_quote && (
        <blockquote>
          <span className="section-label">YOUR SAVED WORDS</span>
          <br />
          {item.reasoning_quote}
        </blockquote>
      )}
      {item.question_quote && (
        <blockquote>
          <span className="section-label">YOUR SAVED QUESTION</span>
          <br />
          {item.question_quote}
        </blockquote>
      )}
      {item.relation === "answers" && (
        <p className="fine">
          This may answer part of your question. Your research stays open until
          you choose what to do next.
        </p>
      )}
      <h4>{source?.title || "Source unavailable"}</h4>
      {item.connection_basis_label && (
        <p className="fine">{item.connection_basis_label}</p>
      )}
      <p>{item.explanation}</p>
      {item.answer_excerpt && (
        <div className="answer-evidence">
          <p className="fine">{item.answer_kind_label}</p>
          <p>
            <strong>Question addressed:</strong> {item.answer_target}
          </p>
          <blockquote>
            <span className="section-label">
              ANSWER EVIDENCE · ORIGINAL WORDING
            </span>
            <br />
            {item.answer_excerpt}
          </blockquote>
        </div>
      )}
      {item.missing_evidence && (
        <p>
          <strong>What would establish the link:</strong>{" "}
          {item.missing_evidence}
        </p>
      )}
      <details>
        <summary>Inspect the source evidence</summary>
        {item.citations.map((c, i) => (
          <blockquote key={i}>{c.quote}</blockquote>
        ))}
        <SentimentContext value={item.conversation} purpose="connection" />
        <button className="source-link" onClick={() => onSource(source)}>
          Open cited source ↗
        </button>
      </details>
    </article>
  );
}
export default function IdeaAlertChecks({
  checks,
  busy,
  onReview,
  onSource,
  onOpen,
  history = false,
  instrumentId,
  embedded = false,
  readOnly = false,
  hideEmpty = false,
}) {
  const [filter, setFilter] = useState(history ? "all" : "pending");
  const scoped = (checks || []).filter(
    (c) => !instrumentId || c.instrument_id === instrumentId,
  );
  const visible = scoped.filter(
    (c) => embedded || filter === "all" || (c.published && !c.review_action),
  );
  if (hideEmpty && !scoped.length) return null;
  return (
    <section
      className="idea-alert-checks"
      aria-label="Evidence linked to saved reasoning"
    >
      {!embedded && (
        <>
          <div className="market-section-head">
            <div>
              <h2>News checked against your idea</h2>
            </div>
            <label>
              Show{" "}
              <Select
                aria-label="Idea relevance history"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
              >
                <option value="pending">Alerts awaiting review</option>
                <option value="all">All checks and earlier revisions</option>
              </Select>
            </label>
          </div>
          <p className="fine">
            Saved checks of how a source relates to the idea you held at the
            time.
          </p>
        </>
      )}
      {!visible.length && (
        <p className="muted">
          {filter === "pending"
            ? "No idea-related alerts awaiting review. Check current sources from the workspace, or choose saved-idea alerts in your news watch."
            : "No news has been checked against this idea yet."}
        </p>
      )}
      {visible.map((c) => {
        const priority = [
          ...c.items.filter((i) =>
            ["supports", "challenges", "risk", "answers"].includes(i.relation),
          ),
          ...c.items.filter((i) => i.relation === "possible_link"),
          ...c.items.filter(
            (i) =>
              ![
                "supports",
                "challenges",
                "risk",
                "answers",
                "possible_link",
              ].includes(i.relation),
          ),
        ];
        return (
          <article className="idea-alert-card" key={c.id}>
            <div className="row">
              <strong>
                {c.symbol} · reasoning revision {c.revision}
              </strong>
              <time>{stamp(c.created_at)}</time>
            </div>
            <h3>{c.question}</h3>
            {c.earlier_method && (
              <p className="fine">
                Saved with an earlier method. Original interpretation and
                evidence are unchanged; later conversation context was not added
                to this check.
              </p>
            )}
            {c.historical_revision && (
              <p className="warning">
                Your idea has since changed or been archived. This check
                describes the earlier reasoning shown here.
              </p>
            )}
            {!c.published && c.noteworthy_count > 0 && (
              <p className="fine">
                Retained in history without delivery because the watch settings,
                reasoning or source sample changed before completion.
              </p>
            )}
            {c.withheld ? (
              <p className="warning">
                Source access changed. The interpretation and source excerpts
                are withheld.
              </p>
            ) : (
              <>
                <p>
                  {c.noteworthy_count
                    ? `${c.noteworthy_count} potential ${c.noteworthy_count === 1 ? "connection" : "connections"} to review.`
                    : c.purpose === "question"
                      ? "No direct answer identified in this selected sample. Your question remains open."
                      : "No direct support, challenge, answer or specific risk identified in this selected sample. This does not establish that there is no relevant risk."}
                </p>
                {c.possible_link_count > 0 && (
                  <p className="fine">
                    {c.possible_link_count} possible{" "}
                    {c.possible_link_count === 1
                      ? "connection needs"
                      : "connections need"}{" "}
                    more evidence. These did not trigger an alert.
                  </p>
                )}
                <p className="fine">
                  {c.purpose_label} · Source cutoff {stamp(c.cutoff)} ·{" "}
                  {c.selection_summary}{" "}
                  {c.pending_source_count > 0
                    ? `${c.pending_source_count} additional candidate groups were outside this check.`
                    : ""}
                  {c.parent_contexts > 0 &&
                    ` ${c.parent_contexts} saved parent ${c.parent_contexts === 1 ? "message was" : "messages were"} supplied as context, not additional source connections.`}
                </p>
                {priority.slice(0, 2).map((i) => (
                  <MatchEvidence
                    key={i.source_id}
                    item={i}
                    sources={c.sources}
                    onSource={onSource}
                  />
                ))}
                {priority.length > 2 && (
                  <details>
                    <summary>
                      Inspect {priority.length - 2} more source connections
                    </summary>
                    {priority.slice(2).map((i) => (
                      <MatchEvidence
                        key={i.source_id}
                        item={i}
                        sources={c.sources}
                        onSource={onSource}
                      />
                    ))}
                  </details>
                )}
                <details>
                  <summary>Full reasoning at revision {c.revision}</summary>
                  <p>{c.reasoning}</p>
                  <p className="fine">{c.limitation}</p>
                  <p className="fine">
                    Model {c.model} · prompt {c.prompt_version}
                  </p>
                </details>
              </>
            )}
            <div className="sentiment-controls">
              <button onClick={() => onOpen(c.instrument_id, "idea")}>
                Open current idea ↗
              </button>
              <a href={`/api/v1/idea-alerts/${c.id}/export`} download>
                Download this check
              </a>
            </div>
            {c.review_action ? (
              <p className="fine">
                {c.review_action === "reviewed"
                  ? "Reviewed"
                  : "Left unresolved"}{" "}
                · recorded separately from the AI interpretation.
              </p>
            ) : (
              c.published &&
              !readOnly && (
                <div className="sentiment-controls">
                  <button
                    disabled={busy}
                    onClick={() => onReview(c.id, "reviewed")}
                  >
                    Mark idea alert reviewed
                  </button>
                  <button
                    disabled={busy}
                    onClick={() => onReview(c.id, "unresolved")}
                  >
                    Leave idea alert unresolved
                  </button>
                </div>
              )
            )}
          </article>
        );
      })}
    </section>
  );
}
