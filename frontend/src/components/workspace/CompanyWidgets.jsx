import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { formatTimestamp } from "../../lib/dateTime";
import { requestUpdate } from "../../lib/updateRequest";
import { watchFrequencyLabel } from "../../lib/watchLanes";
import { Button, Card, ChevronRightIcon, SectionHeader } from "../ui";
import AnalystTargets from "../AnalystTargets";
import { SnapshotGlance } from "../CompanySnapshot";
import HistoricalPrices from "../HistoricalPrices";
import LatestActivity from "../LatestActivity";
import OverviewSections from "../OverviewSections";
import WatchCheckHistory from "../WatchCheckHistory";
import { useWorkspace } from "./WorkspaceContext";
import "../CompanySnapshot.css";

// Optional company-summary widgets. Each reuses the component the Overview
// details or Compare tab already show, reading saved data only: no supplier
// refresh or AI request starts because a widget appeared. Buttons that fetch
// or cost money are the same explicit actions as elsewhere in the app.

export function CompanyChart() {
  const { instrumentId, visible, priceRead, onPriceRead, pricesStep } =
    useWorkspace();
  return (
    <Card className="ws-chart">
      <HistoricalPrices
        key={`prices-${instrumentId}`}
        instrumentId={instrumentId}
        initialRead={priceRead}
        visible={visible}
        onRead={onPriceRead}
        loadStep={pricesStep}
      />
    </Card>
  );
}

export function CompanyActivity() {
  const { snapshotData, data, instrumentId, onUpdates, onView, onSource } =
    useWorkspace();
  return (
    <LatestActivity
      data={snapshotData || data}
      instrumentId={instrumentId}
      onUpdates={onUpdates}
      onView={onView}
      onSource={onSource}
    />
  );
}

export function CompanyBusiness() {
  const { data, instrumentId, visible, onView, businessPanel } = useWorkspace();
  const [briefOpen, setBriefOpen] = useState(false);
  if (data.financials_pending)
    return (
      <Card>
        <SectionHeader level="card" as="h4" title="The business" />
        <p role="status">Loading saved filings…</p>
      </Card>
    );
  return (
    <Card>
      <OverviewSections
        data={data}
        instrumentId={instrumentId}
        visible={visible}
        onView={onView}
        businessPanel={businessPanel}
        briefOpen={briefOpen}
        onBriefToggle={setBriefOpen}
      />
    </Card>
  );
}

export function CompanyGlance() {
  const { data, financialError, onRetryFinancials } = useWorkspace();
  return (
    <Card className="glance">
      <SnapshotGlance
        data={data}
        financialError={financialError}
        onRetryFinancials={onRetryFinancials}
      />
    </Card>
  );
}

// Analyst targets read the same saved valuation context as Compare & value.
export function CompanyTargets() {
  const { data, instrumentId, visible, priceHistory } = useWorkspace();
  const [context, setContext] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!visible) return;
    let active = true;
    api
      .valuationContext(instrumentId)
      .then((value) => active && setContext(value))
      .catch((failure) => active && setError(failure.message));
    return () => {
      active = false;
    };
  }, [instrumentId, visible]);
  if (error)
    return (
      <Card role="alert">
        <SectionHeader level="card" as="h4" title="Analyst price targets" />
        <p>{error}</p>
      </Card>
    );
  if (!context)
    return (
      <Card aria-busy="true">
        <SectionHeader level="card" as="h4" title="Analyst price targets" />
        <p role="status">Reading saved targets…</p>
      </Card>
    );
  return (
    <AnalystTargets
      value={context.analyst_targets}
      quote={data.market?.quote?.quote}
      bars={priceHistory?.snapshot?.series?.bars}
      instrumentId={instrumentId}
      onRefresh={requestUpdate}
    />
  );
}

const every = (minutes) => (minutes === 60 ? "hour" : "four hours");

// Watch status only; turning a watch on or off stays on the News tab, where
// Telegram is checked first and the alert choices sit.
export function CompanyWatch() {
  const { data, instrumentId, onView } = useWorkspace();
  const watch = data.news_watch;
  const on = !!watch?.enabled;
  return (
    <Card className="ws-watch" aria-labelledby="ws-watch-title">
      <SectionHeader
        level="card"
        as="h4"
        id="ws-watch-title"
        title="News watch"
        actions={
          <Button
            size="sm"
            variant="tertiary"
            iconEnd={<ChevronRightIcon />}
            onClick={() => onView?.("evidence")}
          >
            {on ? "Manage watch" : "Set up a watch"}
          </Button>
        }
      />
      {on ? (
        <p>
          On · {watchFrequencyLabel(watch).toLowerCase()}{" "}
          {every(watch.interval_minutes)} while Fledge is running.
          {watch.last_check_at && (
            <>
              {" "}
              Last {watch.error ? "attempt" : "check"}{" "}
              {formatTimestamp(watch.last_check_at)}.
            </>
          )}
          {watch.error && <span className="warning"> {watch.error}</span>}
        </p>
      ) : (
        <p>
          Off. A watch checks this company’s news and discussion on a schedule
          and tells you what changed. Each check uses the AI budget.
        </p>
      )}
      {on && (
        <WatchCheckHistory
          instrumentId={instrumentId}
          lastCheck={watch.last_check_at}
        />
      )}
    </Card>
  );
}
