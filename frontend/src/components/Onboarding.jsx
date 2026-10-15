import { useState } from "react";
import { api } from "../api/client";
import { INVESTOR_TYPES } from "../lib/investorTypes";
import "./Onboarding.css";
import "./AccountGate.css";

// Five questions, asked once per account and retakeable from Account. The
// answers give an investor type and tailor explanations; they never pick,
// rank or recommend investments.
export const QUESTIONS = [
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
    key: "horizon",
    title: "When you buy, how long do you plan to keep it?",
    options: [
      ["short", "Less than a year"],
      ["medium", "One to five years"],
      ["long", "More than five years"],
      ["unsure", "Not sure yet"],
    ],
  },
  {
    key: "trade_frequency",
    title: "How often do you (or would you) buy or sell?",
    options: [
      ["daily", "Most days", "Sometimes several times a day"],
      ["weekly", "Every week or two"],
      ["monthly", "About once a month", "For example, a regular top-up"],
      ["rarely", "A few times a year or less"],
      ["unsure", "I haven't started yet"],
    ],
  },
  {
    key: "drop_reaction",
    title: "A stock you own falls 15% in one week. What do you do first?",
    hint: "There's no right answer. Pick what you would really do.",
    options: [
      ["sell", "Sell before it falls more"],
      ["hold", "Nothing", "I'm in it for the long run"],
      ["add", "Buy more", "If my reason for owning it still holds"],
      ["check", "Read the news, then decide"],
      ["unsure", "I'm not sure"],
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

const INTERESTS = [
  ["technology", "Technology"],
  ["banks", "Banks and finance"],
  ["healthcare", "Healthcare"],
  ["consumer", "Consumer brands"],
  ["energy", "Energy"],
  ["industrials", "Industrials"],
  ["property", "Property"],
  ["communications", "Media and telecoms"],
];

const KEEP = ["experience", "horizon", "trade_frequency", "drop_reaction", "goal"];

function startingAnswers(profile) {
  const answers = { interests: [] };
  if (!profile?.completed) return answers;
  for (const key of KEEP) if (profile[key]) answers[key] = profile[key];
  answers.interests = (profile.interests || []).filter((i) => i !== "unsure");
  return answers;
}

export function InvestorTypeCard({ type }) {
  const info = INVESTOR_TYPES[type];
  if (!info) return null;
  return (
    <div className="investor-type-card">
      <span className="section-label">YOUR INVESTOR TYPE</span>
      <h2>{info.name}</h2>
      <p className="investor-type-short">{info.short}</p>
      <p>{info.about}</p>
      <dl className="investor-type-facts">
        <div>
          <dt>Usually holds for</dt>
          <dd>{info.holds}</dd>
        </div>
        <div>
          <dt>Usually checks</dt>
          <dd>{info.checks}</dd>
        </div>
      </dl>
      <h3>Watch out for</h3>
      <p>{info.watch}</p>
      <h3>How Fledge helps</h3>
      <p>{info.fledge}</p>
    </div>
  );
}

export default function Onboarding({ onDone, onSkip, profile, retake = false }) {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState(() => startingAnswers(profile));
  const [saved, setSaved] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const question = QUESTIONS[step];
  const last = step === QUESTIONS.length - 1;

  function pick(option) {
    setAnswers((current) => ({ ...current, [question.key]: option }));
  }
  function toggleInterest(key) {
    setAnswers((current) => ({
      ...current,
      interests: current.interests.includes(key)
        ? current.interests.filter((i) => i !== key)
        : [...current.interests, key],
    }));
  }

  async function save(body) {
    setBusy(true);
    setError("");
    try {
      return await api.saveProfile(body);
    } catch (failure) {
      setError(failure.message);
      return null;
    } finally {
      setBusy(false);
    }
  }
  async function finish() {
    const result = await save(answers);
    if (result) {
      setSaved(result);
      window.scrollTo(0, 0);
    }
  }
  async function done() {
    const before = (saved.interests || []).filter((i) => i !== "unsure");
    const changed =
      before.length !== answers.interests.length ||
      before.some((i) => !answers.interests.includes(i));
    const result = changed ? await save(answers) : saved;
    if (result) onDone(result);
  }

  if (saved) {
    return (
      <main className="account-page">
        <section className="account-card onboarding">
          <a className="brand" href="/">
            fledge<span>↗</span>
          </a>
          <p className="onboarding-step">
            {retake ? "Quiz retaken" : "All 5 questions done"}
          </p>
          <InvestorTypeCard type={saved.investor_type} />
          <h3>Anything you’re curious about? (optional)</h3>
          <p className="fine">
            Pick industries and Fledge will mention them on your home page.
          </p>
          <div className="onboarding-chips" role="group" aria-label="Interests">
            {INTERESTS.map(([key, label]) => (
              <button
                type="button"
                key={key}
                role="checkbox"
                aria-checked={answers.interests.includes(key)}
                className={answers.interests.includes(key) ? "selected" : ""}
                onClick={() => toggleInterest(key)}
              >
                {label}
              </button>
            ))}
          </div>
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          <div className="onboarding-actions">
            <button
              type="button"
              className="primary"
              disabled={busy}
              onClick={done}
            >
              {busy ? "Saving…" : retake ? "Back to Fledge" : "Start using Fledge"}
            </button>
          </div>
          <p className="fine">
            This describes how you said you invest. It is a starting point,
            not advice, and you can retake the quiz any time from Account.
          </p>
        </section>
      </main>
    );
  }

  const value = answers[question.key];
  return (
    // A sign-up step (full page), not a pop-up over the workspace.
    <main className="account-page">
      <section className="account-card onboarding">
        <a className="brand" href="/">
          fledge<span>↗</span>
        </a>
        <h1>{retake ? "Retake the investor quiz" : "What kind of investor are you?"}</h1>
        <p className="onboarding-intro">
          Answer 5 quick questions to find your investor type. It shapes how
          Fledge explains things.
        </p>
        <div
          className="onboarding-progress"
          role="progressbar"
          aria-valuemin={1}
          aria-valuemax={QUESTIONS.length}
          aria-valuenow={step + 1}
          aria-label={`Question ${step + 1} of ${QUESTIONS.length}`}
        >
          {QUESTIONS.map((q, i) => (
            <span key={q.key} className={i <= step ? "done" : ""} />
          ))}
        </div>
        <p className="onboarding-step">
          Question {step + 1} of {QUESTIONS.length}
        </p>
        <h3>{question.title}</h3>
        {question.hint && <p className="fine">{question.hint}</p>}
        <div
          className="onboarding-options"
          role="radiogroup"
          aria-label={question.title}
        >
          {question.options.map(([key, label, detail]) => (
            <button
              type="button"
              key={key}
              role="radio"
              aria-checked={value === key}
              className={value === key ? "selected" : ""}
              onClick={() => pick(key)}
            >
              <strong>{label}</strong>
              {detail && <span>{detail}</span>}
            </button>
          ))}
        </div>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <div className="onboarding-actions">
          <button type="button" disabled={busy} onClick={onSkip}>
            {retake ? "Cancel" : "Skip for now"}
          </button>
          {step > 0 && (
            <button
              type="button"
              disabled={busy}
              onClick={() => setStep(step - 1)}
            >
              Back
            </button>
          )}
          <button
            type="button"
            className="primary"
            disabled={!value || busy}
            onClick={() => (last ? finish() : setStep(step + 1))}
          >
            {last ? (busy ? "Saving…" : "See my type") : "Next"}
          </button>
        </div>
        <p className="fine">
          Your answers stay private to your account. Fledge never picks stocks
          for you.
        </p>
      </section>
    </main>
  );
}
