import { Button, Card, ChevronRightIcon, SectionHeader } from "../ui";
import { plainTone } from "../../lib/beginnerSummary";
import {
  PriceMoveLine,
  SignalLights,
  ToneHeadlineGroups,
  WorldSignalCard,
  YourViewCard,
} from "../OverviewShared";
import { useWorkspace } from "./WorkspaceContext";
import "../BeginnerSummary.css";

// The Beginner summary's blocks as self-contained widgets. Each reads the
// summary model BeginnerSummary computes (context.summary) and the actions
// App.jsx provides, so the grid can place it anywhere.

export function SummarySignals() {
  const { summary } = useWorkspace();
  return (
    <div className="bs-signals-widget">
      {summary.price?.move && <PriceMoveLine price={summary.price} />}
      <SignalLights
        name={summary.name}
        lights={summary.lights}
        pointer={summary.pointer}
      />
    </div>
  );
}

export function SummaryNews() {
  const { summary, onRate, onUpdate, onSource, onView, rating, practice } =
    useWorkspace();
  const { newsGroups, postGroups, news, reading } = summary;
  return (
    <Card id="bs-news" tabIndex={-1} aria-labelledby="bs-news-title">
      <SectionHeader
        level="card"
        as="h4"
        id="bs-news-title"
        title="News: what happened"
      />
      <p className="bs-meaning">{summary.newsMeaning}</p>
      {onRate &&
        !reading &&
        (newsGroups.unrated.length > 0 || postGroups.unrated.length > 0) && (
          <div className="bs-rate">
            <Button variant="primary" onClick={onRate} disabled={!!rating}>
              {rating === "running"
                ? "Rating… about a minute"
                : rating
                  ? "Getting the latest posts first…"
                  : "Rate with AI"}
            </Button>
            <small>
              Fledge reads the news and posts and marks each good, bad or mixed.
            </small>
          </div>
        )}
      <ToneHeadlineGroups
        groups={newsGroups}
        onSource={onSource}
        reading={reading}
      />
      {!news.length && onUpdate && (
        <p>
          <Button variant="tertiary" size="inline" onClick={onUpdate}>
            Get the latest news
          </Button>
        </p>
      )}
      <div className="bs-actions">
        <Button
          variant="tertiary"
          size="sm"
          iconEnd={<ChevronRightIcon />}
          onClick={() => onView?.("evidence")}
        >
          All news & posts
        </Button>
        {!practice && onRate && (
          <Button
            variant="tertiary"
            size="sm"
            iconEnd={<ChevronRightIcon />}
            onClick={() => onView?.("evidence")}
          >
            Turn on news alerts
          </Button>
        )}
      </div>
    </Card>
  );
}

export function SummaryPeople() {
  const { summary, onSource } = useWorkspace();
  const { postGroups, social, reading } = summary;
  return (
    <Card id="bs-people" tabIndex={-1} aria-labelledby="bs-people-title">
      <SectionHeader
        level="card"
        as="h4"
        id="bs-people-title"
        title="What people online are saying"
      />
      <p className="bs-meaning">{summary.peopleMeaning}</p>
      {social.length > 0 && (
        <p className="bs-muted bs-platforms">
          {social
            .map((s) => `${s.platform}: ${plainTone(s.tone).toLowerCase()}`)
            .join(" · ")}
        </p>
      )}
      <ToneHeadlineGroups
        groups={postGroups}
        onSource={onSource}
        reading={reading}
        social
      />
    </Card>
  );
}

export function SummaryWorld() {
  const { summary, onWorld } = useWorkspace();
  return (
    <WorldSignalCard
      links={summary.links}
      worldState={summary.worldState}
      onWorld={onWorld}
    />
  );
}

export function SummaryView() {
  const { summary, savedView, onSaveView } = useWorkspace();
  return (
    <YourViewCard
      savedView={savedView}
      name={summary.name}
      onSaveView={onSaveView}
    />
  );
}
