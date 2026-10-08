import { useEffect, useState } from "react";

const preferenceKey = "thesis.layout";
export function useWorkspaceLayout() {
  const [layout, setLayout] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(preferenceKey));
      return {
        companiesHidden: saved?.companiesHidden === true,
        ideaHidden: saved?.ideaHidden === true,
        progressHidden: saved?.progressHidden === true,
      };
    } catch {
      return {};
    }
  });
  useEffect(() => {
    try {
      localStorage.setItem(preferenceKey, JSON.stringify(layout));
    } catch {
      /* Layout controls still work when browser storage is unavailable. */
    }
  }, [layout]);
  const toggle = (key) =>
    setLayout((previous) => ({ ...previous, [key]: !previous[key] }));
  return [layout, toggle];
}

export default function WorkspaceControls({ layout, onToggle, hasCompany }) {
  return (
    <div
      className="workspace-controls"
      role="group"
      aria-label="Workspace panels"
    >
      {[
        ["companiesHidden", "company sidebar", "companies-sidebar", "left"],
        ["ideaHidden", "idea sidebar", "idea-sidebar", "right"],
      ].map(
        ([key, label, id, side]) =>
          (side === "left" || hasCompany) && (
            <button
              key={key}
              type="button"
              className={`panel-toggle panel-toggle-${side}`}
              title={`${layout[key] ? "Show" : "Hide"} ${label}`}
              aria-label={`${layout[key] ? "Show" : "Hide"} ${label}`}
              aria-expanded={!layout[key]}
              aria-controls={id}
              onClick={() => onToggle(key)}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                aria-hidden="true"
              >
                <rect x="3" y="4" width="18" height="16" rx="2" />
                <path d={side === "left" ? "M9 4v16" : "M15 4v16"} />
                {!layout[key] && (
                  <path
                    d={side === "left" ? "M5 7h2v10H5z" : "M17 7h2v10h-2z"}
                    fill="currentColor"
                    stroke="none"
                  />
                )}
              </svg>
            </button>
          ),
      )}
    </div>
  );
}
