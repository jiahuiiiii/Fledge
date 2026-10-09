import redditIcon from "../assets/source-icons/reddit.svg";
import hackerNewsIcon from "../assets/source-icons/hackernews.svg";
import xIcon from "../assets/source-icons/x.svg";

export const sourceNames = {
  all: "All sources",
  news: "Company news",
  reddit: "Reddit discussion",
  hackernews: "Hacker News",
  x: "X / Twitter",
};

export function sourceScope(source) {
  return source.kind === "news" ? "news" : source.platform || "reddit";
}

export function SourceIcon({ scope }) {
  if (scope === "hackernews")
    return (
      <img
        className="source-icon"
        src={hackerNewsIcon}
        alt=""
        aria-hidden="true"
      />
    );
  if (scope === "reddit" || scope === "x")
    return (
      <span
        className="source-icon source-icon-mask"
        style={{
          maskImage: `url("${scope === "reddit" ? redditIcon : xIcon}")`,
        }}
        aria-hidden="true"
      />
    );
  return (
    <svg
      className="source-icon"
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {scope === "all" ? (
        <>
          <rect x="3" y="3" width="7" height="7" rx="1.5" />
          <rect x="14" y="3" width="7" height="7" rx="1.5" />
          <rect x="3" y="14" width="7" height="7" rx="1.5" />
          <rect x="14" y="14" width="7" height="7" rx="1.5" />
        </>
      ) : (
        <>
          <rect x="3" y="4" width="18" height="16" rx="2" />
          <path d="M7 8h4v4H7zM15 8h2M15 12h2M7 16h10" />
        </>
      )}
    </svg>
  );
}

export function SourceLabel({ scope, children }) {
  return (
    <span className="source-attribution">
      <SourceIcon scope={scope} />
      <span>{children || sourceNames[scope]}</span>
    </span>
  );
}

export default function SourceFilters({
  selected,
  onChange,
  label = "Sentiment source type",
}) {
  return (
    <div
      className="sentiment-tabs source-filters"
      role="group"
      aria-label={label}
    >
      {Object.entries(sourceNames).map(([scope, name]) => (
        <button
          key={scope}
          type="button"
          aria-label={name}
          title={name}
          aria-pressed={selected === scope}
          className={`source-filter ${selected === scope ? "active" : ""}`}
          onClick={() => onChange(scope)}
        >
          <SourceIcon scope={scope} />
          {scope === "all" && <span>All</span>}
        </button>
      ))}
    </div>
  );
}
