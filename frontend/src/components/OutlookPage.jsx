import ManagementOutlook from "./ManagementOutlook";
import FmpPanel from "./FmpPanel";
import ExpectationsPanel from "./ExpectationsPanel";
import "./OutlookPage.css";

export default function OutlookPage({
  management,
  instrumentId,
  visible,
  initialRead,
  enabled,
  onSource,
  onView,
  onDraft,
  includeForecasts = true,
}) {
  return (
    <div className="outlook-page">
      {includeForecasts && (
        <>
          <ManagementOutlook data={management} />
          <FmpPanel
            instrumentId={instrumentId}
            visible={visible}
            mode="outlook"
          />
        </>
      )}
      <details className="outlook-news">
        <summary>
          <span>
            <strong>Expectations reported in the news</strong>
            <small>Attributed claims from saved stories</small>
          </span>
          <span className="outlook-status">Optional AI reading</span>
        </summary>
        <ExpectationsPanel
          initialRead={initialRead}
          visible={visible}
          instrumentId={instrumentId}
          enabled={enabled}
          onSource={onSource}
          onView={onView}
          onDraft={onDraft}
        />
      </details>
    </div>
  );
}
