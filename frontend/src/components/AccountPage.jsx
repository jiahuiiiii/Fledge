import { useEffect, useState } from "react";
import { useProfile } from "../lib/profile";
import { typeName } from "../lib/investorTypes";
import { ProModeSwitch } from "./DetailModeToggle";
import { AccountSecurityDialog } from "./AccountSecurity";
import { Badge, Button, Card, SectionHeader, UserIcon } from "./ui";
import "./AccountPage.css";

// Presentation for the existing authenticated controls. Opening the page does
// not save a preference, create a code or change the session.
export default function AccountPage({ session, controls, onBack }) {
  const { profile, home } = useProfile();
  const [securityOpen, setSecurityOpen] = useState(false);
  const investor = profile?.completed && typeName(profile.investor_type);
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
      />
      <div className="reading-page-actions">
        <Button variant="tertiary" onClick={onBack}>
          ← Back to research
        </Button>
      </div>
      <Card>
        <SectionHeader
          level="card"
          as="h2"
          title={session.username || session.email || "Local workspace"}
        />
        <div>
          <Badge>
            {session.mode === "password"
              ? "Username sign-in"
              : session.mode === "managed"
                ? "Email sign-in"
                : "Local access"}
          </Badge>
        </div>
      </Card>
      <Card>
        {home ? <ProModeSwitch /> : <p role="status">Loading preferences…</p>}
      </Card>
      {profile && (
        <Card>
          <SectionHeader
            level="card"
            as="h2"
            title="Investor profile"
            description={investor || "Personalise your starting points."}
          />
          <div>
            <Button
              variant="tertiary"
              onClick={() => dispatchEvent(new Event("fledge:retake-quiz"))}
            >
              {profile.completed ? "Retake questions" : "Set up profile"}
            </Button>
          </div>
        </Card>
      )}
      {session.mode === "password" && session.username && (
        <Card>
          <SectionHeader
            level="card"
            as="h2"
            title="Security"
            description={
              session.has_recovery_code
                ? "Recovery code is set."
                : "Recovery code is not set."
            }
          />
          <div>
            <Button onClick={() => setSecurityOpen(true)}>
              Password and recovery code
            </Button>
          </div>
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
