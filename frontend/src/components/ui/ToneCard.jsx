import Card from "./Card";

// A card tinted by sentiment: positive, negative, mixed, neutral or unknown.
// Tint and the status colour come from the app's tone tokens; no side borders.
export default function ToneCard({ tone = "unknown", className = "", children, ...rest }) {
  return (
    <Card variant="inset" className={`ui-tone-card ${className}`} data-tone={tone} {...rest}>
      {children}
    </Card>
  );
}
