import { lazy, useEffect, useState } from "react";
import { api } from "../../api/client";
import { formatTimestamp } from "../../lib/dateTime";
import { inboxSummary, recordKey } from "../../lib/inbox";
import { Badge, Button, Card, ChevronRightIcon, SectionHeader } from "../ui";
import PersonalHome from "../PersonalHome";
import PortfolioRead from "../PortfolioRead";
import { useWorkspace } from "./WorkspaceContext";

// The home page's blocks as widgets: each takes what it needs from context.
const CompanyOverview = lazy(() => import("../CompanyOverview"));

export function HomeWelcome() {
  const { onAddCompany, onOpenCompany, practice } = useWorkspace();
  return (
    <PersonalHome
      onAddCompany={onAddCompany}
      onOpenCompany={onOpenCompany}
      practice={practice}
    />
  );
}

export function HomePortfolio() {
  const { onOpenCompany } = useWorkspace();
  return <PortfolioRead onOpenCompany={onOpenCompany} />;
}

export function HomeCompanies() {
  const { catalogue, onOpen } = useWorkspace();
  return <CompanyOverview catalogue={catalogue} onOpen={onOpen} />;
}

// ---- Optional home widgets: short views of pages that already exist. ----
// Each reads saved records only (no source fetch, no AI) and links to the full
// page. They re-read when the app says home data changed.

function useSaved(read) {
  const [state, setState] = useState({ value: null, error: "" });
  useEffect(() => {
    let active = true;
    const load = () =>
      read()
        .then((value) => active && setState({ value, error: "" }))
        .catch(
          (failure) =>
            active && setState((old) => ({ ...old, error: failure.message })),
        );
    load();
    addEventListener("fledge:home-changed", load);
    return () => {
      active = false;
      removeEventListener("fledge:home-changed", load);
    };
  }, []);
  return state;
}

const KIND = {
  idea: "Your saved idea",
  company: "Company news",
  condition: "Monitored condition",
  move: "Price move",
};

function RecordLines({ records, onOpen }) {
  return (
    <ul className="ws-records">
      {records.map((record) => {
        const d = record.detail || {};
        const summary = inboxSummary(record);
        return (
          <li key={recordKey(record)}>
            <span className="ws-record-meta">
              {d.symbol && <Badge>{d.symbol}</Badge>}
              <span>{KIND[record.kind] || "Update"}</span>
              <time dateTime={record.created_at}>
                {formatTimestamp(record.created_at)}
              </time>
            </span>
            {d.instrument_id && onOpen ? (
              <button
                type="button"
                className="ws-record-title text-link"
                onClick={() =>
                  onOpen(
                    d.instrument_id,
                    record.kind === "idea" ? "idea" : "workspace",
                  )
                }
              >
                {summary.title}
              </button>
            ) : (
              <strong className="ws-record-title">{summary.title}</strong>
            )}
          </li>
        );
      })}
    </ul>
  );
}

function SavedCard({ id, title, count, action, children }) {
  return (
    <Card aria-labelledby={id}>
      <SectionHeader
        level="card"
        as="h3"
        id={id}
        title={
          <>
            {title}
            {count > 0 && <Badge className="ws-count">{count}</Badge>}
          </>
        }
        actions={
          action && (
            <Button
              size="sm"
              variant="tertiary"
              iconEnd={<ChevronRightIcon />}
              onClick={action[1]}
            >
              {action[0]}
            </Button>
          )
        }
      />
      {children}
    </Card>
  );
}

// What the app recorded in the past day: price moves, company news, checks.
export function HomeAlerts() {
  const { onOpen, onUpdates } = useWorkspace();
  const { value, error } = useSaved(() =>
    api.researchReview({ days: 1, review: "all" }),
  );
  return (
    <SavedCard
      id="ws-alerts-title"
      title="Today’s alerts"
      count={value?.total}
      action={["All updates", onUpdates]}
    >
      {error && !value ? (
        <p role="alert">{error}</p>
      ) : !value ? (
        <p role="status">Reading saved updates…</p>
      ) : value.records.length ? (
        <>
          <RecordLines records={value.records.slice(0, 5)} onOpen={onOpen} />
          {value.total > 5 && (
            <p className="ws-more">{value.total - 5} more in Updates.</p>
          )}
        </>
      ) : (
        <p className="ws-quiet">
          Nothing recorded in the past day. A quiet list doesn’t mean nothing
          important happened.
        </p>
      )}
    </SavedCard>
  );
}

// Saved updates still awaiting your review, newest first.
export function HomeInbox() {
  const { onOpen, onUpdates } = useWorkspace();
  const { value, error } = useSaved(() =>
    api.researchReview({ days: 0, review: "pending" }),
  );
  const waiting = value?.totals?.pending_count ?? value?.total ?? 0;
  return (
    <SavedCard
      id="ws-inbox-title"
      title="Updates to review"
      count={waiting}
      action={["Review", onUpdates]}
    >
      {error && !value ? (
        <p role="alert">{error}</p>
      ) : !value ? (
        <p role="status">Reading saved updates…</p>
      ) : value.records.length ? (
        <RecordLines records={value.records.slice(0, 3)} onOpen={onOpen} />
      ) : (
        <p className="ws-quiet">Nothing is waiting for review.</p>
      )}
    </SavedCard>
  );
}

const EFFECT = {
  could_help: "could help",
  could_hurt: "could hurt",
  mixed_or_unclear: "unclear for",
};

// The saved world headlines, those linked to your companies first. Opening
// World fetches newer headlines; this widget only reads what is saved.
export function HomeWorld() {
  const { onWorld } = useWorkspace();
  const { value, error } = useSaved(() => api.worldNews());
  const symbols = Object.fromEntries(
    (value?.companies || []).map((c) => [c.id, c.symbol]),
  );
  const articles = value?.articles || [];
  const linked = (a) => (a.links || []).some((l) => symbols[l.company_id]);
  const shown = [
    ...articles.filter(linked),
    ...articles.filter((a) => !linked(a)),
  ].slice(0, 4);
  return (
    <SavedCard
      id="ws-world-title"
      title="World headlines"
      action={["Open World", onWorld]}
    >
      {error && !value ? (
        <p role="alert">{error}</p>
      ) : !value ? (
        <p role="status">Reading saved headlines…</p>
      ) : shown.length ? (
        <>
          <p className="ws-more">
            Saved {formatTimestamp(value.checked_at, { fallback: "earlier" })}
            {value.stale && " · open World for newer headlines"}
          </p>
          <ul className="ws-records">
            {shown.map((a) => (
              <li key={a.id}>
                <a
                  className="ws-record-title"
                  href={a.url}
                  target="_blank"
                  rel="noreferrer noopener"
                >
                  {a.headline}
                </a>
                <span className="ws-record-meta">
                  <span>{a.publisher}</span>
                  <time dateTime={a.published_at}>
                    {formatTimestamp(a.published_at)}
                  </time>
                </span>
                {(a.links || [])
                  .filter((l) => symbols[l.company_id])
                  .slice(0, 3)
                  .map((l) => (
                    <small
                      key={l.company_id}
                      className={`ws-effect ${l.effect}`}
                    >
                      {EFFECT[l.effect] || "unclear for"}{" "}
                      {symbols[l.company_id]}: {l.reason}
                    </small>
                  ))}
              </li>
            ))}
          </ul>
          <p className="ws-more">
            Possible effects to read about, not predictions.
          </p>
        </>
      ) : (
        <p className="ws-quiet">
          No world headlines are saved yet. Open World to fetch them.
        </p>
      )}
    </SavedCard>
  );
}
