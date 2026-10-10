export const toneNames = {
  positive: "Positive",
  negative: "Negative",
  mixed: "Mixed",
  neutral: "Neutral",
  unclear: "Unclear",
};

export default function ToneFilters({ selected, onChange, counts, controls }) {
  return (
    <div
      className="sentiment-counts tone-filters"
      role="group"
      aria-label="Filter analysed sources by tone"
    >
      <button
        type="button"
        aria-pressed={selected === "all"}
        aria-controls={controls}
        onClick={() => onChange("all")}
      >
        All tones
      </button>
      {Object.entries(toneNames).map(([key, label]) => (
        <button
          type="button"
          className={`tone-${key}`}
          key={key}
          aria-pressed={selected === key}
          aria-controls={controls}
          onClick={() => onChange(selected === key ? "all" : key)}
        >
          {label}
          {counts && (
            <>
              {" "}
              <b>{counts[key]}</b>
            </>
          )}
        </button>
      ))}
    </div>
  );
}
