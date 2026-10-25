import { useProfile } from "../lib/profile";

// Everyone starts in Beginner. Pro tools (financials, charts, comparisons and
// the full research tabs) are switched on here, on the account page, so
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
          <small>Financials, charts and comparisons.</small>
        </span>
      </label>
    </div>
  );
}

export default ProModeSwitch;
