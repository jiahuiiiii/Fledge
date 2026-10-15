import { useEffect, useState } from "react";
import { ProModeSwitch } from "./DetailModeToggle";
import { api } from "../api/client";
import "./AccountGate.css";

export default function AccountGate({ children }) {
  const [session, setSession] = useState(null);
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [retryAt, setRetryAt] = useState(0);
  const [now, setNow] = useState(Date.now());
  const remaining = Math.max(0, Math.ceil((retryAt - now) / 1000));
  const [error, setError] = useState(() =>
    new URLSearchParams(location.search).has("auth_error")
      ? "That link expired or belongs to another browser. Request a new sign-in email here."
      : "",
  );
  useEffect(() => {
    if (!retryAt) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [retryAt]);
  async function checkSession() {
    setBusy(true);
    setError("");
    try {
      setSession(await api.session());
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    let active = true;
    api
      .session()
      .then((value) => {
        if (active) setSession(value);
      })
      .catch((failure) => {
        if (active) setError(failure.message);
      });
    const expired = () => {
      setSession((current) => ({
        mode: current?.mode === "password" ? "password" : "managed",
        authenticated: false,
      }));
      setMessage("");
      setError(
        "Your session ended. Sign in again to open your saved research.",
      );
    };
    window.addEventListener("thesis:sign-in-required", expired);
    const changed = () => {
      setSession(null);
      setError("");
      api
        .session()
        .then((value) => {
          if (active) setSession(value);
        })
        .catch((failure) => {
          if (active) setError(failure.message);
        });
    };
    const recheck = () => {
      if (document.visibilityState !== "visible") return;
      api
        .session()
        .then((value) => {
          if (active) setSession(value);
        })
        .catch((failure) => {
          if (active) setError(failure.message);
        });
    };
    window.addEventListener("thesis:account-changed", changed);
    window.addEventListener("focus", recheck);
    if (new URLSearchParams(location.search).has("auth_error"))
      history.replaceState(null, "", "/");
    return () => {
      active = false;
      window.removeEventListener("thesis:sign-in-required", expired);
      window.removeEventListener("thesis:account-changed", changed);
      window.removeEventListener("focus", recheck);
    };
  }, []);
  async function send(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const result = await api.login(email);
      setMessage(result.message);
      setNow(Date.now());
      setRetryAt(Date.now() + (result.retry_after || 60) * 1000);
    } catch (failure) {
      setError(failure.message);
      if (failure.retryAfter) {
        setNow(Date.now());
        setRetryAt(Date.now() + failure.retryAfter * 1000);
      }
    } finally {
      setBusy(false);
    }
  }
  async function sendPassword(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      if (creating) await api.register(username, password);
      else await api.passwordLogin(username, password);
      setPassword("");
      setSession(await api.session());
    } catch (failure) {
      setError(failure.message);
      if (failure.retryAfter) {
        setNow(Date.now());
        setRetryAt(Date.now() + failure.retryAfter * 1000);
      }
    } finally {
      setBusy(false);
    }
  }
  async function signOut() {
    setBusy(true);
    setError("");
    try {
      await api.logout();
      setSession((current) => ({
        mode: current?.mode === "password" ? "password" : "managed",
        authenticated: false,
      }));
      setMessage("You are signed out. Your saved research is still here.");
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  }
  if (session?.authenticated)
    return children(
      session,
      session.mode === "managed" || session.mode === "password" ? (
        <details className="account-menu">
          <summary>Account</summary>
          <div>
            <span className="section-label">SIGNED IN AS</span>
            <p className="account-identity">
              {session.username || session.email || "Research account"}
            </p>
            <ProModeSwitch />
            <p>
              Company news and financial data are shared. Your saved questions,
              ideas and monitoring settings are private.
            </p>
            <button
              onClick={signOut}
              disabled={busy}
              className="account-signout"
            >
              Sign out
            </button>
          </div>
        </details>
      ) : null,
    );
  return (
    <main className="account-page">
      <section className="account-card">
        <a className="brand" href="/">
          fledge<span>↗</span>
        </a>
        <h1>{creating ? "Create your Fledge account" : "Sign in to your research"}</h1>
        <p>
          Your questions, ideas and monitoring settings belong to your account.
        </p>
        {!session && !error ? (
          <p role="status">Checking your session…</p>
        ) : session?.mode === "password" ? (
          <form onSubmit={sendPassword}>
            <label htmlFor="account-username">Username</label>
            <input
              id="account-username"
              autoComplete="username"
              required
              minLength={3}
              maxLength={30}
              pattern="[A-Za-z0-9_.\-]{3,30}"
              title="3–30 letters, numbers, dots, dashes or underscores"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
            />
            <label htmlFor="account-password">Password</label>
            <input
              id="account-password"
              type="password"
              autoComplete={creating ? "new-password" : "current-password"}
              required
              minLength={creating ? 8 : 1}
              maxLength={128}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
            <button
              type="submit"
              className="primary"
              disabled={busy || remaining > 0}
            >
              {busy
                ? "Please wait…"
                : remaining > 0
                  ? `Try again in ${remaining}s`
                  : creating
                    ? "Create account"
                    : "Sign in"}
            </button>
            <button
              type="button"
              className="account-switch"
              onClick={() => {
                setCreating(!creating);
                setError("");
              }}
            >
              {creating
                ? "Already have an account? Sign in"
                : "New to Fledge? Create an account"}
            </button>
          </form>
        ) : (
          <form onSubmit={send}>
            <label htmlFor="account-email">Email address</label>
            <input
              id="account-email"
              type="email"
              autoComplete="email"
              required
              maxLength={254}
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
            <button
              type="submit"
              className="primary"
              disabled={busy || !session || remaining > 0}
            >
              {busy
                ? "Sending…"
                : remaining > 0
                  ? `Request another link in ${remaining}s`
                  : "Email me a sign-in link"}
            </button>
          </form>
        )}
        {message && <p role="status">{message}</p>}
        {error && <p role="alert">{error}</p>}
        {!session && error && (
          <button type="button" onClick={checkSession} disabled={busy}>
            Retry connection
          </button>
        )}
        {session?.mode === "password" ? (
          <p className="financial-note">
            Test version: there is no password reset yet, so keep your password
            somewhere safe. Your work stays saved when you sign out.
          </p>
        ) : (
        <p className="financial-note">
          Open the newest email link in this browser. New sign-ins renew
          automatically for up to seven days. Your work stays saved when you
          sign out.
        </p>
        )}
      </section>
    </main>
  );
}
