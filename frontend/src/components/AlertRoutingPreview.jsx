export default function AlertRoutingPreview({ record }) {
  if (!record.routing?.preview || record.detail?.withheld) return null;
  const label = {
    telegram: "Telegram immediately",
    digest: "Daily digest",
    app: "In the app only",
  }[record.routing.channel];
  if (!label) return null;
  return (
    <p className="fine" aria-label="Delivery preview">
      Routing preview · {label}. {record.routing.reason}
    </p>
  );
}
