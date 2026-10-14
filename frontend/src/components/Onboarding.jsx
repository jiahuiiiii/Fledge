import { useState } from "react";
import { api } from "../api/client";
import "./Onboarding.css";
import "./AccountGate.css";

// Asked once per account on first sign-in. Answers tailor explanations and
// defaults; they never pick, rank or recommend investments.
const QUESTIONS = [
  {
    key: "experience",
    title: "Where are you with investing?",
    options: [
      ["new", "Just starting", "I haven't invested yet"],
      ["etf", "ETFs or funds", "I invest through ETFs or funds"],
      ["stocks", "A few stocks", "I own or follow a few individual stocks"],
      ["active", "Active", "I research and trade stocks regularly"],
    ],
  },
  {
    key: "interests",
    multi: true,
    title: "What are you interested in?",
    hint: "Choose any. You can change these later.",
    options: [
      ["technology", "Technology"],
      ["banks", "Banks and finance"],
      ["healthcare", "Healthcare"],
      ["consumer", "Consumer brands"],
      ["energy", "Energy"],
      ["industrials", "Industrials"],
      ["property", "Property"],
      ["communications", "Media and telecoms"],
      ["unsure", "Not sure yet"],
    ],
  },
  {
    key: "horizon",
    title: "How long do you usually plan to hold?",
    options: [
      ["short", "Under a year"],
      ["medium", "One to five years"],
      ["long", "More than five years"],
      ["unsure", "Not sure"],
    ],
  },
  {
    key: "goal",
    title: "What do you want Fledge to help with first?",
    options: [
      ["learn", "Understand a company", "Plain-language explanations"],
      ["check", "Check a stock idea", "Evidence for and against"],
      ["monitor", "Watch what I own", "Alerts when something changes"],
    ],
  },
];

export default function Onboarding({ onDone, onSkip }) {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState({ interests: [] });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const question = QUESTIONS[step];
  const value = answers[question.key];
  const ready = question.multi ? value.length > 0 : !!value;
  const last = step === QUESTIONS.length - 1;

  function pick(option) {
    setAnswers((current) => {
      if (!question.multi) return { ...current, [question.key]: option };
      const list = current.interests.filter((v) => v !== "unsure");
      const next =
        option === "unsure"
          ? ["unsure"]
          : list.includes(option)
            ? list.filter((v) => v !== option)
            : [...list, option];
      return { ...current, interests: next };
    });
  }

  async function finish() {
    setBusy(true);
    setError("");
    try {
      onDone(await api.saveProfile(answers));
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    // A sign-up step (full page), not a pop-up over the workspace.
    <main className="account-page">
      <section className="account-card onboarding">
      <a className="brand" href="/">
        fledge<span>↗</span>
      </a>
      <h1>Welcome to Fledge</h1>
      <p className="onboarding-step">
        Question {step + 1} of {QUESTIONS.length}
      </p>
      <h3>{question.title}</h3>
      {question.hint && <p className="fine">{question.hint}</p>}
      <div
        className="onboarding-options"
        role={question.multi ? "group" : "radiogroup"}
        aria-label={question.title}
      >
        {question.options.map(([key, label, detail]) => {
          const selected = question.multi ? value.includes(key) : value === key;
          return (
            <button
              type="button"
              key={key}
              role={question.multi ? "checkbox" : "radio"}
              aria-checked={selected}
              className={selected ? "selected" : ""}
              onClick={() => pick(key)}
            >
              <strong>{label}</strong>
              {detail && <span>{detail}</span>}
            </button>
          );
        })}
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="onboarding-actions">
        <button type="button" disabled={busy} onClick={onSkip}>
          Skip for now
        </button>
        {step > 0 && (
          <button type="button" disabled={busy} onClick={() => setStep(step - 1)}>
            Back
          </button>
        )}
        <button
          type="button"
          className="primary"
          disabled={!ready || busy}
          onClick={() => (last ? finish() : setStep(step + 1))}
        >
          {last ? (busy ? "Saving…" : "Finish") : "Next"}
        </button>
      </div>
      <p className="fine">
        Your answers shape your home page and how Fledge explains things.
        Fledge never picks stocks for you.
      </p>
      </section>
    </main>
  );
}

