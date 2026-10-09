// Kestrel's connect/disconnect notification flow, adapted for this local app.
import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import Modal from "./Modal";
import LoadingSkeleton from "./LoadingSkeleton";
import Checkbox from "./Checkbox";
import "./TelegramSettings.css";

const labels = {
  queued: "Waiting to send",
  sending: "Sending",
  sent: "Delivered",
  failed: "Not delivered",
  uncertain: "Delivery unconfirmed",
  skipped: "Not forwarded",
  cancelled: "Cancelled",
};
const kinds = {
  company: "Company update",
  idea: "Saved idea",
  condition: "Monitored condition",
  test: "Connection test",
};
const time = (value) =>
  new Date(value).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

function TelegramIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="m3 10 18-7-5 18-5-7-8-4Z" />
      <path d="m11 14 10-11" />
    </svg>
  );
}

export default function TelegramSettings() {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState(null);
  const [link, setLink] = useState(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const mutation = useRef(0);
  const acting = useRef(false);
  useEffect(() => {
    if (!open) return;
    let live = true;
    const read = () => {
      const started = mutation.current;
      if (acting.current) return;
      return api
        .telegram()
        .then((value) => {
          if (live && !acting.current && started === mutation.current)
            setData(value);
        })
        .catch((e) => {
          if (live) setError(e.message);
        });
    };
    read();
    const timer = setInterval(read, 5000);
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, [open]);

  async function act(name, action, message) {
    const previous = data;
    acting.current = true;
    mutation.current += 1;
    setBusy(name);
    setError("");
    setNotice("");
    try {
      const result = await action();
      if (name === "connect") {
        setLink(result);
        setData(await api.telegram());
      } else {
        setData(result);
        if (result.linked || name === "disconnect") setLink(null);
        if (name === "check" && !result.linked)
          setNotice(
            "No connection yet. Tap Start in the Telegram chat, then check again.",
          );
        else if (message) setNotice(message);
      }
    } catch (e) {
      setError(e.message);
      if (name === "delivery") setData(previous);
    } finally {
      acting.current = false;
      setBusy("");
    }
  }

  return (
    <>
      <button
        className="telegram-launch"
        aria-label="Telegram alerts"
        onClick={() => setOpen(true)}
      >
        <TelegramIcon />
        <span>Telegram</span>
      </button>
      <Modal
        open={open}
        onClose={() => !busy && setOpen(false)}
        title="Telegram alerts"
        className="telegram-modal"
      >
        <div className="telegram-settings">
          <div className="telegram-intro">
            <span className="telegram-mark">
              <TelegramIcon />
            </span>
            <div>
              <h3>Keep up with what changes</h3>
              <p>Important research updates, delivered to your private chat.</p>
            </div>
          </div>
          {error && (
            <p className="telegram-error" role="alert">
              {error}
            </p>
          )}
          {notice && (
            <p className="telegram-notice" role="status">
              {notice}
            </p>
          )}
          {!data ? (
            <LoadingSkeleton rows={3} label="Loading Telegram settings…" />
          ) : (
            <>
              {!data.configured && (
                <section className="telegram-setup">
                  <h4>Set up your bot once</h4>
                  <ol>
                    <li>
                      Open{" "}
                      <a
                        href="https://t.me/BotFather"
                        target="_blank"
                        rel="noreferrer"
                      >
                        BotFather
                      </a>{" "}
                      in Telegram and send <code>/newbot</code>.
                    </li>
                    <li>
                      Put its token in <code>TELEGRAM_BOT_TOKEN</code> in your
                      project’s <code>.env</code> file.
                    </li>
                    <li>Come back here and connect your chat.</li>
                  </ol>
                  <p className="muted">
                    Use a dedicated Thesis bot so it can run alongside Kestrel.
                  </p>
                  <button
                    disabled={!!busy}
                    onClick={() => act("reload", api.telegram)}
                  >
                    Check setup
                  </button>
                </section>
              )}
              {data.token_changed && (
                <p className="telegram-error" role="status">
                  The bot token changed or is unavailable. Delivery is stopped.
                  Disconnect this chat, then reconnect after updating .env.
                </p>
              )}
              {data.linked ? (
                <section className="telegram-connection">
                  <div className="telegram-connection-heading">
                    <div>
                      <span className="section-label">YOUR PRIVATE CHAT</span>
                      <h4>{data.chat_label}</h4>
                      <p>@{data.bot_username}</p>
                    </div>
                    <span
                      className={`telegram-state ${data.active ? "on" : ""}`}
                    >
                      {data.active ? "Delivery on" : "Delivery off"}
                    </span>
                  </div>
                  <label className="telegram-enable">
                    <Checkbox
                      checked={data.enabled}
                      disabled={!!busy || (data.token_changed && !data.enabled)}
                      onChange={(e) => {
                        const enabled = e.target.checked;
                        setData((value) => ({ ...value, enabled }));
                        act(
                          "delivery",
                          () => api.telegramDelivery(enabled),
                          enabled
                            ? "Future alerts will be sent to this chat."
                            : "Telegram delivery paused.",
                        );
                      }}
                    />
                    <span>
                      Send future alerts to this chat
                      <small>
                        Old updates stay in Thesis. Your research watches keep
                        their own settings.
                      </small>
                    </span>
                  </label>
                  <div className="telegram-actions">
                    <button
                      disabled={!!busy || data.token_changed}
                      onClick={() =>
                        act(
                          "test",
                          api.telegramTest,
                          "Test queued. Its delivery status will appear below.",
                        )
                      }
                    >
                      {busy === "test" ? "Queuing…" : "Send a test message"}
                    </button>
                    <button
                      className="telegram-disconnect"
                      disabled={!!busy}
                      onClick={() =>
                        act(
                          "disconnect",
                          api.telegramDisconnect,
                          "Chat disconnected. No further messages will be sent.",
                        )
                      }
                    >
                      Disconnect
                    </button>
                  </div>
                </section>
              ) : (
                data.configured && (
                  <section className="telegram-setup">
                    <h4>Connect your private chat</h4>
                    <p>
                      {link
                        ? "Open the link, tap Start in Telegram, then check your connection here."
                        : "Create a connection link, then open it in Telegram. The link expires after ten minutes."}
                    </p>
                    <div
                      className={`telegram-actions telegram-pairing-actions ${link ? "has-link" : ""}`}
                    >
                      {link && (
                        <a
                          className="telegram-open primary"
                          href={link.url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Open Telegram ↗
                        </a>
                      )}
                      <button
                        className={link ? "" : "primary"}
                        disabled={!!busy}
                        onClick={() =>
                          act(
                            link ? "check" : "connect",
                            link ? api.telegramCheck : api.telegramConnect,
                          )
                        }
                      >
                        {busy === "connect"
                          ? "Connecting…"
                          : busy === "check"
                            ? "Checking…"
                            : link
                              ? "Check connection"
                              : "Connect Telegram"}
                      </button>
                      {link && (
                        <button
                          className="telegram-new-link"
                          disabled={!!busy}
                          onClick={() => act("connect", api.telegramConnect)}
                        >
                          Create a new link
                        </button>
                      )}
                    </div>
                  </section>
                )
              )}
              <details className="telegram-includes">
                <summary>What will arrive in Telegram?</summary>
                <ul>
                  <li>
                    New company reporting and changes in sampled news or social
                    sentiment.
                  </li>
                  <li>
                    Published evidence related to your saved question or
                    reasoning.
                  </li>
                  <li>
                    Changes to monitored figures, event evidence or reporting
                    coverage.
                  </li>
                </ul>
                <p>
                  Messages include the ticker, reason, timestamps and available
                  source links. Social sentiment describes the selected sample,
                  not the whole market. Published manual checks can also
                  generate alerts.
                </p>
                <p>
                  Thesis must be running on this Mac. Watches check on their
                  saved schedule; these are research alerts, not live price
                  alarms. After a restart, only alerts from the last 24 hours
                  are forwarded.
                </p>
                <p>
                  Alert text and a short saved-question excerpt are sent to
                  Telegram. Previously delivered messages remain in your chat
                  after pausing or disconnecting.
                </p>
              </details>
              {!!data.deliveries.length && (
                <section className="telegram-history">
                  <h4>Recent deliveries</h4>
                  <ul>
                    {data.deliveries.map((item) => (
                      <li key={item.id}>
                        <div>
                          <strong>
                            {item.symbol ? `${item.symbol} · ` : ""}
                            {kinds[item.kind]}
                          </strong>
                          <time>{time(item.created_at)}</time>
                        </div>
                        <span
                          className={`telegram-state ${item.status === "sent" ? "on" : ""}`}
                        >
                          {labels[item.status]}
                        </span>
                        {item.error && <p>{item.error}</p>}
                        {item.retry_at && item.status === "queued" && (
                          <p>Next attempt after {time(item.retry_at)}.</p>
                        )}
                      </li>
                    ))}
                  </ul>
                </section>
              )}
            </>
          )}
        </div>
      </Modal>
    </>
  );
}
