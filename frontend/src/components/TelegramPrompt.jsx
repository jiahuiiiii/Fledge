import { useState } from "react";
import { Button, Modal } from "./ui";
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
          Connecting takes about a minute from your Account page. Without it,
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
// ask first. `prompt` is the modal to render once in the caller.
export function useTelegramGuard({ onConnect, what }) {
  const link = useTelegramLink();
  const [pending, setPending] = useState(null);
  async function guard(run) {
    const status = await link.refresh();
    if (status.configured && !status.linked) setPending({ run });
    else run();
  }
  const prompt = (
    <TelegramPrompt
      open={!!pending}
      what={what}
      onClose={() => setPending(null)}
      onConnect={() => {
        setPending(null);
        onConnect?.();
      }}
      onContinue={() => {
        const run = pending?.run;
        setPending(null);
        run?.();
      }}
    />
  );
  return { guard, prompt, link };
}
