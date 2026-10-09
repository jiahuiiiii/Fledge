import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import Select from "./Select";
import Modal from "./Modal";
import { starterQuestions } from "../lib/companion";

export const questionDefaults = [
  "Can growth hold up without sacrificing margins?",
  "What could weaken the growth story?",
  "Are expectations supported by reported performance?",
];

export default function QuestionSelector({
  instrumentId,
  company,
  question,
  currentQuestion,
  library,
  onSaved,
  disabled = false,
  onBusyChange,
  editor,
  actions,
}) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  async function save(value, adding = false) {
    setBusy(true);
    onBusyChange?.(true);
    setError("");
    setNotice("");
    try {
      const result = await api.saveResearchQuestion(instrumentId, value);
      if (!alive.current) return;
      onSaved(result);
      setOpen(false);
      setDraft("");
      if (adding) setNotice("Question saved.");
    } catch (e) {
      if (alive.current) setError(e.message);
    } finally {
      if (alive.current) {
        setBusy(false);
        onBusyChange?.(false);
      }
    }
  }
  const options = [
    ...new Set(
      [
        question,
        ...starterQuestions.map((item) => item.question),
        ...questionDefaults,
        ...(library?.items || []).map((item) => item.question),
        currentQuestion,
      ].filter(Boolean),
    ),
  ];
  return (
    <>
      <div className="question-strip question-library">
        <div className="question-library-heading">
          <label htmlFor={editor ? "specific-question" : "research-question"}>
            Research question
          </label>
          <div className="question-library-actions">
            {actions}
            <button
              type="button"
              className="text-button add-question"
              disabled={busy || disabled}
              onClick={() => {
                setDraft("");
                setError("");
                setOpen(true);
              }}
            >
              <span aria-hidden="true">＋</span> Add question
            </button>
          </div>
        </div>
        {editor || (
          <Select
            id="research-question"
            value={question}
            disabled={busy || disabled}
            onChange={(e) => save(e.target.value)}
          >
            {options.map((q) => (
              <option key={q}>{q}</option>
            ))}
          </Select>
        )}
        {busy && !open && (
          <p className="fine" role="status">
            Saving selection…
          </p>
        )}
        {error && !open && (
          <p className="warning" role="alert">
            {error}
          </p>
        )}
        {notice && (
          <p className="fine question-saved" role="status">
            {notice}
          </p>
        )}
      </div>
      <Modal
        open={open}
        title="Add research question"
        className="question-dialog"
        initialFocus="#new-research-question"
        onClose={() => {
          if (!busy) setOpen(false);
        }}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            save(draft, true);
          }}
        >
          <p className="question-company">{company}</p>
          <label htmlFor="new-research-question">
            What do you want to find out?
          </label>
          <textarea
            id="new-research-question"
            autoFocus
            rows={3}
            required
            minLength={3}
            maxLength={600}
            value={draft}
            disabled={busy}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="e.g. Can the company grow without relying on one customer?"
          />
          <p className="fine">
            Saved privately for this company. Adding a question does not run AI
            analysis or start monitoring.
          </p>
          {error && (
            <p className="warning" role="alert">
              {error}
            </p>
          )}
          <div className="question-dialog-actions">
            <button
              type="button"
              disabled={busy}
              onClick={() => setOpen(false)}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="primary"
              disabled={busy || draft.trim().length < 3}
            >
              {busy ? "Saving…" : "Add question"}
            </button>
          </div>
        </form>
      </Modal>
    </>
  );
}
