import LoadingSkeleton from "./LoadingSkeleton";
import { readableLoad } from "../lib/loading";
import Select from "./Select";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import { stamp } from "./MarketResearch";
import AlertRating from "./AlertRating";
import AlertRoutingPreview from "./AlertRoutingPreview";
import DailyUpdates from "./DailyUpdates";
import InboxRecord from "./InboxRecord";
import WeeklyReview from "./WeeklyReview";
import { ConditionChange } from "./IdeasAndChanges";
import { inboxSummary, recordKey } from "../lib/inbox";
import "./UpdateInbox.css";
import {
  Badge,
  BellIcon,
  Button,
  Card,
  Disclosure,
  EmptyState,
  MetaRow,
  Pagination,
  RefreshIcon,
  SectionHeader,
} from "./ui";

const kindName = {
  idea: "Your saved idea",
  company: "Company news",
  condition: "Monitored condition",
  move: "Price move",
};
const reviewName = (action) =>
  ({ reviewed: "Reviewed", unresolved: "Left unresolved" })[action] ||
  "Awaiting review";

export default function UpdateInbox({
  active = true,
  filters,
  onFiltersChange,
  catalogue,
  onOpen,
  onSource,
  onReviewed,
  onReviewsChanged,
  unseenReviews = 0,
}) {
  const { company, review, page, cutoff } = filters;
  const [refresh, setRefresh] = useState(0);
  const [data, setData] = useState(null);
  const [fetching, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [weeklyOpen, setWeeklyOpen] = useState(false);
  const [emptyCompany, setEmptyCompany] = useState("");
  const isEmptyCompany = !!company && emptyCompany === company;
  // A sidebar filter changes outside this component. Withhold the earlier
  // result immediately, including before the new request effect starts.
  const loading =
    fetching ||
    (!error &&
      !isEmptyCompany &&
      (!data ||
        (data.instrument_id || "") !== company ||
        data.review !== review ||
        data.page !== page));
  const companies = [
    ...new Map(
      [...(catalogue || []), ...(data?.companies || [])].map((c) => [c.id, c]),
    ).values(),
  ];
  useEffect(() => {
    if (!active) return;
    let current = true;
    const existing =
      data &&
      (data.instrument_id || "") === company &&
      data.review === review &&
      data.page === page;
    setLoading(!existing);
    setError("");
    setEmptyCompany("");
    readableLoad(
      api.researchReview({
        days: 0,
        instrument_id: company,
        review,
        page,
        cutoff,
      }),
      existing ? 0 : 280,
    )
      .then((result) => {
        if (current) setData(result);
      })
      .catch((e) => {
        if (!current) return;
        if (
          company &&
          e.status === 404 &&
          e.message ===
            "No saved idea or watch exists for this company in your account."
        ) {
          setEmptyCompany(company);
        } else {
          setError(e.message);
        }
      })
      .finally(() => {
        if (current) setLoading(false);
      });
    return () => {
      current = false;
    };
  }, [company, review, page, cutoff, refresh, active]);
  function reset(changes = {}) {
    setLoading(true);
    onFiltersChange((current) => ({
      ...current,
      ...changes,
      page: 0,
      cutoff: "",
    }));
  }
  function turnPage(delta) {
    setLoading(true);
    onFiltersChange((current) => ({
      ...current,
      cutoff: data.cutoff,
      page: current.page + delta,
    }));
  }
  function reload() {
    reset();
    setRefresh((n) => n + 1);
  }
  async function acknowledge(kind, id, action) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await (kind === "move"
        ? api.reviewMoveAlert(id, action)
        : kind === "idea"
          ? api.reviewIdeaAlert(id, action)
          : api.reviewAlert(id, action));
      setNotice(
        action === "reviewed"
          ? "Review recorded. Your idea is unchanged."
          : "Left unresolved. Your idea is unchanged.",
      );
      reload();
      // The write succeeded even if the separate navigation-badge refresh fails.
      await onReviewed().catch(() => {});
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  const scoped = (data?.companies || []).filter(
    (c) => !company || c.id === company,
  );
  const gaps = scoped.filter((c) => c.coverage.concerns.length);
  const off = scoped.filter(
    (c) => c.mode !== "recorded" && !c.coverage.watch?.enabled,
  );
  return (
    <section className="update-inbox" aria-label="Research update inbox">
      <SectionHeader
        level="page"
        as="h2"
        icon={<BellIcon />}
        title="Updates"
        description="Price moves, company reporting and changes to your saved research."
      />
      <div className="reading-page-actions inbox-heading-actions">
        {(
          <Button onClick={() => setWeeklyOpen(true)}>
            Weekly review
            {unseenReviews > 0 && (
              <Badge status="accent">{unseenReviews} new</Badge>
            )}
          </Button>
        )}
        <Button
          variant="plain"
          icon={<RefreshIcon />}
          onClick={reload}
          disabled={loading || busy}
        >
          Refresh inbox
        </Button>
      </div>
      <WeeklyReview
        open={weeklyOpen}
        onClose={() => setWeeklyOpen(false)}
        onOpen={onOpen}
        onChanged={onReviewsChanged}
      />
      {!company && data?.daily_reports_enabled && (
        <DailyUpdates refresh={refresh} onOpen={onOpen} onSource={onSource} />
      )}
      <Disclosure
        className="inbox-filter-disclosure"
        title="Filter updates"
        description={`${companies.find((c) => c.id === company)?.symbol || "All companies"} · ${review === "all" ? "All updates" : reviewName(review === "pending" ? null : review)}`}
      >
        <div className="inbox-filters">
          <label>
            Company
            <Select
              aria-label="Inbox company"
              value={company}
              disabled={busy}
              onChange={(e) => {
                reset({ company: e.target.value });
              }}
            >
              <option value="">All my ideas and watches</option>
              {companies.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.symbol} · {c.name}
                </option>
              ))}
            </Select>
          </label>
          <label>
            Show updates
            <Select
              aria-label="Show updates"
              value={review}
              disabled={busy}
              onChange={(e) => {
                reset({ review: e.target.value });
              }}
            >
              <option value="pending">Awaiting review</option>
              <option value="unresolved">Left unresolved</option>
              <option value="reviewed">Reviewed</option>
              <option value="all">All updates</option>
            </Select>
          </label>
        </div>
        {data && (
          <p className="fine">
            Showing {data.records.length ? page * data.page_size + 1 : 0}–
            {page * data.page_size + data.records.length} of {data.total} ·
            recorded through {stamp(data.cutoff)}. Review status is current;
            source event dates may be earlier.
          </p>
        )}
      </Disclosure>
      {!loading && data && !isEmptyCompany && (
        <MetaRow aria-label="Update counts">
          <span>
            {data.total}{" "}
            {review === "pending"
              ? "awaiting review"
              : data.total === 1
                ? "update"
                : "updates"}
          </span>
          <span>Newest first</span>
          <span>Through {stamp(data.cutoff)}</span>
        </MetaRow>
      )}
      {notice && (
        <p role="status" className="notice">
          {notice}
        </p>
      )}
      {error && (
        <div role="alert" className="warning">
          <p>{error}</p>
          <Button onClick={reload} disabled={busy}>
            Retry inbox
          </Button>
        </div>
      )}
      {loading && <LoadingSkeleton label="Loading saved updates…" />}
      {!loading && isEmptyCompany && (
        <EmptyState
          title="No updates in this view"
          description="No saved idea or watch exists for this company yet."
          actions={
            <Button
              variant="tertiary"
              onClick={() => onOpen(company, "workspace")}
            >
              Open company research ↗
            </Button>
          }
        />
      )}
      {!loading && !error && !isEmptyCompany && data && (
        <>
          {!data.records.length && (
            <EmptyState
              title={
                review === "pending"
                  ? "Nothing awaiting review"
                  : "No updates in this view"
              }
              description="Choose another company or review status. Source coverage and quiet checks remain available below."
            />
          )}
          <div className="inbox-records change-collection">
            {data.records.map((record) => {
              const d = record.detail,
                summary = inboxSummary(record);
              if (record.kind === "condition")
                return (
                  <Card
                    as="article"
                    className="inbox-record"
                    data-kind={record.kind}
                    data-record-id={record.id}
                    key={recordKey(record)}
                  >
                    <div className="inbox-kind">{kindName[record.kind]}</div>
                    <ConditionChange change={d} onOpen={onOpen} />
                    <AlertRoutingPreview record={record} />
                    <AlertRating record={record} />
                  </Card>
                );
              return (
                <InboxRecord
                  key={recordKey(record)}
                  record={record}
                  busy={busy}
                  onOpen={onOpen}
                  onSource={onSource}
                  onReview={acknowledge}
                />
              );
            })}
          </div>
          {data.total > data.page_size && (
            <Pagination
              className="review-pagination"
              label="Update pages"
              page={page + 1}
              totalPages={Math.ceil(data.total / data.page_size)}
              disabled={busy}
              previousLabel="Previous updates"
              nextLabel="Next updates"
              onPrevious={() => turnPage(-1)}
              onNext={() => turnPage(1)}
            />
          )}
          <Disclosure
            className={`inbox-coverage${gaps.length ? " has-concerns" : ""}`}
            title="Source coverage"
            description={`${gaps.length ? `${gaps.length} ${gaps.length === 1 ? "company needs" : "companies need"} attention` : "Inspect latest checks"}${off.length ? ` · ${off.length} ${off.length === 1 ? "watch" : "watches"} off` : ""}`}
          >
            <p className="fine">
              A quiet inbox does not mean nothing important happened. These are
              the latest recorded checks; opening this inbox does not refresh
              sources.
            </p>
            {!scoped.length && (
              <p>
                No saved ideas or watches yet. Open a company to begin your
                research.
              </p>
            )}
            {scoped.map((c) => (
              <div key={c.id}>
                <strong>
                  {c.symbol} · {c.name}
                </strong>
                <p className="fine">
                  {c.mode === "recorded"
                    ? "Recorded fictional example"
                    : c.coverage.watch?.enabled
                      ? `Local watch on · every ${c.coverage.watch.interval_minutes === 60 ? "hour" : "four hours"} while the app runs`
                      : "Local watch off"}
                </p>
                {c.coverage.concerns.map((message) => (
                  <p className="fine" key={message}>
                    {message}
                  </p>
                ))}
                <Button onClick={() => onOpen(c.id, "workspace")}>
                  Open {c.symbol} research ↗
                </Button>
              </div>
            ))}
          </Disclosure>
          <p className="fine">
            Marking an alert reviewed records your attention. It does not
            approve the investment, resolve a risk or change your saved idea.
          </p>
        </>
      )}
    </section>
  );
}
