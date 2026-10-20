import { useState } from "react";
import Modal from "./Modal";
import { api } from "../api/client";

// A recovery code is shown once, right after it is made. The server keeps
// only a hash, so nobody (including us) can show it again.
export function RecoveryCodeScreen({ code, reason = "new", onDone }) {
  const [copied, setCopied] = useState(false);
  const [saved, setSaved] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }
  return (
    <main className="account-page">
      <section className="account-card recovery-card">
        <a className="brand" href="/" aria-label="Fledge home">
          fledge<span aria-hidden="true">↗</span>
        </a>
        <h1 className="account-pitch">Save your recovery code</h1>
        <RecoveryCodeBody
          code={code}
          reason={reason}
          copied={copied}
          onCopy={copy}
        />
        <label className="consent-check">
          <input
            type="checkbox"
            checked={saved}
            onChange={(event) => setSaved(event.target.checked)}
          />
          <span>I’ve saved it somewhere safe.</span>
        </label>
        <button
          type="button"
          className="primary account-submit"
          disabled={!saved}
          onClick={onDone}
        >
          Continue
        </button>
      </section>
    </main>
  );
}

function RecoveryCodeBody({ code, reason, copied, onCopy }) {
  return (
    <>
      <p className="account-lede">
        {reason === "reset"
          ? "Your password is changed and your old code no longer works. Here is your new one."
          : "If you forget your password, this code lets you set a new one. It’s shown only once."}
      </p>
      <p className="recovery-code" aria-label="Recovery code">
        <code>{code}</code>
      </p>
      <button type="button" className="recovery-copy" onClick={onCopy}>
        {copied ? "Copied ✓" : "Copy code"}
      </button>
      <p className="recovery-tip">
        Keep it in your password manager or notes app. Anyone with your
        username and this code can change your password.
      </p>
    </>
  );
}

// Signed-out form: username + recovery code + new password.
export function ForgotPasswordForm({ onDone, onBack }) {
  const [username, setUsername] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [retryAt, setRetryAt] = useState(0);
  async function submit(event) {
    event.preventDefault();
    if (!username.trim() || !code.trim()) {
      setError("Enter your username and recovery code.");
      return;
    }
    if (password.length < 8) {
      setError(`Use a new password of at least 8 characters (you have ${password.length}).`);
      document.getElementById("reset-password")?.focus();
      return;
    }
    if (retryAt > Date.now()) return;
    setBusy(true);
    setError("");
    try {
      const result = await api.passwordReset(username.trim(), code.trim(), password);
      setPassword("");
      onDone(result?.recovery_code || "");
    } catch (failure) {
      setError(failure.message);
      if (failure.retryAfter) setRetryAt(Date.now() + failure.retryAfter * 1000);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form onSubmit={submit} noValidate className="account-form">
      <div className="account-field">
        <label htmlFor="reset-username">Username</label>
        <input
          id="reset-username"
          autoComplete="username"
          autoCapitalize="none"
          maxLength={30}
          value={username}
          onChange={(event) => setUsername(event.target.value)}
        />
      </div>
      <div className="account-field">
        <label htmlFor="reset-code">Recovery code</label>
        <input
          id="reset-code"
          autoComplete="one-time-code"
          autoCapitalize="characters"
          spellCheck={false}
          maxLength={40}
          placeholder="XXXX-XXXX-XXXX-XXXX"
          value={code}
          onChange={(event) => setCode(event.target.value)}
        />
        <small>Your most recent recovery code.</small>
      </div>
      <div className="account-field">
        <label htmlFor="reset-password">New password</label>
        <input
          id="reset-password"
          type="password"
          autoComplete="new-password"
          maxLength={128}
          placeholder="At least 8 characters"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
      </div>
      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}
      <button type="submit" className="primary account-submit" disabled={busy}>
        {busy ? "Please wait…" : "Set new password"}
      </button>
      <p className="account-alt">
        Lost your code too? Contact the Fledge team to reset it.
      </p>
      <p className="account-alt">
        <button type="button" onClick={onBack}>
          Back to sign in
        </button>
      </p>
    </form>
  );
}

// Signed-in: change password, or make a new recovery code.
export function AccountSecurityDialog({ open, onClose, hasRecoveryCode, onCodeChanged }) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [code, setCode] = useState("");
  const [copied, setCopied] = useState(false);
  function close() {
    setCurrent("");
    setNext("");
    setError("");
    setNotice("");
    setCode("");
    setCopied(false);
    onClose();
  }
  async function run(kind) {
    setError("");
    setNotice("");
    if (!current) {
      setError("Enter your current password first.");
      document.getElementById("security-current")?.focus();
      return;
    }
    if (kind === "password" && next.length < 8) {
      setError(`Use a new password of at least 8 characters (you have ${next.length}).`);
      document.getElementById("security-new")?.focus();
      return;
    }
    setBusy(kind);
    try {
      if (kind === "password") {
        await api.changePassword(current, next);
        setNext("");
        setNotice("Password changed. Other browsers signed in to this account were signed out.");
      } else {
        const result = await api.newRecoveryCode(current);
        setCode(result.recovery_code);
        setCopied(false);
        onCodeChanged?.();
      }
      setCurrent("");
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy("");
    }
  }
  return (
    <Modal
      open={open}
      onClose={close}
      title="Password and recovery code"
      className="security-dialog"
      initialFocus="#security-current"
    >
      <div className="security-body account-card">
        {code ? (
          <>
            <RecoveryCodeBody
              code={code}
              reason="new"
              copied={copied}
              onCopy={async () => {
                try {
                  await navigator.clipboard.writeText(code);
                  setCopied(true);
                } catch {
                  setCopied(false);
                }
              }}
            />
            <p className="recovery-tip">Your previous code no longer works.</p>
            <button type="button" className="primary account-submit" onClick={close}>
              I’ve saved it
            </button>
          </>
        ) : (
          <form
            className="account-form"
            noValidate
            onSubmit={(event) => {
              event.preventDefault();
              run("password");
            }}
          >
            {!hasRecoveryCode && (
              <p className="security-nudge">
                You don’t have a recovery code yet. Without one, a forgotten
                password can only be reset by the Fledge team.
              </p>
            )}
            <div className="account-field">
              <label htmlFor="security-current">Current password</label>
              <input
                id="security-current"
                type="password"
                autoComplete="current-password"
                maxLength={128}
                value={current}
                onChange={(event) => setCurrent(event.target.value)}
              />
            </div>
            <div className="account-field">
              <label htmlFor="security-new">New password</label>
              <input
                id="security-new"
                type="password"
                autoComplete="new-password"
                maxLength={128}
                placeholder="At least 8 characters"
                value={next}
                onChange={(event) => setNext(event.target.value)}
              />
            </div>
            <button type="submit" className="primary account-submit" disabled={!!busy}>
              {busy === "password" ? "Please wait…" : "Change password"}
            </button>
            <button
              type="button"
              className="security-secondary"
              disabled={!!busy}
              onClick={() => run("recovery")}
            >
              {busy === "recovery"
                ? "Please wait…"
                : hasRecoveryCode
                  ? "Make a new recovery code"
                  : "Create a recovery code"}
            </button>
            <small className="recovery-tip">
              Both need your current password.
            </small>
            {error && (
              <p className="field-error" role="alert">
                {error}
              </p>
            )}
            {notice && <p role="status">{notice}</p>}
          </form>
        )}
      </div>
    </Modal>
  );
}
