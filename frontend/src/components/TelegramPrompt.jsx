import { useState } from "react";
import { Button, Modal } from "./ui";
import TelegramSettings from "./TelegramSettings";
import { useTelegramLink } from "../lib/useTelegramLink";

// Watches send their alerts to Telegram. When no chat is connected yet, ask to
// connect it first; the alternative keeps alerts in the app only (Updates).
export function TelegramPrompt({
  open,
  onClose,
  onConnect,
  onContinue,
  what = "this watch",
}) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Connect Telegram first"
      className="telegram-prompt"
    >
      <div className="telegram-prompt__body">
        <p>
          Alerts from {what} are sent to Telegram, so you hear about changes
          without opening Fledge. Telegram isn’t connected yet.
        </p>
        <p className="fine">
          Connecting takes about a minute and opens right here. Without it,
          alerts still appear in Updates inside the app.
        </p>
        <div className="telegram-prompt__actions">
          <Button variant="primary" onClick={onConnect}>
            Connect Telegram
          </Button>
          <Button variant="secondary" onClick={onContinue}>
            Turn on without Telegram
          </Button>
          <Button variant="plain" onClick={onClose}>
            Cancel
          </Button>
        </div>
      </div>
    </Modal>
  );
}

// guard(run): run() now when Telegram is connected (or not applicable); otherwise
// ask first. "Connect Telegram" opens the Telegram setup right here (not the
// Account page); once a chat is connected, run() carries on by itself. Closing
// the setup without connecting goes back to the question. connect(run) skips
// the question, for callers that already asked. `prompt` is the modals to
// render once in the caller.
export function useTelegramGuard({ what }) {
  const link = useTelegramLink();
  const [pending, setPending] = useState(null);
  async function guard(run) {
    const status = await link.refresh();
    if (status.configured && !status.linked) setPending({ run, stage: "ask" });
    else run();
  }
  function connect(run) {
    setPending({ run, stage: "connect" });
  }
  const prompt = (
    <>
      <TelegramPrompt
        open={pending?.stage === "ask"}
        what={what}
        onClose={() => setPending(null)}
        onConnect={() => setPending((p) => p && { ...p, stage: "connect" })}
        onContinue={() => {
          const run = pending?.run;
          setPending(null);
          run?.();
        }}
      />
      {pending?.stage === "connect" && (
        <TelegramSettings
          open
          continueLabel="Continue"
          onClose={async (linked) => {
            const status = await link.refresh();
            if (linked || status.linked) {
              const run = pending.run;
              setPending(null);
              run?.();
            } else setPending((p) => p && { ...p, stage: "ask" });
          }}
        />
      )}
    </>
  );
  return { guard, connect, prompt, link };
}
