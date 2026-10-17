export default function AlertRoutingPreview({ record }) {
  if (!record.routing || record.detail?.withheld) return null;
  const label = {
    telegram: "Telegram immediately",
    digest: "Daily digest",
    app: "In the app only",
  }[record.routing.channel];
  if (!label) return null;
  return (
    <p
      className="fine"
      aria-label={
        record.routing.preview ? "Delivery preview" : "Delivery route"
      }
    >
      {record.routing.preview ? "Routing preview" : "Delivery route"} · {label}.{" "}
      {record.routing.reason}
    </p>
  );
}
