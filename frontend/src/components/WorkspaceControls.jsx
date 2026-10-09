import { useEffect, useState } from "react";

const preferenceKey = "thesis.layout";
export function useWorkspaceLayout() {
  const [layout, setLayout] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(preferenceKey));
      return {
        companiesHidden:
          saved?.railDefaultVersion === 2
            ? saved.companiesHidden !== false
            : true,
        railDefaultVersion: 2,
        ideaHidden: saved?.ideaHidden === true,
        progressHidden: saved?.progressHidden !== false,
      };
    } catch {
      return {
        companiesHidden: true,
        ideaHidden: true,
        progressHidden: true,
        railDefaultVersion: 2,
      };
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

export function WorkspaceSidebar({ hidden, children, ...props }) {
  return (
    <aside
      {...props}
      aria-hidden={hidden || undefined}
      inert={hidden ? "" : undefined}
    >
      <div className="sidebar-clip">
        <div className="sidebar-body">{children}</div>
      </div>
    </aside>
  );
}

export default function WorkspaceControls({ onOpen, ideaAvailable }) {
  if (!ideaAvailable) return null;
  return (
    <button type="button" className="my-research-button" onClick={onOpen}>
      My research
    </button>
  );
}
