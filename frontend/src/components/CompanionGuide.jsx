import { useState } from "react";
import Modal from "./Modal";
import { companionPromise, starterQuestions } from "../lib/companion";
import "./Companion.css";

export default function CompanionGuide({
  recorded,
  onExplore,
  onNotebook,
  onReasoning,
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        type="button"
        className="companion-start"
        aria-haspopup="dialog"
        onClick={() => setOpen(true)}
      >
        Start with a question
      </button>
      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="Start with a question"
        className="companion-dialog"
      >
        <div className="companion-dialog-body">
          <p>{companionPromise}</p>
          <p className="muted">
            Choose somewhere to start. These shortcuts open saved research; gaps
            will stay visible.
          </p>
          <div className="companion-questions">
            {starterQuestions
              .filter((item) => !recorded || item.section !== "expectations")
              .map((item) => (
                <button
                  type="button"
                  key={item.id}
                  onClick={() => {
                    setOpen(false);
                    onExplore(item);
                  }}
                >
                  <strong>{item.question}</strong>
                  <span>
                    {recorded && item.section === "business"
                      ? "Overview · Fictional scenario"
                      : item.destination}{" "}
                    <span aria-hidden="true">→</span>
                  </span>
                </button>
              ))}
          </div>
          <div className="companion-next">
            <h3>Then put it in your own words</h3>
            <p>
              Save one reason you’re interested and one uncertainty. A draft or
              a decision not to invest is a useful outcome.
            </p>
            <div className="companion-actions">
              <button
                type="button"
                onClick={() => {
                  setOpen(false);
                  onNotebook();
                }}
              >
                Ask my own question
              </button>
              <button
                type="button"
                onClick={() => {
                  setOpen(false);
                  onReasoning();
                }}
              >
                Save my reasoning
              </button>
            </div>
          </div>
          <p className="fine">
            Fledge does not tell you what to buy. You choose whether to save an
            idea or enable a watch.
          </p>
        </div>
      </Modal>
    </>
  );
}

export function ExplorationPrompt({ question, recorded, onDone, onReasoning }) {
  if (!question) return null;
  return (
    <aside className="companion-prompt" aria-label="Your starting question">
      <div>
        <strong>{question.question}</strong>
        <p>
          {recorded
            ? "Explore the clearly labelled fictional scenario and its saved evidence, then write what you think and what is still unknown."
            : question.prompt}
        </p>
      </div>
      <div className="companion-actions">
        <button type="button" onClick={onReasoning}>
          Save my reasoning
        </button>
        <button type="button" onClick={onDone}>
          Close guide
        </button>
      </div>
    </aside>
  );
}
