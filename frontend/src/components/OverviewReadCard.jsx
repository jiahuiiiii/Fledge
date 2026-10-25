import { Button, Card, SectionHeader } from "./ui";

export default function OverviewReadCard({
  title,
  reading,
  figures,
  onEvidence,
  onView,
  destination,
}) {
  return (
    <Card as="article" className="overview-read-card">
      <SectionHeader level="card" as="h3" title={title} />
      <p>{reading}</p>
      <div className="overview-read-figures">
        {figures.map(({ label, value }) => (
          <span key={label}>
            <strong>{value ?? "Unknown"}</strong>
            <small>{label}</small>
          </span>
        ))}
      </div>
      <div className="overview-read-actions">
        <Button variant="tertiary" size="sm" onClick={onEvidence}>
          View evidence
        </Button>
        <Button variant="tertiary" size="sm" onClick={onView}>
          {destination} →
        </Button>
      </div>
    </Card>
  );
}
