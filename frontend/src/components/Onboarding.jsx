import { useEffect, useRef, useState } from "react";
import { Button } from "./ui";
import { api } from "../api/client";
import { INVESTOR_TYPES } from "../lib/investorTypes";
import "./Onboarding.css";
import "./AccountGate.css";

// Two short steps, each on one screen:
//  - "start" (first sign-in): where you are + what you want. Then straight in.
//  - "type" (optional, from Home or Account): trading style + reaction to a
//    fall, then the investor-type result.
// Answers tailor wording and the home page; they never pick, rank or
// recommend investments.
export const START_QUESTIONS = [
  {
    key: "experience",
    title: "Where are you with investing?",
    options: [
      ["new", "Haven’t started yet", "I’m learning first"],
      ["etf", "Funds or ETFs", "For example, a robo-adviser"],
      ["stocks", "A few stocks", "I own or follow some companies"],
      ["active", "I trade often", "Stocks or options, most weeks"],
    ],
  },
  {
    key: "goal",
    title: "What do you want from Fledge?",
    options: [
      ["news", "Keep up with news", "What’s happening and why"],
      ["learn", "Understand a company", "Plain-English explanations"],
      ["check", "Check a stock idea", "The case for and against"],
      ["monitor", "Watch what I own", "Alerts when something changes"],
      [
        "explore",
        "Not sure what to look at",
        "Help me find companies to start with",
      ],
    ],
  },
];

export const TYPE_QUESTIONS = [
  {
    key: "trade_frequency",
    title: "Which sounds most like you?",
    options: [
      ["rarely", "I buy and hold for years", "A few trades a year"],
      ["monthly", "I add a little regularly", "For example, every month"],
      ["weekly", "I trade every week or two", "Holding for days or weeks"],
      ["daily", "I trade most days", "In and out quickly"],
      ["unsure", "I haven’t started yet"],
    ],
  },
  {
    key: "drop_reaction",
    title:
      "A stock you own (or would buy) falls 15% in a week. What do you do first?",
    hint: "No right answer. Pick what you would really do.",
    options: [
      ["hold", "Nothing, I’m in it for the long run"],
      ["check", "Read the news, then decide"],
      ["add", "Buy more if my reason still holds"],
      ["sell", "Sell before it falls more"],
      ["unsure", "Not sure, or prefer not to say"],
    ],
  },
];

const label = (questions, key, value) =>
  questions.find((q) => q.key === key)?.options.find(([v]) => v === value)?.[1];

