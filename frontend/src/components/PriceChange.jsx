const signed = (value) =>
  `${value > 0 ? "+" : value < 0 ? "−" : ""}${Math.abs(value).toFixed(2)}`;
const day = (value) =>
  new Date(`${value}T12:00:00Z`).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  });
export default function PriceChange({ movement }) {
  if (!movement) return null;
  return (
    <span
      className={`price-change ${movement.change > 0 ? "positive" : movement.change < 0 ? "negative" : "unchanged"}`}
    >
      <span>
        {signed(movement.change)}
        {movement.percent != null && ` (${signed(movement.percent)}%)`}
      </span>
      {movement.referenceDate && (
        <span className="price-change-basis">
          vs {day(movement.referenceDate)} close
        </span>
      )}
    </span>
  );
}
