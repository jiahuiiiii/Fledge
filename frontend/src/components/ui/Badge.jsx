import "./ui.css";

// Shapes keep tone readable without colour.
export const TONE_SHAPE = {
  positive: "▲",
  negative: "▼",
  mixed: "◆",
  neutral: "●",
  unknown: "○",
};

// Older code says good/bad/none for the same tones. Anything else, including
// a missing value, shows as unknown rather than being guessed. "caution" from
// financialStory.js is not mapped: decide its tone when that page moves over.
const TONE_ALIASES = { good: "positive", bad: "negative", none: "neutral" };

export function toneOf(value) {
  const tone = TONE_ALIASES[value] || value;
  return Object.hasOwn(TONE_SHAPE, tone) ? tone : "unknown";
}

// Small pill label. Pass `tone` for an assessment (with its shape), or
// `status` (neutral, info, accent, new) for a plain label. The text is always
// the children; the shape is decorative.
export default function Badge({
  tone,
  status = "neutral",
  shape = true,
  className = "",
  children,
  ...rest
}) {
  const resolved = tone === undefined ? null : toneOf(tone);
  const variant = resolved ? `tone-${resolved}` : status;
  return (
    <span
      className={`ui-badge ui-badge--${variant} ${className}`.trim()}
      {...rest}
    >
      {resolved && shape && (
        <span className="ui-badge__shape" aria-hidden="true">
          {TONE_SHAPE[resolved]}
        </span>
      )}
      {children}
    </span>
  );
}