// One radio group: a single Tab stop, arrow keys move and select (WAI-ARIA).
function Choice({ question, value, onPick }) {
  const refs = useRef([]);
  const keys = question.options.map(([key]) => key);
  const current = Math.max(0, keys.indexOf(value));
  function onKeyDown(event, index) {
    const step = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 }[
      event.key
    ];
    if (!step) return;
    event.preventDefault();
    const next = (index + step + keys.length) % keys.length;
    onPick(keys[next]);
    refs.current[next]?.focus();
  }
  const id = `q-${question.key}`;
  return (
    <fieldset
      className="onboarding-question"
      role="radiogroup"
      aria-labelledby={id}
      id={`${id}-group`}
    >
      <legend id={id} tabIndex={-1}>
        {question.title}
      </legend>
      {question.hint && <p className="fine">{question.hint}</p>}
      <div className="onboarding-options">
        {question.options.map(([key, text, detail], index) => {
          const selected = value === key;
          return (
            <button
              type="button"
              key={key}
              ref={(el) => (refs.current[index] = el)}
              role="radio"
              aria-checked={selected}
              tabIndex={index === current ? 0 : -1}
              className={selected ? "selected" : ""}
              onClick={() => onPick(key)}
              onKeyDown={(event) => onKeyDown(event, index)}
            >
              <span className="onboarding-check" aria-hidden="true">
                {selected ? "✓" : ""}
              </span>
              <span className="onboarding-text">
                <strong>{text}</strong>
                {detail && <span>{detail}</span>}
              </span>
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}

export function InvestorTypeCard({ type, answers = {} }) {
  const info = INVESTOR_TYPES[type];
  if (!info) return null;
  const said = [
    label(TYPE_QUESTIONS, "trade_frequency", answers.trade_frequency),
    label(TYPE_QUESTIONS, "drop_reaction", answers.drop_reaction),
  ].filter(Boolean);
  return (
    <div className="investor-type-card">
      <span className="section-label">YOUR INVESTOR TYPE</span>
      <h2>{info.name}</h2>
      <p className="investor-type-short">{info.short}</p>
      <p>{info.about}</p>
      {said.length > 0 && (
        <p className="investor-type-said">
          You said: {said.map((s) => `“${s}”`).join(" and ")}.
        </p>
      )}
      <h3>Watch out for</h3>
      <p>{info.watch}</p>
      <h3>How Fledge helps</h3>
      <p>{info.fledge}</p>
    </div>
  );
}

export default function Onboarding({
  onDone,
  onSkip,
  profile,
  stage = "start",
  onTurnOnPro,
}) {
  // Someone who skipped the first two questions answers all four at once.
  const questions =
    stage !== "type"
      ? START_QUESTIONS
      : profile?.completed
        ? TYPE_QUESTIONS
        : [...START_QUESTIONS, ...TYPE_QUESTIONS];
  const [answers, setAnswers] = useState(() => {
    const start = {};
    if (profile?.completed)
      for (const key of [
        "experience",
        "goal",
        "trade_frequency",
        "drop_reaction",
      ])
        if (profile[key]) start[key] = profile[key];
    return start;
  });
  const [saved, setSaved] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const heading = useRef(null);
  // New screen: move focus to its heading so screen readers announce it.
  useEffect(() => {
    heading.current?.focus();
    window.scrollTo(0, 0);
  }, [saved]);
  const ready = questions.every((q) => answers[q.key]);
  const pick = (key) => (value) =>
    setAnswers((current) => ({ ...current, [key]: value }));

  async function submit(event) {
    event.preventDefault();
    if (!ready) {
      // Take people to the question they missed, not just a message below.
      const missing = questions.find((q) => !answers[q.key]);
      setError(`Pick an answer for “${missing.title}”`);
      const legend = document.getElementById(`q-${missing.key}`);
      legend?.scrollIntoView({ block: "center", behavior: "smooth" });
      legend?.focus({ preventScroll: true });
      return;
    }
    setBusy(true);
    setError("");
    try {
      const body = {
        experience: answers.experience || profile?.experience || "new",
        goal: answers.goal || profile?.goal || "learn",
        interests: (profile?.interests || []).filter((i) => i !== "unsure"),
        trade_frequency: answers.trade_frequency ?? null,
        drop_reaction: answers.drop_reaction ?? null,
      };
      const result = await api.saveProfile(body);
      if (stage === "type") setSaved(result);
      else if (answers.pro && onTurnOnPro) {
        await onTurnOnPro();
        onDone({ ...result, detail_mode: "data" });
      } else onDone(result);
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  }

  if (saved) {
    // Only for people who trade: beginners don't need the extra choice.
    const offerPro =
      (["swing_trader", "active_trader"].includes(saved.investor_type) ||
        saved.experience === "active") &&
      saved.detail_mode !== "data" &&
      onTurnOnPro;
    return (
      <main className="account-page onboarding-page">
        <section className="account-card onboarding">
          <a className="brand" href="/" aria-label="Fledge home">
            fledge<span aria-hidden="true">↗</span>
          </a>
          <h1 ref={heading} tabIndex={-1} className="sr-only">
            Your investor type
          </h1>
          <div className="onboarding-body">
            <InvestorTypeCard type={saved.investor_type} answers={saved} />
            <p className="fine">
              This describes how you said you invest. It is a starting point,
              not advice. You can retake it any time from Account.
            </p>
          </div>
          <div className="onboarding-sticky">
            <Button variant="primary" onClick={() => onDone(saved)}>
              Done
            </Button>
            {offerPro && (
              <button
                type="button"
                onClick={async () => {
                  await onTurnOnPro();
                  onDone({ ...saved, detail_mode: "data" });
                }}
              >
                Done, and turn on Pro tools (financials and charts)
              </button>
            )}
          </div>
        </section>
      </main>
    );
  }

  return (
    // A sign-up step (full page), not a pop-up over the workspace.
    <main className="account-page onboarding-page">
      <form className="account-card onboarding" onSubmit={submit} noValidate>
        <a className="brand" href="/" aria-label="Fledge home">
          fledge<span aria-hidden="true">↗</span>
        </a>
        <h1 ref={heading} tabIndex={-1}>
          {stage === "type"
            ? "What kind of investor are you?"
            : "Two quick questions"}
        </h1>
        <p className="onboarding-intro">
          {stage === "type"
            ? `${questions.length} questions, about ${questions.length * 10} seconds.`
            : "So Fledge explains things at the right level. About 10 seconds."}
        </p>
        {/* Logo, title and buttons stay put; only the questions scroll
            (on screens wider than a phone). */}
        <div className="onboarding-body">
          {questions.map((question) => (
            <Choice
              key={question.key}
              question={question}
              value={answers[question.key]}
              onPick={pick(question.key)}
            />
          ))}
          {stage !== "type" &&
            answers.experience === "active" &&
            onTurnOnPro && (
              <label className="onboarding-pro">
                <input
                  type="checkbox"
                  checked={!!answers.pro}
                  onChange={(event) =>
                    setAnswers((current) => ({
                      ...current,
                      pro: event.target.checked,
                    }))
                  }
                />
                <span>
                  <strong>Turn on Pro tools now</strong>
                  <small>
                    Financials, charts and every research tab. You can switch
                    later in Account.
                  </small>
                </span>
              </label>
            )}
          <p className="fine">
            Your answers stay private to your account. Fledge never picks stocks
            for you.
          </p>
        </div>
        <div className="onboarding-sticky">
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          <Button type="submit" variant="primary" disabled={busy}>
            {busy ? "Saving…" : stage === "type" ? "See my type" : "Continue"}
          </Button>
          <button
            type="button"
            className="onboarding-skip"
            disabled={busy}
            onClick={onSkip}
          >
            {stage === "type" ? "Not now" : "Skip, show me the app"}
          </button>
        </div>
      </form>
    </main>
  );
}
