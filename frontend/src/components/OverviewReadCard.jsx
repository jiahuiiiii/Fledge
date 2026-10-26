import { Button, Card } from "./ui";

// One business topic: a reading sentence, up to two figures (each opens its
// evidence) and a link to the tab that has the detail.
export default function OverviewReadCard({ reading, figures, onView, destination }) {
  return (
    <Card as="article" className="overview-read-card">
      <p>{reading}</p>
      <div className="overview-read-figures">
        {figures.map(({ label, value, onOpen }) => {
          const body = (
            <>
              <strong>{value ?? "Unknown"}</strong>
              <small>{label}</small>
            </>
          );
          return onOpen ? (
            <button type="button" key={label} onClick={onOpen} aria-label={`${label}: ${value ?? "Unknown"}. Show evidence.`}>
              {body}
            </button>
          ) : (
            <span key={label}>{body}</span>
          );
        })}
      </div>
      <div className="overview-read-actions">
        <Button variant="tertiary" size="sm" onClick={onView}>
          {destination} →
        </Button>
      </div>
    </Card>
  );
}
