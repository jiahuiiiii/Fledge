import { useProfile } from "../lib/profile";

// Beginner shows a plain summary and hides charts and detailed financials;
// Pro shows everything. Same saved research either way.
export default function DetailModeToggle() {
  const { home, mode, setDetailMode } = useProfile();
  if (!home) return null;
  return (
    <div className="detail-mode" role="radiogroup" aria-label="View mode">
      {[
        ["explain", "Beginner", "A plain summary: price, news, what people say, world events"],
        ["data", "Pro", "Everything: financials, charts, comparisons and full evidence"],
      ].map(([key, label, title]) => (
        <button
          key={key}
          type="button"
          role="radio"
          aria-checked={mode === key}
          title={title}
          className={mode === key ? "active" : ""}
          onClick={() => mode !== key && setDetailMode(key)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
