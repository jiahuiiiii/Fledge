import { modelAvailability } from "../lib/modelAvailability";
import Checkbox from "./Checkbox";
import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import Modal from "./Modal";
import SentimentContext from "./SentimentContext";
import QuestionSelector, { questionDefaults } from "./QuestionSelector";
const stamp = (v) =>
  new Date(v).toLocaleString("en-GB", {
    timeZone: "UTC",
    dateStyle: "medium",
    timeStyle: "short",
  }) + " UTC";
const labels = {
  supported: "Answered within this sample",
  partial: "Partial answer",
  insufficient: "Not enough evidence",
};
const channels = {
  news: "News",
  social: "Social opinions",
  filing: "Filing figures",
};

export default function ResearchQuestion({
  instrumentId,
  company,
  question,
  currentQuestion,
  library,
  onSaved,
  onQuestion,
  modelStatus,
  onDone,
  onDraft,
}) {
  const [editing, setEditing] = useState(false),
    [savingQuestion, setSavingQuestion] = useState(false),
    [items, setItems] = useState([]),
    [cursor, setCursor] = useState(null);
  const [selected, setSelected] = useState(null),
    [parent, setParent] = useState(null),
    [social, setSocial] = useState(true);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [source, setSource] = useState(null);
  const questionInput = useRef(null);
  useEffect(() => {
    if (editing) questionInput.current?.focus();
  }, [editing, parent]);
  useEffect(() => {
    let active = true;
    api
      .questionHistory(instrumentId)
      .then((d) => {
        if (active) {
          setItems(d.items);
          setCursor(d.next_cursor);
        }
      })
      .catch((e) => active && setError(e.message));
    return () => {
      active = false;
    };
  }, [instrumentId]);
  async function ask(event) {
    event.preventDefault();
    if (busy || savingQuestion || modelAvailability(modelStatus).blocked)
      return;
    setBusy(true);
    setError("");
    setNotice("");
    const submitted = {
      question: question.trim(),
      include_social: social,
      parent_id: parent?.id || null,
    };
    try {
      const answer = await api.askResearch(instrumentId, submitted);
      setSelected(answer);
      setItems((previous) => [
        answer,
        ...previous.filter((r) => r.id !== answer.id),
      ]);
      setNotice(
        "Answer saved in question history. Its question and source cutoff are shown below.",
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
      onDone();
    }
  }
  async function choose(id) {
    setError("");
    setBusy(true);
    try {
      const a = await api.researchAnswer(id);
      setSelected(a);
      setNotice("Opened the saved answer. No new analysis was requested.");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function older() {
    setBusy(true);
    setError("");
    try {
      const d = await api.questionHistory(instrumentId, cursor);
      setItems((previous) => [
        ...previous,
        ...d.items.filter((a) => !previous.some((p) => p.id === a.id)),
      ]);
      setCursor(d.next_cursor);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  function follow(q = "") {
    setParent({ id: selected.id, question: selected.question });
    onQuestion(q);
    setEditing(true);
    setNotice("Edit the follow-up above, then choose Answer this question.");
  }
  function citations(refs, contexts = []) {
    return refs.map((c, i) => {
      const s = selected.sources.find((s) => s.id === c.source_id);
      return (
        <details className="answer-citation" key={c.source_id + c.passage_id}>
          <summary>
            Evidence {i + 1} · {s?.publisher || "Source"}
          </summary>
          <blockquote>{c.quote}</blockquote>
          {i === refs.findIndex((r) => r.source_id === c.source_id) &&
            contexts
              .filter((context) => context.source_id === c.source_id)
              .map((context) => (
                <SentimentContext
                  key={context.result_id}
                  value={context}
                  purpose="finding"
                />
              ))}
          {s && (
            <button
              type="button"
              className="source-link"
              onClick={() => setSource(s)}
            >
              Inspect this source ↗
            </button>
          )}
        </details>
      );
    });
  }
  const answer = selected?.result;
  const disabled = modelAvailability(modelStatus).blocked;
  return (
    <section
      className="question-research"
      aria-label="Question-focused research"
    >
      <QuestionSelector
        instrumentId={instrumentId}
        company={company}
        question={question}
        currentQuestion={currentQuestion}
        library={library}
        disabled={busy}
        onBusyChange={setSavingQuestion}
        onSaved={(result) => {
          onSaved(result);
          setEditing(false);
          setParent(null);
          setError("");
          setNotice("");
        }}
        actions={
          <button
            type="button"
            className="text-button edit-question"
            disabled={busy || savingQuestion}
            onClick={() => {
              if (editing) {
                onQuestion(
                  library?.selected_question ||
                    currentQuestion ||
                    questionDefaults[0],
                );
                setParent(null);
                setNotice("");
              }
              setEditing(!editing);
            }}
          >
            {editing ? "Cancel edit" : "Edit question"}
          </button>
        }
        editor={
          editing && (
            <textarea
              ref={questionInput}
              id="specific-question"
              form="research-question-form"
              aria-label="Your research question"
              maxLength={600}
              minLength={3}
              required
              disabled={busy || savingQuestion}
              value={question}
              onChange={(e) => onQuestion(e.target.value)}
              rows={2}
            />
          )
        }
      />
      <div id="question-workbench">
        <form id="research-question-form" onSubmit={ask}>
          {parent && (
            <p className="fine">
              Follow-up to: {parent.question}{" "}
              <button
                type="button"
                disabled={busy}
                onClick={() => setParent(null)}
              >
                Start a separate question
              </button>
            </p>
          )}
          <div className="question-controls">
            <label>
              <Checkbox
                checked={social}
                disabled={busy || savingQuestion}
                onChange={(e) => setSocial(e.target.checked)}
              />{" "}
              Include social discussion
            </label>
            <button
              className="primary"
              type="submit"
              disabled={
                busy || savingQuestion || disabled || question.trim().length < 3
              }
            >
              {busy ? "Working…" : "Answer this question"}
            </button>
          </div>
          <p className="fine question-privacy">
            AI analysis of saved sources · Private to your workspace
          </p>
          {disabled && (
            <p className="fine">{modelAvailability(modelStatus).message}</p>
          )}
        </form>
        {error && (
          <p className="warning" role="alert">
            {error}
          </p>
        )}
        {notice && (
          <p className="fine" role="status">
            {notice}
          </p>
        )}
        {!!items.length && (
          <details className="question-history">
            <summary>
              Question history · {items.length}
              {cursor ? "+" : ""} saved
            </summary>
            <ul>
              {items.map((a) => (
                <li key={a.id}>
                  <button
                    disabled={busy}
                    aria-pressed={selected?.id === a.id}
                    onClick={() => choose(a.id)}
                  >
                    {a.question}
                    <small>{stamp(a.created_at)}</small>
                  </button>
                </li>
              ))}
            </ul>
            {cursor && (
              <button disabled={busy} onClick={older}>
                Earlier questions
              </button>
            )}
          </details>
        )}
        {selected && (
          <article
            className="research-answer"
            aria-label="Saved question answer"
          >
            <div className="section-label">
              {selected.withheld
                ? "SOURCE ACCESS CHANGED"
                : labels[answer?.coverage]}{" "}
              · SAVED ANSWER
            </div>
            <h3>{selected.question}</h3>
            {selected.earlier_method && (
              <p className="warning">
                Earlier answer method. Its original evidence and wording are
                preserved; later context has not been added.
              </p>
            )}
            {selected.previous_question && (
              <p className="fine">Follow-up to: {selected.previous_question}</p>
            )}
            <p className="fine">
              Evidence cutoff {stamp(selected.cutoff)}.{" "}
              {selected.stale
                ? "This source sample is over 24 hours old."
                : "This answer uses its saved sample; newer evidence is not added automatically."}
            </p>
            {selected.withheld ? (
              <p className="warning">
                The answer is withheld because access to its sources changed.
              </p>
            ) : (
              <>
                <p className="answer-lead">{answer.answer}</p>
                {citations(answer.answer_citations, answer.answer_contexts)}
                <ul className="answer-points">
                  {answer.evidence.map((p, i) => (
                    <li key={i}>
                      <span className="section-label">
                        AI reading ·{" "}
                        {[
                          ...new Set(
                            p.citations
                              .map(
                                (c) =>
                                  channels[
                                    selected.sources.find(
                                      (s) => s.id === c.source_id,
                                    )?.channel
                                  ],
                              )
                              .filter(Boolean),
                          ),
                        ].join(" + ")}
                      </span>
                      <p>{p.text}</p>
                      {citations(p.citations, p.contexts)}
                    </li>
                  ))}
                </ul>
                {!!answer.unknowns.length && (
                  <div className="answer-gaps">
                    <h4>Still unknown</h4>
                    <ul>
                      {answer.unknowns.map((u, i) => (
                        <li key={i}>{u}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <p className="fine">
                  {selected.coverage.selected_news} of{" "}
                  {selected.coverage.available_news} eligible news snippets ·{" "}
                  {selected.coverage.selected_social} of{" "}
                  {selected.coverage.available_social} eligible social posts ·{" "}
                  {selected.coverage.filing_tables} filing tables. News/posts
                  cover at most 7 days. {selected.coverage.selection}
                </p>
                {selected.coverage.selected_social_platforms && (
                  <p className="fine">
                    Social sample:{" "}
                    {selected.coverage.selected_social_platforms.reddit || 0}{" "}
                    Reddit{" "}
                    {selected.coverage.selected_social_platforms.reddit === 1
                      ? "post"
                      : "posts"}{" "}
                    ·{" "}
                    {selected.coverage.selected_social_platforms.hackernews ||
                      0}{" "}
                    Hacker News{" "}
                    {selected.coverage.selected_social_platforms.hackernews ===
                    1
                      ? "comment"
                      : "comments"}{" "}
                    {selected.coverage.selected_social_platforms.x > 0 && (
                      <>
                        {" "}
                        · {selected.coverage.selected_social_platforms.x} X
                        posts{" "}
                      </>
                    )}
                    · {selected.coverage.parent_contexts || 0} saved{" "}
                    {selected.coverage.parent_contexts === 1
                      ? "parent"
                      : "parents"}{" "}
                    supplied as context, not additional sources.
                  </p>
                )}
                {selected.include_social &&
                  selected.coverage.selected_social === 0 && (
                    <p className="fine">
                      No eligible social posts were available for this answer.
                      This does not establish neutral sentiment.
                    </p>
                  )}
                <details>
                  <summary>Sample sources and limits</summary>
                  <p className="fine">{answer.limitation}</p>
                  {selected.include_social &&
                    selected.social_status.map((feed) => (
                      <p className="fine" key={feed.feed}>
                        {feed.label || `Reddit · r/${feed.feed}`}:{" "}
                        {!feed.enabled
                          ? "not selected"
                          : feed.error
                            ? "last check failed; saved posts may be older"
                            : feed.completed_at
                              ? `last checked ${stamp(feed.completed_at)}`
                              : "not checked"}
                      </p>
                    ))}
                  <ul>
                    {selected.sources.map((s) => (
                      <li key={s.id}>
                        <button
                          className="source-link"
                          onClick={() => setSource(s)}
                        >
                          {s.title} ↗
                        </button>
                        <small>
                          {s.kind} · {stamp(s.published_at)}
                        </small>
                      </li>
                    ))}
                  </ul>
                </details>
                {answer.next_question && (
                  <button
                    className="followup-question"
                    disabled={busy}
                    onClick={() => follow(answer.next_question)}
                  >
                    Explore next: {answer.next_question}
                  </button>
                )}
                <div className="question-actions">
                  <button disabled={busy} onClick={() => follow()}>
                    Write a follow-up
                  </button>
                  <button
                    disabled={busy}
                    onClick={() => onDraft(selected.question)}
                  >
                    Use this question in idea draft
                  </button>
                </div>
              </>
            )}
            <a
              className="source-link"
              href={`/api/v1/research-answers/${selected.id}/export`}
              download
            >
              Download private answer ↗
            </a>
          </article>
        )}
      </div>
      <Modal
        open={!!source}
        title="Question source evidence"
        onClose={() => setSource(null)}
      >
        {source && (
          <div className="source-modal">
            <span className="demo-tag">{source.kind}</span>
            <h3>{source.title}</h3>
            <p>
              {source.publisher} ·{" "}
              {source.timestamp_basis === "feed_updated"
                ? "feed updated"
                : "published"}{" "}
              {stamp(source.published_at)}
            </p>
            {source.timestamp_basis === "feed_updated" && (
              <p className="fine">
                Original publication time and reply-to context are unavailable.
              </p>
            )}
            <p className="fine">Available here {stamp(source.available_at)}</p>
            <blockquote>
              {source.text || "Only a headline was supplied."}
            </blockquote>
            {source.conversation && (
              <details>
                <summary>Saved parent passages supplied to this answer</summary>
                <p className="fine">
                  Separate{" "}
                  {source.conversation.parent_type === "story"
                    ? "story"
                    : "message"}
                  ; not proof that the commenter agrees. Checked{" "}
                  {stamp(source.conversation.checked_at)}.
                </p>
                {source.conversation.passages.map((p) => (
                  <blockquote key={p.id}>{p.quote}</blockquote>
                ))}
                <a
                  href={source.conversation.url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Open saved parent discussion ↗
                </a>
              </details>
            )}
            <a href={source.url} target="_blank" rel="noopener noreferrer">
              Read original source ↗
            </a>
            <p className="fine">
              {source.channel === "filing"
                ? "These are stored code-formatted filing figures, not a verbatim filing excerpt. Each figure retains its actual reporting period."
                : source.channel === "social"
                  ? "An opinion from the selected social sample, not a verified event or market consensus."
                  : "The stored headline and provider snippet may omit article context."}
            </p>
          </div>
        )}
      </Modal>
    </section>
  );
}
