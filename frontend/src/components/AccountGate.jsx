import { useEffect, useState } from "react";
import { ProModeSwitch } from "./DetailModeToggle";
import { api } from "../api/client";
import { useProfile } from "../lib/profile";
import { typeName } from "../lib/investorTypes";
import { TERMS_VERSION } from "../lib/terms";
import {
  AccountSecurityDialog,
  ForgotPasswordForm,
  RecoveryCodeScreen,
} from "./AccountSecurity";
import "./AccountGate.css";

function InvestorTypeLine() {
  const { profile } = useProfile();
  if (!profile) return null;
  const name = profile.completed && typeName(profile.investor_type);
  return (
    <div className="account-type">
      {name ? (
        <>
          Your investor type
          <strong>{name}</strong>
        </>
      ) : (
        "What kind of investor are you? "
      )}
      <button
        type="button"
        onClick={(event) => {
          event.currentTarget.closest("details")?.removeAttribute("open");
          dispatchEvent(new Event("fledge:retake-quiz"));
        }}
      >
        {name
          ? "Retake the quiz"
          : `Find out in ${profile.completed ? 2 : 4} questions`}
      </button>
    </div>
  );
}

// Accounts made before consent existed (or after the terms change) accept
// once before continuing. New sign-ups accept on the form itself.
function TermsGate({ onAccepted, onSignOut }) {
  const [agree, setAgree] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function accept(event) {
    event.preventDefault();
    if (!agree) {
      setError("Tick the box to agree, or sign out below.");
      document.getElementById("account-consent")?.focus();
      return;
    }
    setBusy(true);
    setError("");
    try {
      onAccepted(await api.acceptTerms(TERMS_VERSION));
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="account-page">
      <section className="account-card terms-gate">
        <a className="brand" href="/">
          fledge<span>↗</span>
        </a>
        <h1>Before you continue</h1>
        <p>
          We’ve added Terms of Use and a Privacy Notice. In short:
        </p>
        <ul>
          <li>Fledge is for learning and research. It is not financial advice.</li>
          <li>
            We keep your answers, saved companies and notes only to run your
            account. We don’t sell your data or show ads.
          </li>
          <li>You can ask us to show, correct or delete your data.</li>
        </ul>
        <form onSubmit={accept}>
          <ConsentCheck checked={agree} onChange={setAgree} />
          <button type="submit" className="primary" disabled={busy}>
            {busy ? "Please wait…" : "Agree and continue"}
          </button>
        </form>
        {error && <p role="alert">{error}</p>}
        <button type="button" className="account-switch" onClick={onSignOut}>
          Not now, sign out
        </button>
      </section>
    </main>
  );
}

function ConsentCheck({ checked, onChange, invalid = false }) {
  return (
    <label className="consent-check">
      <input
        id="account-consent"
        type="checkbox"
        aria-invalid={invalid}
        aria-describedby={invalid ? "consent-error" : undefined}
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
      />
      <span>
        I agree to the{" "}
        <a href="/terms" target="_blank" rel="noopener">
          Terms
        </a>{" "}
        and{" "}
        <a href="/privacy" target="_blank" rel="noopener">
          Privacy Notice
        </a>
        .
      </span>
    </label>
  );
}

export default function AccountGate({ children }) {
  const [session, setSession] = useState(null);
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  // First-time visitors (no account on this browser yet) start on Create.
  const [creating, setCreating] = useState(() => {
    try {
      return !localStorage.getItem("fledge:has-account");
    } catch {
      return true;
    }
  });
  const [fieldError, setFieldError] = useState({});
  // A just-made recovery code, shown once before the app opens.
  const [recovery, setRecovery] = useState(null);
  const [forgot, setForgot] = useState(false);
  const [securityOpen, setSecurityOpen] = useState(false);
  const [agree, setAgree] = useState(false);
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
    // Our own messages, shown under each field, instead of browser bubbles.
    const problems = {};
    const name = username.trim();
    if (creating) {
      if (!/^[A-Za-z0-9_.-]{3,30}$/.test(name))
        problems.username = name.includes("@")
          ? "⚠ Use a username, not an email: 3–30 letters or numbers."
          : /\s/.test(name)
            ? "⚠ No spaces, please: 3–30 letters or numbers."
            : "⚠ Use 3–30 letters or numbers (. - _ are fine).";
      if (password.length < 8)
        problems.password = `⚠ At least 8 characters (you have ${password.length}).`;
      if (!agree)
        problems.consent =
          "⚠ Tick the box to agree to the Terms and Privacy Notice.";
    } else {
      if (!name) problems.username = "Enter your username.";
      if (!password) problems.password = "Enter your password.";
    }
    setFieldError(problems);
    if (Object.keys(problems).length) {
      const first = problems.username
        ? "account-username"
        : problems.password
          ? "account-password"
          : "account-consent";
      document.getElementById(first)?.focus();
      return;
    }
    setBusy(true);
    setError("");
    setMessage("");
    try {
      if (creating) {
        const result = await api.register(name, password, TERMS_VERSION);
        if (result?.recovery_code)
          setRecovery({ code: result.recovery_code, reason: "new" });
      } else await api.passwordLogin(name, password);
      try {
        localStorage.setItem("fledge:has-account", "1");
      } catch {
        /* Storage can be unavailable; only the default tab changes. */
      }
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
  async function refreshSession() {
    try {
      setSession(await api.session());
    } catch (failure) {
      setError(failure.message);
    }
  }
  if (session?.authenticated && recovery)
    return (
      <RecoveryCodeScreen
        code={recovery.code}
        reason={recovery.reason}
        onDone={() => setRecovery(null)}
      />
    );
  if (session?.authenticated && session.terms && !session.terms.accepted)
    return (
      <TermsGate
        onAccepted={(terms) => setSession((current) => ({ ...current, terms }))}
        onSignOut={signOut}
      />
    );
  if (session?.authenticated)
    return children(
      session,
      session.mode === "managed" || session.mode === "password" ? (
        <details className="account-menu">
          <summary
            aria-label="Account menu"
            onKeyDown={(event) => {
              if (event.key === "Escape")
                event.currentTarget.parentElement.removeAttribute("open");
            }}
          >
            Account
          </summary>
          <div
            onKeyDown={(event) => {
              if (event.key !== "Escape") return;
              const menu = event.currentTarget.parentElement;
              menu.removeAttribute("open");
              menu.querySelector("summary")?.focus();
            }}
          >
            <span className="section-label">SIGNED IN AS</span>
            <p className="account-identity">
              {session.username || session.email || "Research account"}
            </p>
            <InvestorTypeLine />
            <ProModeSwitch />
            {session.mode === "password" && session.username && (
              <div className="account-security">
                {session.has_recovery_code === false && (
                  <p className="security-nudge">
                    Add a recovery code so you can reset a forgotten password.
                  </p>
                )}
                <button
                  type="button"
                  onClick={(event) => {
                    event.currentTarget.closest("details")?.removeAttribute("open");
                    setSecurityOpen(true);
                  }}
                >
                  Password and recovery code
                </button>
                <AccountSecurityDialog
                  open={securityOpen}
                  onClose={() => setSecurityOpen(false)}
                  hasRecoveryCode={!!session.has_recovery_code}
                  onCodeChanged={refreshSession}
                />
              </div>
            )}
            <p>
              News and company data are the same for everyone. Your answers,
              notes and settings are private to you.
            </p>
            <button
              onClick={signOut}
              disabled={busy}
              className="account-signout"
            >
              Sign out
            </button>
            <p className="account-legal">
              <a href="/terms" target="_blank" rel="noopener">Terms</a>
              <a href="/privacy" target="_blank" rel="noopener">Privacy</a>
            </p>
          </div>
        </details>
      ) : null,
    );
  return (
    <main className="account-page">
      <section className="account-card">
        <a className="brand" href="/" aria-label="Fledge home">
          fledge<span aria-hidden="true">↗</span>
        </a>
        <h1 className="account-pitch">
          {forgot
            ? "Reset your password"
            : session?.mode === "password" && !creating
              ? "Welcome back"
              : "Understand the news behind your stocks"}
        </h1>
        <p className="account-lede">
          {forgot
            ? "Use the recovery code you saved when you signed up."
            : session?.mode === "password" && !creating
              ? "Sign in to pick up where you left off."
              : "Plain-English news and what people are saying, for US stocks."}
        </p>
        {!session && !error ? (
          <p role="status">Checking your session…</p>
        ) : session?.mode === "password" && forgot ? (
          <ForgotPasswordForm
            onBack={() => {
              setForgot(false);
              setError("");
            }}
            onDone={async (code) => {
              try {
                localStorage.setItem("fledge:has-account", "1");
              } catch {
                /* Storage can be unavailable. */
              }
              if (code) setRecovery({ code, reason: "reset" });
              setForgot(false);
              setMessage("");
              await refreshSession();
            }}
          />
        ) : session?.mode === "password" ? (
          <form onSubmit={sendPassword} noValidate className="account-form">
            <div className="account-field">
              <label htmlFor="account-username">Username</label>
              <input
                id="account-username"
                autoComplete="username"
                autoCapitalize="none"
                maxLength={30}
                placeholder={creating ? "Letters or numbers, no spaces" : ""}
                aria-describedby={fieldError.username ? "username-error" : undefined}
                aria-invalid={!!fieldError.username}
                value={username}
                onChange={(event) => setUsername(event.target.value)}
              />
              {fieldError.username && (
                <small id="username-error" className="field-error">
                  {fieldError.username}
                </small>
              )}
            </div>
            <div className="account-field">
              <label htmlFor="account-password">Password</label>
              <input
                id="account-password"
                type="password"
                autoComplete={creating ? "new-password" : "current-password"}
                maxLength={128}
                placeholder={creating ? "At least 8 characters" : ""}
                aria-describedby={fieldError.password ? "password-error" : undefined}
                aria-invalid={!!fieldError.password}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
              {fieldError.password && (
                <small id="password-error" className="field-error">
                  {fieldError.password}
                </small>
              )}
              {!creating && (
                <button
                  type="button"
                  className="account-forgot"
                  onClick={() => {
                    setForgot(true);
                    setError("");
                    setFieldError({});
                  }}
                >
                  Forgot password?
                </button>
              )}
            </div>
            {creating && (
              <>
                <ConsentCheck
                  invalid={!!fieldError.consent}
                  checked={agree}
                  onChange={(value) => {
                    setAgree(value);
                    setFieldError((f) => ({ ...f, consent: "" }));
                  }}
                />
                {fieldError.consent && (
                  <p className="field-error" role="alert" id="consent-error">
                    {fieldError.consent}
                  </p>
                )}
              </>
            )}
            <button
              type="submit"
              className="primary account-submit"
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
            <p className="account-alt">
              {creating ? "Already have an account? " : "New to Fledge? "}
              <button
                type="button"
                onClick={() => {
                  setCreating(!creating);
                  setError("");
                  setFieldError({});
                }}
              >
                {creating ? "Sign in" : "Create an account"}
              </button>
            </p>
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
        {session?.mode !== "password" && (
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
