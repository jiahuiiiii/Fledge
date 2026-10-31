import { useState } from "react";
import { Button, Card, Modal, Checkbox } from "./ui";
import { useTelegramLink } from "../lib/useTelegramLink";

// Shown once after adding a company: analyse the news now, and optionally watch
// for changes. Nothing starts until the user chooses; both are explicit.
export default function NewCompanySetup({
  open,
  name,
  aiBlocked,
  onSkip,
  onStart,
  onConnectTelegram,
}) {
  const [analyse, setAnalyse] = useState(true);
  const [watch, setWatch] = useState(false);
  const telegram = useTelegramLink();
  const needsTelegram = telegram.configured && !telegram.linked;
  return (
    <Modal
      open={open}
      onClose={onSkip}
      title={`Set up ${name}`}
      className="company-setup"
    >
      <div className="company-setup__body">
        <p>
          Fledge has collected the latest news and discussion. Choose what to do
          next.
        </p>
        <Card variant="inset" as="label" className="company-setup__option">
          <Checkbox
            checked={analyse && !aiBlocked}
            disabled={aiBlocked}
            onChange={(e) => setAnalyse(e.target.checked)}
          />
          <span>
            <strong>Analyse the news now</strong>
            <small>
              Reads the news and posts with AI and labels each one positive,
              negative, mixed or neutral, so the tone shows up. This can take a
              few minutes and uses your AI allowance.
              {aiBlocked && " AI analysis is switched off right now."}
            </small>
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
            onClick={() => onStart({ analyse: analyse && !aiBlocked, watch })}
          >
            {analyse && !aiBlocked ? "Start" : watch ? "Turn on watch" : "Done"}
          </Button>
          {watch && needsTelegram && (
            <Button
              variant="secondary"
              onClick={() =>
                onConnectTelegram({ analyse: analyse && !aiBlocked })
              }
            >
              Connect Telegram first
            </Button>
          )}
          <Button variant="plain" onClick={onSkip}>
            Not now
          </Button>
        </div>
      </div>
    </Modal>
  );
}
