import { useProfile } from "../lib/profile";

// Everyone starts in Beginner. Pro tools (financials, charts, comparisons and
// the full research tabs) are switched on here, inside the account menu, so
// the first screens stay simple.
export function ProModeSwitch() {
  const { home, mode, setDetailMode } = useProfile();
  if (!home) return null;
  const pro = mode === "data";
  return (
    <div className="pro-mode-switch">
      <label>
        <input
          type="checkbox"
          role="switch"
          checked={pro}
          onChange={() => setDetailMode(pro ? "explain" : "data")}
        />
        <span>
          <strong>Pro tools</strong>
          <small>
            {pro
              ? "On: financials, charts, comparisons and every research tab."
              : "Off: simple summaries only. Turn on for financials, charts and comparisons."}
          </small>
        </span>
      </label>
    </div>
  );
}

// For a copy of Fledge without accounts: the same switch in a small menu.
export function SettingsMenu() {
  return (
    <details className="account-menu">
      <summary>Settings</summary>
      <div>
        <ProModeSwitch />
      </div>
    </details>
  );
}

export default ProModeSwitch;
