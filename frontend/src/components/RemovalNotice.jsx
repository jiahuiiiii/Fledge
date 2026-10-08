import { useEffect, useState } from "react";

export default function RemovalNotice({ company, onUndo, onDismiss }) {
  // Retain the message while its row collapses; hidden controls are inert.
  const [lastCompany, setLastCompany] = useState(company);
  useEffect(() => {
    if (company) setLastCompany(company);
  }, [company]);
  const displayed = company || lastCompany;
  return (
    <div
      className={`removal-notice${company ? " is-open" : ""}`}
      aria-hidden={!company}
      inert={!company ? "" : undefined}
    >
      <div className="removal-notice-clip">
        <div className="removal-notice-bar">
          <span
            key={displayed?.id}
            className="removal-notice-sweep"
            aria-hidden="true"
          />
          <span
            className="removal-notice-message"
            role="status"
            aria-atomic="true"
          >
            {displayed &&
              `${displayed.symbol} removed from sidebar. Saved research and monitoring are unchanged.`}
          </span>
          <div
            className="removal-notice-actions"
            role="group"
            aria-label="Removal actions"
          >
            <button
              type="button"
              aria-label="Undo"
              title="Undo removal"
              onClick={onUndo}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.75"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="m9 14-5-5 5-5M4 9h10a6 6 0 0 1 0 12h-2" />
              </svg>
            </button>
            <button
              type="button"
              aria-label="Dismiss removal notice"
              title="Dismiss"
              onClick={onDismiss}
            >
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.75"
                strokeLinecap="round"
                aria-hidden="true"
              >
                <path d="m6 6 12 12M18 6 6 18" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
