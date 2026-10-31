import { useEffect, useState } from "react";
import { api } from "../api/client";
import { PRIVACY_CONTACT, TERMS_DATE } from "../lib/terms";
import "./AccountGate.css";
import "./LegalPage.css";

// Terms of Use and Privacy Notice (Singapore PDPA), readable before signing up.
// Plain words on purpose: people should understand what they agree to.
// The contact is set per installation (THESIS_PRIVACY_CONTACT on the
// server); the built-in value is only a fallback.
function Contact() {
  const [email, setEmail] = useState(PRIVACY_CONTACT);
  useEffect(() => {
    let active = true;
    api
      .legal()
      .then((result) => {
        if (active && result?.privacy_contact) setEmail(result.privacy_contact);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);
  return email ? (
    <a href={`mailto:${email}`}>{email}</a>
  ) : (
    "the Fledge team (contact details coming soon)"
  );
}
const contact = <Contact />;

function Terms() {
  return (
    <>
      <h1>Terms of Use</h1>
      <p className="legal-date">Last updated {TERMS_DATE}</p>
      <p>
        These terms explain how you can use Fledge. By creating an account you
        agree to them and to our <a href="/privacy">Privacy Notice</a>.
      </p>
      <h2>1. What Fledge is</h2>
      <p>
        Fledge is a research and learning tool built by students. It helps you
        read company news, world events and what people online are saying, and
        lets you write down your own view on a company. This is a test version:
        features may change, pause or stop.
      </p>
      <h2>2. Not financial advice</h2>
      <ul>
        <li>
          Everything in Fledge is general information to help you learn and
          think. It is not financial, investment, tax or legal advice.
        </li>
        <li>
          Fledge never tells you to buy, sell or hold anything. Fledge is not a
          licensed financial adviser.
        </li>
        <li>
          Your investor type is a description of how you said you invest. It is
          not a recommendation.
        </li>
        <li>
          Investing is risky. You can lose some or all of your money. Decisions
          you make are your own.
        </li>
      </ul>
      <h2>3. Information can be wrong or late</h2>
      <p>
        Prices, news and summaries come from outside sources and from AI. They
        can be delayed, incomplete or wrong. News items and posts link to their
        source so you can check them; AI summaries are built from those sources
        and can still get things wrong.
      </p>
      <h2>4. Your account</h2>
      <ul>
        <li>One account per person. Keep your password private.</li>
        <li>
          When you sign up you get a one-time recovery code. Keep it safe: it is
          the only way to reset a forgotten password yourself, and anyone with
          your username and code can change your password.
        </li>
        <li>
          If you are under 18, use Fledge only with a parent or guardian’s
          permission.
        </li>
      </ul>
      <h2>5. Fair use</h2>
      <p>
        Do not misuse Fledge: no breaking or overloading it, copying its data in
        bulk, using someone else’s account, or anything illegal. We may pause or
        close accounts that do.
      </p>
      <h2>6. Your notes</h2>
      <p>
        What you write in Fledge (questions, views, notes) stays yours. You let
        us store and process it only to run Fledge for you, as described in the
        Privacy Notice.
      </p>
      <h2>7. Limits on our responsibility</h2>
      <p>
        As far as the law allows, Fledge and its team are not responsible for
        losses from decisions you make using Fledge, or from Fledge being
        unavailable or wrong.
      </p>
      <h2>8. Changes and law</h2>
      <p>
        If these terms change in an important way, we will ask you to read and
        accept them again before you continue. These terms are governed by the
        laws of Singapore. Questions: {contact}.
      </p>
    </>
  );
}

function Privacy() {
  return (
    <>
      <h1>Privacy Notice</h1>
      <p className="legal-date">Last updated {TERMS_DATE}</p>
      <p>
        This notice explains what personal data Fledge collects, why, and your
        choices, in line with Singapore’s Personal Data Protection Act 2012
        (PDPA).
      </p>
      <h2>1. What we collect</h2>
      <ul>
        <li>
          <strong>Account:</strong> your username (or your email address, on
          versions of Fledge that use email sign-in). Your password is stored
          only as a scrambled hash; we cannot read it. Your password recovery
          code is stored the same way.
        </li>
        <li>
          <strong>Your answers:</strong> where you are with investing and what
          you want from Fledge. If you choose to take the investor-type quiz,
          also your trading style and how you would react to a fall.
        </li>
        <li>
          <strong>What you save:</strong> companies you follow, questions, views
          and notes you write, and alert settings.
        </li>
        <li>
          <strong>Telegram (only if you connect it):</strong> your Telegram chat
          ID and name, so we can send the alerts you asked for.
        </li>
        <li>
          <strong>Security:</strong> a sign-in cookie and a count of failed
          sign-in attempts, to keep your account safe.
        </li>
      </ul>
      <p>
        We do not ask for your NRIC, bank or brokerage details, and Fledge never
        handles real money.
      </p>
      <h2>2. Why we use it</h2>
      <ul>
        <li>To run your account and keep your saved work private to you.</li>
        <li>
          To tailor explanations and your home page, for example Beginner
          wording and your investor type.
        </li>
        <li>To send alerts you switch on.</li>
        <li>To keep Fledge secure and fix problems.</li>
      </ul>
      <p>
        We do not sell your data, show you ads, or use your data to recommend
        investments.
      </p>
      <h2>3. Your consent</h2>
      <p>
        You agree to this notice when you create an account. You can withdraw
        your consent at any time by contacting us. Fledge cannot run an account
        without this data, so withdrawing means we close your account and delete
        your data.
      </p>
      <h2>4. Who else sees it</h2>
      <ul>
        <li>
          <strong>AI services</strong> (such as OpenAI, Anthropic or DeepSeek,
          depending on setup) receive the question you ask and the company text
          needed to answer it, but not your username, email or password. Please
          don’t type personal details into questions.
        </li>
        <li>
          <strong>Market data services</strong> (such as Finnhub) receive only
          company names and tickers, never your personal data.
        </li>
        <li>
          <strong>Telegram</strong>, only if you connect it, receives the alert
          messages you asked for.
        </li>
      </ul>
      <p>
        Some of these services are based outside Singapore: OpenAI, Anthropic,
        Finnhub and Telegram process data in the United States or elsewhere, and
        DeepSeek in China. We send each one only what it needs.
      </p>
      <h2>5. How we protect it</h2>
      <p>
        Passwords are hashed, sign-in cookies cannot be read by web pages, and
        the database keeps each account’s saved work separate so other users
        cannot see it. Only the people who run Fledge can access the database,
        and only to keep it working.
      </p>
      <h2>6. How long we keep it</h2>
      <p>
        We keep your data while your account is open. Ask us to delete your
        account and we will delete your personal data, normally within 30 days,
        unless the law requires us to keep it.
      </p>
      <h2>7. Seeing or correcting your data</h2>
      <p>
        You can ask for a copy of your personal data, or ask us to correct it.
        We will reply within 30 days, or tell you when we can.
      </p>
      <h2>8. If something goes wrong</h2>
      <p>
        If a data breach is likely to cause you significant harm, we will tell
        you and the Personal Data Protection Commission as the PDPA requires.
      </p>
      <h2>9. Contact</h2>
      <p>
        For any question or request about your personal data, contact our Data
        Protection Officer: {contact}.
      </p>
      <h2>10. Changes</h2>
      <p>
        If this notice changes in an important way, we will ask you to read and
        accept it again.
      </p>
    </>
  );
}

export default function LegalPage({ kind }) {
  return (
    <main className="account-page legal-page">
      <article className="account-card legal-card">
        <a className="brand" href="/">
          fledge<span>↗</span>
        </a>
        <nav className="legal-nav" aria-label="Legal">
          <a href="/terms" aria-current={kind === "terms" ? "page" : undefined}>
            Terms of Use
          </a>
          <a
            href="/privacy"
            aria-current={kind === "privacy" ? "page" : undefined}
          >
            Privacy Notice
          </a>
        </nav>
        {kind === "privacy" ? <Privacy /> : <Terms />}
        <a className="legal-back" href="/">
          ← Back to Fledge
        </a>
      </article>
    </main>
  );
}
