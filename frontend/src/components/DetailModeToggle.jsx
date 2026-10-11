import { useProfile } from "../lib/profile";

// Same data, different depth: plain-language explanations or the full detail.
export default function DetailModeToggle() {
  const { profile, setDetailMode } = useProfile();
  if (!profile?.completed) return null;
  const mode = profile.detail_mode;
  return (
    <div className="detail-mode" role="radiogroup" aria-label="Detail level">
      {[
        ["explain", "Explain it to me"],
        ["data", "Show me the data"],
      ].map(([key, label]) => (
        <button
          key={key}
          type="button"
          role="radio"
          aria-checked={mode === key}
          className={mode === key ? "active" : ""}
          onClick={() => mode !== key && setDetailMode(key)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
