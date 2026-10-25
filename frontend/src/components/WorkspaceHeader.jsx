import TelegramSettings from "./TelegramSettings";

// One header for the loading workspace, research pages and account settings.
export default function WorkspaceHeader({
  beginner,
  view,
  updatesWaiting = false,
  onNavigate,
  onHome,
  account,
}) {
  const items = beginner
    ? [
        ["workspace", "Home"],
        ["world", "World"],
        ["ideas", "My views"],
        ...(updatesWaiting ? [["updates", "Updates"]] : []),
      ]
    : [
        ["workspace", "Home"],
        ["ideas", "My views"],
        ["updates", "Updates"],
        ["world", "World"],
      ];
  return (
    <header className="topbar">
      <a className="skip-link" href="#workspace">
        Skip to content
      </a>
      <a
        href="?view=workspace"
        className="brand"
        onClick={(event) => {
          event.preventDefault();
          onNavigate("workspace");
        }}
      >
        fledge<span>↗</span>
      </a>
      <nav aria-label="Workspace navigation">
        {items.map(([key, label]) => {
          const active =
            view === key ||
            (view === "idea" && key === "ideas") ||
            (view === "review" && key === "updates");
          return (
            <button
              key={key}
              className={active ? "active" : ""}
              aria-current={active ? "page" : undefined}
              onClick={() =>
                beginner && key === "workspace" ? onHome() : onNavigate(key)
              }
            >
              {label}
              {key === "updates" && updatesWaiting && <i className="dot" />}
            </button>
          );
        })}
      </nav>
      <div className="topbar-tools">
        {!beginner && <TelegramSettings />}
        {account}
      </div>
    </header>
  );
}
