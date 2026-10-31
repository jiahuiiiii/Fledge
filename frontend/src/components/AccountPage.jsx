import { useEffect, useState } from "react";
import { useProfile } from "../lib/profile";
import { INVESTOR_TYPES, typeName } from "../lib/investorTypes";
import { AccountSecurityDialog } from "./AccountSecurity";
import TelegramSettings from "./TelegramSettings";
import { Badge, Button, Card, SectionHeader, UserIcon } from "./ui";
import "./AccountPage.css";

// Presentation for the existing authenticated controls. Opening the page does
// not save a preference, create a code or change the session.
export default function AccountPage({ session, controls, onBack }) {
  const { profile } = useProfile();
  const [securityOpen, setSecurityOpen] = useState(false);
  const type = profile?.completed
    ? INVESTOR_TYPES[profile.investor_type]
    : null;
  const canSignOut = ["managed", "password"].includes(session.mode);
  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      const heading = document.getElementById("account-settings-title");
      window.scrollTo(0, 0);
      heading?.closest("main")?.scrollTo(0, 0);
      heading?.setAttribute("tabindex", "-1");
      heading?.focus({ preventScroll: true });
    });
    return () => cancelAnimationFrame(frame);
  }, []);
  return (
    <section
      className="account-settings-page"
      aria-labelledby="account-settings-title"
    >
      <SectionHeader
        level="page"
        as="h1"
        id="account-settings-title"
        icon={<UserIcon />}
        title="Account"
        actions={
          <Button variant="tertiary" onClick={onBack}>
            ← Back to research
          </Button>
        }
      />
      <Card>
        <SectionHeader
          level="card"
          as="h2"
          title={session.username || session.email || "Local workspace"}
          description="How you sign in to this workspace."
          actions={
            <Badge>
              {session.mode === "password"
                ? "Username sign-in"
                : session.mode === "managed"
                  ? "Email sign-in"
                  : "Local access"}
            </Badge>
          }
        />
      </Card>
      {profile && (
        <Card>
          <SectionHeader
            level="card"
            as="h2"
            title="Investor profile"
            description={
              type?.name || typeName(profile.investor_type) || "Not set up yet."
            }
            actions={
              <Button
                variant="secondary"
                onClick={() => dispatchEvent(new Event("fledge:retake-quiz"))}
              >
                {profile.completed ? "Retake questions" : "Set up profile"}
              </Button>
            }
          />
          {type && <p className="account-note">{type.short}</p>}
          <div className="account-explain">
            <strong>How Fledge uses it</strong>
            <ul>
              <li>
                Chooses which research questions and shortcuts come first.
              </li>
              <li>Shapes the wording and the examples on your home page.</li>
              <li>
                Never picks, ranks or recommends investments, and nothing is
                shared.
              </li>
            </ul>
          </div>
        </Card>
      )}
      <TelegramSettings
        wrap={(trigger) => (
          <Card>
            <SectionHeader
              level="card"
              as="h2"
              title="Telegram alerts"
              description="Urgent alerts, price moves and the daily summary, sent to your Telegram. Off until you connect it."
              actions={trigger}
            />
          </Card>
        )}
      />
      {session.mode === "password" && session.username && (
        <Card>
          <SectionHeader
            level="card"
            as="h2"
            title="Security"
            description={
              session.has_recovery_code
                ? "Your password can be reset with your recovery code."
                : "No recovery code yet: a forgotten password could only be reset by the Fledge team."
            }
            actions={
              <Button onClick={() => setSecurityOpen(true)}>
                Password and recovery code
              </Button>
            }
          />
          <AccountSecurityDialog
            open={securityOpen}
            onClose={() => setSecurityOpen(false)}
            hasRecoveryCode={!!session.has_recovery_code}
            onCodeChanged={controls?.onCodeChanged}
          />
        </Card>
      )}
      {controls?.error && <p role="alert">{controls.error}</p>}
      <footer className="account-settings-footer">
        {canSignOut && (
          <Button
            danger
            disabled={controls?.busy}
            onClick={controls?.onSignOut}
          >
            Sign out
          </Button>
        )}
        <div className="account-settings-legal">
          <Button
            variant="tertiary"
            size="sm"
            href="/terms"
            target="_blank"
            rel="noopener"
          >
            Terms
          </Button>
          <Button
            variant="tertiary"
            size="sm"
            href="/privacy"
            target="_blank"
            rel="noopener"
          >
            Privacy
          </Button>
        </div>
      </footer>
    </section>
  );
}
