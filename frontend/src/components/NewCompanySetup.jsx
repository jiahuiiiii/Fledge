import { useEffect, useState } from "react";
import { Button, Card, Modal, Checkbox } from "./ui";
import { useTelegramLink } from "../lib/useTelegramLink";
import FledgeLoader from "./FledgeLoader";
import "./NewsDiscussion.css";

// Short, true things about Fledge to read while the first collection runs.
export const SETUP_TIPS = [
  "Fledge saves what it collects, so next time this company opens from saved data.",
  "Write down why a company interests you. Fledge can tell you when news backs it up or goes against it.",
  "Tone labels come from AI reading the news. Open a story to check the original.",
  "A news watch re-checks a company about every four hours while the app runs.",
  "The World page lists headlines on rates, trade and energy that may affect your companies.",
  "Use Arrange to move and resize the sections on your home and Summary pages.",
  "Missing figures show as unknown, never as zero.",
];
const TIP_MS = 7000;

function headline(progress, name) {
  if (progress.stage === "opening")
    return [`Opening ${name}…`, "Reading what Fledge already has saved."];
  if (progress.stage === "ready")
    return ["All set!", `Next time ${name} opens from saved data.`];
  return [
    "Gathering sources…",
    "Usually a minute or two. You can keep browsing.",
  ];
}

function StageIcon({ state }) {
  if (state === "done")
    return (
      <svg viewBox="0 0 16 16" aria-hidden="true">
        <path d="M3.5 8.5l3 3 6-7" />
      </svg>
    );
  return <span aria-hidden="true" />;
}

const STATE_TEXT = { done: "Done", working: "In progress", waiting: "Waiting" };

// The game-style loading screen: the bird, three stages under it, then a tip.
export function SetupHero({ progress, name, tipIndex = null }) {
  const [tip, setTip] = useState(
    () => tipIndex ?? Math.floor(Math.random() * SETUP_TIPS.length),
  );
  const ready = progress.stage === "ready";
  useEffect(() => {
    if (tipIndex != null || ready) return;
    const timer = setInterval(
      () => setTip((index) => (index + 1) % SETUP_TIPS.length),
      TIP_MS,
    );
    return () => clearInterval(timer);
  }, [tipIndex, ready]);
  const [title, detail] = headline(progress, name);
  const stages = progress.stages || [];
  return (
    <div className={`company-setup__hero${ready ? " is-ready" : ""}`}>
      <FledgeLoader done={ready} />
      <div className="company-setup__status" role="status">
        <strong>{title}</strong>
        <small>{detail}</small>
      </div>
      {stages.length > 0 && (
        <ol className="company-setup__stages" aria-label="Setup progress">
          {stages.map((stage) => (
            <li key={stage.id} className={`is-${stage.state}`}>
              <StageIcon state={stage.state} />
              <span>{stage.label}</span>
              <small>
                {stage.state === "done"
                  ? STATE_TEXT.done
                  : `${stage.done} of ${stage.total}`}
                <span className="sr-only"> · {STATE_TEXT[stage.state]}</span>
              </small>
            </li>
          ))}
        </ol>
      )}
      {!ready && (
        <p className="company-setup__tip">
          <span>Tip</span>
          <span key={tip} className="company-setup__tip-text">
            {SETUP_TIPS[tip]}
          </span>
        </p>
      )}
    </div>
  );
}

// Shown once after adding a company. The first collection of filings, prices,
// news and discussions runs while it is open, with the fledgling and plain
// progress. Analysing the news and watching are explicit choices; nothing
// starts until the user picks them.
export default function NewCompanySetup({
  open,
  name,
  progress = { stage: "opening", stages: [] },
  ai = { state: "unknown" },
  onSkip,
  onStart,
  onConnectTelegram,
}) {
  const [analyse, setAnalyse] = useState(true);
  const [watch, setWatch] = useState(false);
  const telegram = useTelegramLink();
  // This dialog stays mounted, so its first status can be from before the
  // chat was connected (e.g. in Account, then on the phone). Ask again each
  // time it opens.
  const { refresh: refreshTelegram } = telegram;
  useEffect(() => {
    if (open) refreshTelegram();
  }, [open, refreshTelegram]);
  const needsTelegram =
    telegram.ready && telegram.configured && !telegram.linked;
  const ready = progress.stage === "ready";
  // Only AI switched off rules the choice out. While availability is still
  // being checked, or another analysis is running, it can be chosen now: the
  // analysis waits for the news to be collected and for its turn.
  const aiOff = ai.state === "disabled";
  const analyseNote = aiOff
    ? "AI analysis is switched off in this workspace, so this can’t be chosen. The news still shows, without labels."
    : !ready
      ? "You can choose this now. It starts by itself once the news has been collected."
      : ai.state === "running"
        ? "Another analysis is running; this one starts when it finishes."
        : null;
  return (
    <Modal
      open={open}
      onClose={onSkip}
      title={ready ? `${name} is ready` : `Setting up ${name}`}
      className="company-setup"
    >
      <div className="company-setup__body">
        <SetupHero progress={progress} name={name} />
        <p className="company-setup__lead">
          {ready
            ? "Everything Fledge could find is saved. Choose what to do next."
            : "The first time you add a company, Fledge collects its prices, filings, news and discussions. You can close this; the page fills in as each part arrives."}
        </p>
        <Card variant="inset" as="label" className="company-setup__option">
          <Checkbox
            checked={analyse && !aiOff}
            disabled={aiOff}
            aria-describedby={
              analyseNote ? "company-setup-analyse-note" : undefined
            }
            onChange={(e) => setAnalyse(e.target.checked)}
          />
          <span>
            <strong>
              {ready ? "Analyse the news now" : "Analyse the news"}
            </strong>
            <small>
              Reads the news and posts with AI and labels each one positive,
              negative, mixed or neutral, so the tone shows up. This can take a
              few minutes and uses your AI allowance.
            </small>
            {analyseNote && (
              <small
                id="company-setup-analyse-note"
                className={`company-setup__note${aiOff ? "" : " is-info"}`}
              >
                {analyseNote}
              </small>
            )}
          </span>
        </Card>
        <Card variant="inset" as="label" className="company-setup__option">
          <Checkbox
            checked={watch}
            onChange={(e) => setWatch(e.target.checked)}
          />
          <span>
            <strong>Watch for changes</strong>
            <small>
              Re-checks about every four hours while the app runs and alerts you
              when the tone shifts. Each check can use your AI allowance.
            </small>
            {watch && needsTelegram && (
              <small className="company-setup__note">
                Alerts go to Telegram, which isn’t connected yet. You can
                connect it now, or keep alerts in Updates only.
              </small>
            )}
          </span>
        </Card>
        <div className="company-setup__actions">
          <Button
            variant="primary"
            onClick={() => onStart({ analyse: analyse && !aiOff, watch })}
          >
            {analyse && !aiOff ? "Start" : watch ? "Turn on watch" : "Done"}
          </Button>
          {watch && needsTelegram && (
            <Button
              variant="secondary"
              onClick={() => onConnectTelegram({ analyse: analyse && !aiOff })}
            >
              Connect Telegram first
            </Button>
          )}
          <Button variant="plain" onClick={onSkip}>
            {ready ? "Not now" : "Keep browsing"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
