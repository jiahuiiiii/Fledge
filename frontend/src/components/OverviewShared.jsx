import { Badge, Button, Card, ChevronRightIcon, SectionHeader } from "./ui";
import { dayLabel, platformName } from "../lib/beginnerSummary";

const EFFECT_WORDS = {
  could_help: "Could help",
  could_hurt: "Could hurt",
  mixed_or_unclear: "Could go either way",
};
const EFFECT_TONE = {
  could_help: "positive",
  could_hurt: "negative",
  mixed_or_unclear: "mixed",
};

export function PriceMoveLine({ price, pro = false }) {
  if (!price) return null;
  return (
    <section className="bs-price-row" aria-label="Share price">
      {pro && <strong>{price.price}</strong>}
      {price.move && (
        <Badge tone={price.mood} shape={false}>
          {price.move}
        </Badge>
      )}
      <span className="bs-price-note">
        {pro
          ? "Prices move for many reasons."
          : "Price moves may have other causes."}
      </span>
    </section>
  );
}

export function SignalLights({ name, lights, pointer }) {
  return (
    <section aria-label={`${name} at a glance`}>
      <ul className="bs-summary-cards">
        {lights.map((light) => (
          <li key={light.key}>
            <Card
              as="a"
              interactive
              href={`#bs-${light.key}`}
              className="bs-summary-card"
              aria-label={`${light.title}: ${light.status}. Show details.`}
            >
              <SectionHeader
                level="card"
                as="span"
                title={light.title}
                actions={
                  <span className="bs-summary-arrow" aria-hidden="true">
                    <ChevronRightIcon />
                  </span>
                }
              />
              <span className="bs-summary-status">{light.status}</span>
            </Card>
          </li>
        ))}
      </ul>
      {pointer && <p className="bs-pointer">{pointer}</p>}
    </section>
  );
}

export function ToneHeadlineGroups({
  groups,
  onSource,
  reading,
  social = false,
  includeUnrated = false,
}) {
  const headline = (item) => (
    <li key={item.id}>
      <button
        type="button"
        className="bs-link"
        onClick={() => onSource?.(item)}
      >
        {item.headline}
      </button>
      <small>
        {item.kind === "social"
          ? platformName(item.platform)
          : item.source || item.publisher || "News"}{" "}
        · {dayLabel(item.published_at)}
      </small>
    </li>
  );
  const group = (label, mood, list, limit = 3) =>
    list.length > 0 && (
      <div className={`bs-group tone-${mood}`}>
        <h5>
          {label} <Badge>{list.length}</Badge>
        </h5>
        <ul className="bs-headlines">{list.slice(0, limit).map(headline)}</ul>
      </div>
    );
  return (
    <>
      {group(
        social ? "Upbeat posts (opinions)" : "Good news",
        "good",
        groups.good,
      )}
      {group(
        social ? "Worried posts (opinions)" : "Bad news",
        "bad",
        groups.bad,
      )}
      {group(
        social
          ? "Mixed posts: good and bad"
          : "Mixed: good and bad in one story",
        "mixed",
        groups.mixed,
      )}
      {!social && groups.neutral.length > 0 && (
        <details className="bs-group tone-neutral">
          <summary>
            Neutral, neither good nor bad <Badge>{groups.neutral.length}</Badge>
          </summary>
          <ul className="bs-headlines">
            {groups.neutral.slice(0, 5).map(headline)}
          </ul>
        </details>
      )}
      {(!reading || includeUnrated) &&
        group("Not rated yet", "none", groups.unrated, social ? 3 : 5)}
    </>
  );
}

export function YourViewCard({ savedView, name, onSaveView }) {
  return (
    <Card aria-labelledby="bs-yourview">
      <SectionHeader level="card" as="h4" id="bs-yourview" title="Your view" />
      {savedView?.question ? (
        <>
          <p>{savedView.question}</p>
          {savedView.reasoning && (
            <p className="bs-muted">{savedView.reasoning}</p>
          )}
        </>
      ) : (
        <p className="bs-muted">
          Why are you interested in {name}? Write it down in a sentence. Later,
          you can turn on news alerts to hear when news backs it up or goes
          against it.
        </p>
      )}
      {onSaveView && (
        <div className="bs-actions">
          <Button variant="primary" onClick={onSaveView}>
            {savedView ? "Edit my view" : "Write my view"}
          </Button>
        </div>
      )}
    </Card>
  );
}

export function WorldSignalCard({ links, worldState, onWorld, limit = 3 }) {
  return (
    <Card id="bs-world" tabIndex={-1} aria-labelledby="bs-world-title">
      <SectionHeader
        level="card"
        as="h4"
        id="bs-world-title"
        title="World news that may matter"
      />
      {links.length ? (
        <ul className="bs-world">
          {links.slice(0, limit).map(({ article, link }) => (
            <li key={article.id}>
              <Badge tone={EFFECT_TONE[link.effect]}>
                {EFFECT_WORDS[link.effect]}
              </Badge>
              <a href={article.url} target="_blank" rel="noopener noreferrer">
                {article.headline}
              </a>
              <small className="bs-meta">
                {article.publisher} · {dayLabel(article.published_at)}
              </small>
              <p>{link.reason}</p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="bs-muted">{worldState.reason}</p>
      )}
      {links.length > 0 && (
        <p className="bs-caveat">
          These are possibilities to think about, not predictions or tips.
        </p>
      )}
      <div className="bs-actions">
        <Button
          variant="tertiary"
          size="sm"
          iconEnd={<ChevronRightIcon />}
          onClick={onWorld}
        >
          World news
        </Button>
      </div>
    </Card>
  );
}
